"""diagnose_multi_instance_issues — active/standby state, shared FS, failover events."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from mq_sentinel.connectors.base import MQConnector
from mq_sentinel.inventory.registry import InventoryRegistry
from mq_sentinel.rcs.engine import RCSFinding
from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.rcs.matchers.miqm import match_miqm_findings
from mq_sentinel.secrets.backend import SecretsBackend
from mq_sentinel.tools.base import ToolResponse, open_qm
from mq_sentinel.topology.detect import TopologyFingerprint

TOOL_NAME = "diagnose_multi_instance_issues"

_INSTANCE_LINE_RE = re.compile(
    r"QMNAME\((?P<qm>\S+)\)\s+STATUS\((?P<status>[^)]+)\)"
    r"(?:\s+INSTANCE\((?P<host>\S+)\))?"
    r"(?:\s+MODE\((?P<mode>\S+)\))?",
    re.IGNORECASE,
)
_STANDBY_PERMITTED_RE = re.compile(r"STANDBY\(\s*PERMITTED\s*\)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class MIQMCheckResult:
    findings: tuple[RCSFinding, ...]
    raw_evidence: dict[str, Any]


def run_miqm_checks(
    connector: MQConnector,
    fingerprint: TopologyFingerprint,
    registry: KCRegistry,
) -> MIQMCheckResult:
    """Internal helper for use by the standalone tool and the composite."""
    dspmq_x = _safe_shell(connector, ["dspmq", "-x"])
    dspmq_standby = _safe_shell(connector, ["dspmq", "-o", "standby"])
    log_tail = _safe_log_tail(connector)

    instances = _parse_instances(dspmq_x)
    permitted = bool(_STANDBY_PERMITTED_RE.search(dspmq_standby))
    fs_ok = None  # filesystem probing requires a path-allowlisted reader (Phase 2)

    raw = {
        "instances": instances,
        "standby_permitted": permitted,
        "shared_fs_ok": fs_ok,
        "error_log_tail": log_tail,
    }
    findings = match_miqm_findings(raw, registry, mq_version=fingerprint.mq_version)
    return MIQMCheckResult(
        findings=tuple(findings),
        raw_evidence={
            "instance_count": len(instances),
            "active_count": sum(
                1 for i in instances if str(i.get("instance_type", "")).upper() == "ACTIVE"
            ),
            "standby_permitted": permitted,
        },
    )


def diagnose_multi_instance_issues(
    *,
    qm_name: str,
    connector_factory: Any,
    inventory: InventoryRegistry,
    secrets: SecretsBackend,
    kc_registry: KCRegistry | None = None,
) -> dict[str, Any]:
    registry = kc_registry or KCRegistry()
    with open_qm(
        qm_name,
        connector_factory=connector_factory,
        inventory=inventory,
        secrets=secrets,
    ) as (connector, _entry, fingerprint):
        result = run_miqm_checks(connector, fingerprint, registry)
        return ToolResponse(
            tool=TOOL_NAME,
            qm_name=qm_name,
            topology=fingerprint,
            findings=result.findings,
            raw_evidence=result.raw_evidence,
        ).to_dict()


# --- helpers ---------------------------------------------------------------


def _safe_shell(connector: MQConnector, argv: list[str]) -> str:
    try:
        return connector.execute_shell(argv)
    except Exception:  # noqa: BLE001
        return ""


def _safe_log_tail(connector: MQConnector) -> str:
    try:
        result = connector.execute_mqsc("DISPLAY QMSTATUS")
    except Exception:  # noqa: BLE001
        return ""
    return result.raw or ""


def _parse_instances(raw: str) -> list[dict[str, Any]]:
    if not raw:
        return []
    out: list[dict[str, Any]] = []
    for m in _INSTANCE_LINE_RE.finditer(raw):
        host = m.group("host") or ""
        mode = (m.group("mode") or "").upper()
        status = (m.group("status") or "").strip()
        # MQ uses MODE(Active) or MODE(Standby); some versions use INSTANCE only.
        instance_type = mode or _infer_role(status)
        out.append(
            {
                "qm_name": m.group("qm"),
                "host": host,
                "status": status,
                "instance_type": instance_type,
                "role": instance_type,
            }
        )
    return out


def _infer_role(status: str) -> str:
    s = status.upper()
    if "STANDBY" in s:
        return "STANDBY"
    if "RUNNING" in s or "ACTIVE" in s:
        return "ACTIVE"
    return "NONE"
