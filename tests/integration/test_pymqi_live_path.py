"""Live path end to end: server -> PymqiConnector -> MQSC parser -> matchers.

pymqi needs the IBM MQ C client, so a fake module stands in for it. The fake
returns MQSC reply text exactly as MQCMD_ESCAPE's EscapedReply carries it.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import pytest

from mq_sentinel.auth.oidc import StubOIDCVerifier
from mq_sentinel.config import Settings
from mq_sentinel.connectors.base import MQConnectionError
from mq_sentinel.connectors.pymqi_connector import PymqiConnector
from mq_sentinel.inventory.models import QMEntry
from mq_sentinel.inventory.registry import InMemoryInventory
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.server import MQSentinelServer

_ESCAPED_REPLY = 3014

_REPLIES = {
    "DISPLAY QMGR VERSION": [
        "AMQ8408I: Display Queue Manager details.\n   QMNAME(LIVE_QM)   VERSION(09040000)"
    ],
    "DISPLAY CHSTATUS(*) ALL": [
        "AMQ8417I: Display Channel Status details.\n"
        "   CHANNEL(TO.PARTNER)   CHLTYPE(SDR)\n"
        "   CONNAME(partner.example(1414))   CURRENT\n"
        "   STATUS(RETRYING)   INDOUBT(NO)",
        "AMQ8417I: Display Channel Status details.\n"
        "   CHANNEL(FROM.PARTNER)   CHLTYPE(RCVR)\n"
        "   STATUS(RUNNING)   INDOUBT(YES)",
        "AMQ8417I: Display Channel Status details.\n"
        "   CHANNEL(APP.SVRCONN)   CHLTYPE(SVRCONN)\n"
        "   STATUS(RUNNING)   INDOUBT(NO)",
    ],
}


class _FakePCF:
    def __init__(self, qmgr: Any) -> None:
        self.qmgr = qmgr

    def MQCMD_ESCAPE(self, args: dict[int, Any]) -> list[dict[int, Any]]:  # noqa: N802
        command = args[1].decode()
        self.qmgr.commands.append(command)
        replies = _REPLIES.get(command, ["AMQ8147E: IBM MQ object not found."])
        return [{_ESCAPED_REPLY: r.encode()} for r in replies]

    def disconnect(self) -> None:
        pass


class _FakeQueueManager:
    def __init__(self, _name: Any) -> None:
        self.commands: list[str] = []
        self.connect_kwargs: dict[str, Any] = {}

    def connect_with_options(self, name: str, **kwargs: Any) -> None:
        self.name = name
        self.connect_kwargs = kwargs
        _fake_pymqi.last_qmgr = self  # type: ignore[attr-defined]

    def disconnect(self) -> None:
        pass


class _Struct:
    pass


_fake_pymqi = types.ModuleType("pymqi")
_fake_pymqi.CD = _Struct  # type: ignore[attr-defined]
_fake_pymqi.SCO = _Struct  # type: ignore[attr-defined]
_fake_pymqi.QueueManager = _FakeQueueManager  # type: ignore[attr-defined]
_fake_pymqi.PCFExecute = _FakePCF  # type: ignore[attr-defined]
_fake_pymqi.CMQC = types.SimpleNamespace(MQCHT_CLNTCONN=6, MQXPT_TCP=2)  # type: ignore[attr-defined]
_fake_pymqi.CMQCFC = types.SimpleNamespace(  # type: ignore[attr-defined]
    MQCACF_ESCAPE_TEXT=1,
    MQIACF_ESCAPE_TYPE=2,
    MQET_MQSC=1,
    MQCACF_ESCAPED_REPLY=_ESCAPED_REPLY,
)


@pytest.fixture(autouse=True)
def _pymqi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pymqi", _fake_pymqi)


def _entry(host: str = "mq1.example.com") -> QMEntry:
    return QMEntry(
        qm_name="LIVE_QM",
        host=host,
        port=1414,
        channel="MQS.SVRCONN",
        environment="dev",
        secret_ref="dev/live",
        cipher_spec="ANY_TLS13_OR_HIGHER",
    )


def _secrets_root(tmp_path: Path) -> Path:
    root = tmp_path / "secrets"
    secret = root / "dev" / "live"
    secret.mkdir(parents=True)
    for d in (root, root / "dev", secret):
        d.chmod(0o700)
    (secret / "username").write_text("mqsentinel\n")
    (secret / "password").write_text("not-a-real-password\n")
    (secret / "keystore_path").write_text("/etc/mqs/key\n")
    (secret / "cert_label").write_text("mqs-client\n")
    for f in secret.iterdir():
        f.chmod(0o600)
    return root


def _server(tmp_path: Path, *, secrets_dir: Path | None) -> MQSentinelServer:
    s = Settings()
    s.audit.log_path = tmp_path / "audit.jsonl"
    s.server.environment = "dev"
    s.server.connector = "pymqi"
    s.server.secrets_dir = str(secrets_dir) if secrets_dir else None
    return MQSentinelServer(s, inventory=InMemoryInventory([_entry()]), verifier=StubOIDCVerifier())


def test_live_channels_diagnosis_from_mqsc_text(tmp_path: Path) -> None:
    srv = _server(tmp_path, secrets_dir=_secrets_root(tmp_path))
    out = srv.dispatch(token="dev", tool="diagnose_failed_channels", params={"qm_name": "LIVE_QM"})

    assert out["topology"]["mq_version"] == "9.4.0.0"
    issues = {f["issue"] for f in out["findings"]}
    assert any("TO.PARTNER" in i for i in issues)
    assert "Channel FROM.PARTNER is in-doubt" in issues
    assert not any("APP.SVRCONN" in i for i in issues)
    assert out["raw_evidence"]["channels_examined"] == 3


def test_connect_uses_inventory_tls_and_filesystem_secrets(tmp_path: Path) -> None:
    srv = _server(tmp_path, secrets_dir=_secrets_root(tmp_path))
    srv.dispatch(token="dev", tool="diagnose_failed_channels", params={"qm_name": "LIVE_QM"})

    qmgr = _fake_pymqi.last_qmgr  # type: ignore[attr-defined]
    cd, sco = qmgr.connect_kwargs["cd"], qmgr.connect_kwargs["sco"]
    assert cd.ChannelName == b"MQS.SVRCONN"
    assert cd.ConnectionName == b"mq1.example.com(1414)"
    assert cd.SSLCipherSpec == b"ANY_TLS13_OR_HIGHER"
    assert sco.KeyRepository == b"/etc/mqs/key"
    assert sco.CertificateLabel == b"mqs-client"
    assert qmgr.connect_kwargs["user"] == b"mqsentinel"
    # Only allowlisted DISPLAY commands reached the queue manager.
    assert qmgr.commands and all(c.startswith("DISPLAY") for c in qmgr.commands)


def test_missing_secrets_dir_fails_with_actionable_message(tmp_path: Path) -> None:
    srv = _server(tmp_path, secrets_dir=None)
    with pytest.raises(RuntimeError, match="MQS_SERVER_SECRETS_DIR"):
        srv.dispatch(token="dev", tool="diagnose_failed_channels", params={"qm_name": "LIVE_QM"})


def test_health_lists_readable_qms_and_live_mode(tmp_path: Path) -> None:
    srv = _server(tmp_path, secrets_dir=_secrets_root(tmp_path))
    out = srv.dispatch(token="dev", tool="health", params={})
    assert out["connector"] == "live"
    assert [q["qm_name"] for q in out["queue_managers"]] == ["LIVE_QM"]


def test_shell_diagnostics_refused_for_remote_qm(monkeypatch: pytest.MonkeyPatch) -> None:
    def _no_subprocess(*_a: Any, **_k: Any) -> None:
        raise AssertionError("shell must not run for a remote QM")

    monkeypatch.setattr("subprocess.run", _no_subprocess)
    conn = PymqiConnector()
    conn.connect(_entry(), MQCredential(user="u", password="p"))
    with pytest.raises(MQConnectionError, match="queue manager's host"):
        conn.execute_shell(["dspmq", "-o", "standby"])


def test_connect_failure_reports_reason_code_not_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    class _MQMIError(Exception):
        reason = 2035

    def _refuse(self: Any, *_a: Any, **_k: Any) -> None:
        raise _MQMIError("conn string with password=hunter2")

    monkeypatch.setattr(_FakeQueueManager, "connect_with_options", _refuse)
    conn = PymqiConnector()
    with pytest.raises(MQConnectionError) as info:
        conn.connect(_entry(), MQCredential(user="u", password="hunter2"))
    assert str(info.value) == "failed to connect to LIVE_QM (MQRC 2035)"
    assert info.value.__cause__ is None
