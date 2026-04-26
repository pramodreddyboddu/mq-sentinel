"""Channel failure pattern matchers.

Maps raw CHSTATUS rows + AMQERR log excerpts to RCSFindings with
verified IBM Knowledge Center links. No invented fixes — only patterns
backed by curated entries in KCRegistry.
"""

from __future__ import annotations

import re
from typing import Any

from mq_sentinel.rcs.engine import RCSFinding, Severity
from mq_sentinel.rcs.kc_registry import KCRegistry

_AMQ_CODE = re.compile(r"\bAMQ\d{4}[A-Z]?\b")


def _extract_amq_codes(text: str) -> list[str]:
    return [m.group(0).rstrip("EWIS") for m in _AMQ_CODE.finditer(text or "")]


def _bad_chstatus_status(status: str) -> bool:
    return status.upper() in {
        "RETRYING",
        "STOPPED",
        "PAUSED",
        "INDOUBT",
        "INACTIVE_FAILED",
    }


def match_channel_failures(
    raw_data: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None = None,
) -> list[RCSFinding]:
    """Inspect channel data and produce findings.

    Expected raw_data shape:
        {
            "channels": [{"CHANNEL": "APP.SVRCONN", "STATUS": "RETRYING",
                          "REASON": 2035, "RQMNAME": "...", ...}, ...],
            "error_log_tail": "...AMQ9202E... AMQ9503E...",
        }
    """
    findings: list[RCSFinding] = []

    for ch in raw_data.get("channels", []) or []:
        name = str(ch.get("CHANNEL") or ch.get("CHLNAME") or "<unknown>")
        status = str(ch.get("STATUS") or ch.get("CHSTATUS") or "")
        reason_raw = ch.get("REASON") or ch.get("LSTMSGRC") or 0
        try:
            reason = int(reason_raw)
        except (TypeError, ValueError):
            reason = 0

        if not _bad_chstatus_status(status) and reason == 0:
            continue

        if reason == 2035:
            findings.append(_finding_2035(name, ch, registry, mq_version))
            continue

        if reason in (2009, 2059):
            findings.append(_finding_conn_error(name, ch, reason, registry, mq_version))
            continue

        if status.upper() == "INDOUBT":
            findings.append(_finding_indoubt(name, ch))
            continue

        if _bad_chstatus_status(status):
            findings.append(_finding_generic_bad_status(name, ch, status))

    log_tail = str(raw_data.get("error_log_tail") or "")
    for amq in set(_extract_amq_codes(log_tail)):
        refs = registry.lookup_amq(amq, mq_version)
        if not refs:
            continue
        findings.append(
            RCSFinding(
                issue=f"Error log contains {amq}",
                severity=Severity.HIGH,
                reason_code=None,
                amq_code=amq,
                root_cause=(
                    f"AMQERR log contains {amq}. See the IBM Knowledge Center page "
                    "for the documented cause and resolution."
                ),
                fix_steps=(
                    "DISPLAY CHSTATUS(*) WHERE(LSTMSGRC NE 0)",
                    "DISPLAY LSSTATUS(*) ALL",
                ),
                verify_commands=("DISPLAY QMSTATUS",),
                doc_refs=tuple(refs),
                confidence="High",
                evidence={"amq_code": amq},
            )
        )

    return findings


def _finding_2035(
    name: str,
    ch: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None,
) -> RCSFinding:
    refs = registry.lookup_reason(2035, mq_version)
    return RCSFinding(
        issue=f"Channel {name} returned MQRC 2035 (NOT_AUTHORIZED)",
        severity=Severity.HIGH,
        reason_code=2035,
        amq_code=None,
        root_cause=(
            "The connecting principal failed authorization. Common causes: "
            "a CHLAUTH BLOCKUSER rule blocked the user, the resolved MCAUSER "
            "lacks +connect/+inq on the QM, or CONNAUTH credentials failed."
        ),
        fix_steps=(
            f"DISPLAY CHLAUTH('{name}') ALL",
            f"DISPLAY CHSTATUS('{name}') ALL",
            "DISPLAY QMGR CONNAUTH",
            "DISPLAY AUTHINFO(*) ALL",
        ),
        verify_commands=(
            f"DISPLAY CHSTATUS('{name}') CURRENT",
            "DISPLAY QMSTATUS",
        ),
        doc_refs=tuple(refs),
        confidence="High",
        evidence={
            "channel": name,
            "status": str(ch.get("STATUS", "")),
            "rqmname": str(ch.get("RQMNAME", "")),
        },
    )


def _finding_conn_error(
    name: str,
    ch: dict[str, Any],
    reason: int,
    registry: KCRegistry,
    mq_version: str | None,
) -> RCSFinding:
    refs = registry.lookup_amq("AMQ9202", mq_version)
    return RCSFinding(
        issue=f"Channel {name} connection error (reason {reason})",
        severity=Severity.HIGH,
        reason_code=reason,
        amq_code="AMQ9202",
        root_cause=(
            "Network or TLS handshake failure to the remote endpoint. "
            "Verify CONNAME resolves, the listener is running, and the TLS "
            "negotiation completes (CipherSpec/CipherSuite and certificates)."
        ),
        fix_steps=(
            f"DISPLAY CHSTATUS('{name}') ALL",
            f"DISPLAY CHANNEL('{name}') CONNAME XMITQ SSLCIPH",
            "DISPLAY LSSTATUS(*) ALL",
            "PING CHANNEL(" + name + ")",
        ),
        verify_commands=(f"DISPLAY CHSTATUS('{name}') CURRENT",),
        doc_refs=tuple(refs),
        confidence="High",
        evidence={"channel": name, "status": str(ch.get("STATUS", ""))},
    )


def _finding_indoubt(name: str, ch: dict[str, Any]) -> RCSFinding:
    return RCSFinding(
        issue=f"Channel {name} is in-doubt",
        severity=Severity.CRITICAL,
        reason_code=None,
        amq_code=None,
        root_cause=(
            "An in-doubt channel has uncommitted batches that cannot resolve "
            "automatically. Manual resolution is required after confirming the "
            "remote QM state."
        ),
        fix_steps=(
            f"DISPLAY CHSTATUS('{name}') ALL CURLUWID LSTLUWID",
            # Resolution itself (RESOLVE CHANNEL) is intentionally NOT suggested;
            # this MCP is read-only. The operator must run it manually.
        ),
        verify_commands=(f"DISPLAY CHSTATUS('{name}') CURRENT",),
        doc_refs=(),
        confidence="Medium",
        evidence={"channel": name, "status": "INDOUBT"},
    )


def _finding_generic_bad_status(name: str, ch: dict[str, Any], status: str) -> RCSFinding:
    return RCSFinding(
        issue=f"Channel {name} status is {status}",
        severity=Severity.MEDIUM,
        reason_code=None,
        amq_code=None,
        root_cause=(
            f"Channel reports status {status}. Inspect retry counters, "
            "last error code, and the AMQERR log for context."
        ),
        fix_steps=(
            f"DISPLAY CHSTATUS('{name}') ALL",
            f"DISPLAY CHANNEL('{name}') ALL",
        ),
        verify_commands=(f"DISPLAY CHSTATUS('{name}') CURRENT",),
        doc_refs=(),
        confidence="Medium",
        evidence={"channel": name, "status": status},
    )
