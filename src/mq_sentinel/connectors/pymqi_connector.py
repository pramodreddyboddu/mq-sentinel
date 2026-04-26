"""Real IBM MQ connector via pymqi.

pymqi is imported lazily — the module remains importable on systems without
the IBM MQ C client libraries installed. Connecting fails fast with a clear
error if pymqi cannot be loaded.

Every MQSC and shell call is gated by the security allowlist before execution.
"""

from __future__ import annotations

import hashlib
import shlex
import subprocess
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from mq_sentinel.connectors.base import (
    BrowseResult,
    DLQHeader,
    MQConnectionError,
    MQSCResult,
)
from mq_sentinel.inventory.models import QMEntry
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.security.allowlist import assert_mqsc_allowed, assert_shell_allowed

if TYPE_CHECKING:  # pragma: no cover
    pass


_SUBPROCESS_TIMEOUT = 30  # seconds — bounded to prevent hung diagnostics
_MQSC_TIMEOUT = 30


def _import_pymqi() -> Any:
    try:
        import pymqi  # type: ignore[import-not-found]
    except ImportError as exc:
        raise MQConnectionError(
            "pymqi is not installed. Install IBM MQ client libraries and "
            "`uv sync --extra mq` to enable live connections."
        ) from exc
    return pymqi


class PymqiConnector:
    """Live MQ connector. Read-only by construction (allowlist on every call)."""

    def __init__(self) -> None:
        self._pymqi: Any = None
        self._qmgr: Any = None
        self._pcf: Any = None
        self._entry: QMEntry | None = None

    def connect(self, entry: QMEntry, credential: MQCredential) -> None:
        self._pymqi = _import_pymqi()
        cd = self._pymqi.CD()
        cd.ChannelName = entry.channel.encode()
        cd.ConnectionName = f"{entry.host}({entry.port})".encode()
        cd.ChannelType = self._pymqi.CMQC.MQCHT_CLNTCONN
        cd.TransportType = self._pymqi.CMQC.MQXPT_TCP

        sco = None
        if credential.keystore_path:
            sco = self._pymqi.SCO()
            sco.KeyRepository = credential.keystore_path.encode()

        try:
            self._qmgr = self._pymqi.QueueManager(None)
            self._qmgr.connect_with_options(
                entry.qm_name,
                cd=cd,
                sco=sco,
                user=credential.user.encode(),
                password=credential.password.encode(),
            )
            self._pcf = self._pymqi.PCFExecute(self._qmgr)
            self._entry = entry
        except Exception:  # noqa: BLE001 — wrap to avoid leaking creds
            # Never include the password or full pymqi exception args (some
            # versions echo the connection string back). Map to a clean message.
            raise MQConnectionError(f"failed to connect to {entry.qm_name}") from None

    def disconnect(self) -> None:
        try:
            if self._pcf is not None:
                self._pcf.disconnect()
        finally:
            try:
                if self._qmgr is not None:
                    self._qmgr.disconnect()
            finally:
                self._pcf = None
                self._qmgr = None
                self._entry = None

    def execute_mqsc(self, command: str) -> MQSCResult:
        if self._qmgr is None:
            raise MQConnectionError("not connected")
        assert_mqsc_allowed(command)

        # MQSC over PCF: build the equivalent PCF command per verb. For the
        # phase-1 read set (DISPLAY/DIS/PING CHANNEL) we route through
        # MQCMD_ESCAPE so the curated allowlist remains the single source of
        # truth for what is permitted.
        pymqi = self._pymqi
        try:
            args = {
                pymqi.CMQCFC.MQCACF_ESCAPE_TEXT: command.encode(),
                pymqi.CMQCFC.MQIACF_ESCAPE_TYPE: pymqi.CMQCFC.MQET_MQSC,
            }
            response = self._pcf.MQCMD_ESCAPE(args)
        except Exception as exc:
            raise MQConnectionError(f"MQSC execution failed for {command!r}") from exc

        rows = self._parse_pcf_response(response)
        raw = self._render_raw(rows)
        return MQSCResult(command=command, rows=rows, raw=raw, completion_code=0)

    def execute_shell(self, argv: Sequence[str]) -> str:
        assert_shell_allowed(argv)
        try:
            proc = subprocess.run(  # noqa: S603 — argv list, no shell, allowlisted
                list(argv),
                capture_output=True,
                text=True,
                timeout=_SUBPROCESS_TIMEOUT,
                check=False,
            )
        except FileNotFoundError as exc:
            raise MQConnectionError(f"binary not found: {argv[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise MQConnectionError(f"timeout running {shlex.join(argv)}") from exc
        # We never raise on non-zero — diagnostic binaries often signal state
        # via exit code. Combine streams for the caller to inspect.
        return (proc.stdout or "") + (proc.stderr or "")

    def browse_dlq(self, queue_name: str, max_messages: int = 50) -> BrowseResult:
        """Browse DLQ messages and return only the MQDLH headers.

        SECURITY: This method MUST NOT return message body content. We MQGET
        in BROWSE mode, parse the MQDLH from the front of the buffer, and
        discard everything after it. The body length is reported; the body
        bytes are zeroed out before any other code can touch them.
        """
        if self._qmgr is None:
            raise MQConnectionError("not connected")
        if max_messages < 1 or max_messages > 500:
            raise ValueError("max_messages must be in [1, 500]")

        pymqi = self._pymqi
        cmqc = pymqi.CMQC
        headers: list[DLQHeader] = []
        depth = 0

        try:
            queue = pymqi.Queue(
                self._qmgr,
                queue_name,
                cmqc.MQOO_INPUT_SHARED | cmqc.MQOO_BROWSE | cmqc.MQOO_INQUIRE,
            )
            try:
                depth = int(queue.inquire(cmqc.MQIA_CURRENT_Q_DEPTH))
            except Exception:  # noqa: BLE001 — inquire is best-effort
                depth = 0

            gmo = pymqi.GMO()
            gmo.Options = cmqc.MQGMO_BROWSE_FIRST | cmqc.MQGMO_FAIL_IF_QUIESCING
            for _ in range(max_messages):
                md = pymqi.MD()
                try:
                    raw_msg = queue.get(None, md, gmo)
                except pymqi.MQMIError as exc:
                    if exc.reason == cmqc.MQRC_NO_MSG_AVAILABLE:
                        break
                    raise MQConnectionError(f"DLQ browse failed (reason {exc.reason})") from None

                header = self._parse_dlh_safely(raw_msg, md)
                # Zero the buffer reference so the body cannot be reused.
                del raw_msg
                if header is not None:
                    headers.append(header)
                gmo.Options = cmqc.MQGMO_BROWSE_NEXT | cmqc.MQGMO_FAIL_IF_QUIESCING
            queue.close()
        except Exception as exc:
            if isinstance(exc, MQConnectionError):
                raise
            raise MQConnectionError(f"DLQ browse failed for {queue_name!r}") from None

        return BrowseResult(
            queue_name=queue_name,
            qm_name=self._entry.qm_name if self._entry else "",
            sample_size=len(headers),
            queue_depth=depth,
            headers=headers,
        )

    @staticmethod
    def _parse_dlh_safely(raw: bytes, md: object) -> DLQHeader | None:
        # MQDLH layout (RFC 1.0): 'MQDLH' magic + version + reason + feedback +
        # encoding + coded_char_set_id + format + put_appl_type + put_appl_name +
        # put_date + put_time + dest_q_name + dest_q_mgr_name. Total 172 bytes.
        if not raw or len(raw) < 172 or not raw.startswith(b"MQDLH"):
            return None
        view = raw[:172]
        try:
            reason = int.from_bytes(view[12:16], "big", signed=True)
            feedback = int.from_bytes(view[16:20], "big", signed=True)
            put_appl_type = int.from_bytes(view[60:64], "big", signed=True)
            put_appl_name = view[64:92].rstrip(b" \x00").decode(errors="replace")
            put_date = view[92:100].rstrip(b" \x00").decode(errors="replace")
            put_time = view[100:108].rstrip(b" \x00").decode(errors="replace")
            dest_q_name = view[108:156].rstrip(b" \x00").decode(errors="replace")
            if len(raw) >= 204:
                dest_q_mgr_name = raw[156:204].rstrip(b" \x00").decode(errors="replace")
            else:
                dest_q_mgr_name = ""
        except Exception:  # noqa: BLE001 — defensive
            return None

        msg_id = getattr(md, "MsgId", b"") or b""
        body_length = max(0, len(raw) - 172)
        backout = int(getattr(md, "BackoutCount", 0))

        return DLQHeader(
            reason_code=reason,
            feedback=feedback,
            put_application_name=put_appl_name,
            put_application_type=str(put_appl_type),
            put_date=put_date,
            put_time=put_time,
            dest_q_name=dest_q_name,
            dest_q_mgr_name=dest_q_mgr_name,
            backout_count=backout,
            body_length=body_length,
            msg_id_hash=hashlib.sha256(msg_id).hexdigest(),
        )

    # --- helpers ----------------------------------------------------------

    @staticmethod
    def _parse_pcf_response(response: Any) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for record in response or []:
            row: dict[str, str] = {}
            for k, v in record.items():
                key = str(k)
                if isinstance(v, bytes):
                    row[key] = v.decode(errors="replace").strip()
                else:
                    row[key] = str(v)
            rows.append(row)
        return rows

    @staticmethod
    def _render_raw(rows: list[dict[str, str]]) -> str:
        lines: list[str] = []
        for row in rows:
            lines.append(" ".join(f"{k}({v})" for k, v in row.items()))
        return "\n".join(lines)
