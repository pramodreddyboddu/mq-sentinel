"""diagnose_native_ha_issues — replica state, quorum, log lag, CRR."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from mq_sentinel.connectors.base import MQConnector
from mq_sentinel.inventory.registry import InventoryRegistry
from mq_sentinel.rcs.engine import RCSFinding
from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.rcs.matchers.native_ha import match_native_ha_findings
from mq_sentinel.secrets.backend import SecretsBackend
from mq_sentinel.tools.base import ToolResponse, open_qm
from mq_sentinel.topology.detect import TopologyFingerprint

TOOL_NAME = "diagnose_native_ha_issues"

_CRR_LAG_RE = re.compile(r"REPLICATIONLAG\s*\(\s*(\d+)\s*\)", re.IGNORECASE)
_RG_RE = re.compile(r"RECOVERYGROUP\s*\(\s*([A-Z0-9._%/]+)\s*\)", re.IGNORECASE)
_CRR_ROLE_RE = re.compile(r"RGROLE\s*\(\s*([A-Z]+)\s*\)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class NativeHACheckResult:
    findings: tuple[RCSFinding, ...]
    raw_evidence: dict[str, Any]


def run_native_ha_checks(
    connector: MQConnector,
    fingerprint: TopologyFingerprint,
    registry: KCRegistry,
) -> NativeHACheckResult:
    """Internal helper for use by the standalone tool and the composite."""
    instances = _safe_rows(connector, "DISPLAY NATIVEHASTATUS")
    rg_raw = _safe_raw(connector, "DISPLAY QMSTATUS RECOVERYGROUP")
    crr = _parse_crr(rg_raw)

    raw = {
        "instances": instances,
        "crr": crr,
        "quorum_required": (len(instances) // 2 + 1) if instances else 0,
    }
    findings = match_native_ha_findings(raw, registry, mq_version=fingerprint.mq_version)
    return NativeHACheckResult(
        findings=tuple(findings),
        raw_evidence={
            "instance_count": len(instances),
            "in_sync_count": sum(1 for i in instances if str(i.get("INSYNC", "")).upper() == "YES"),
            "active_count": sum(1 for i in instances if str(i.get("ROLE", "")).upper() == "ACTIVE"),
            "crr_enabled": bool(crr and crr.get("enabled")),
            "crr_lag_seconds": int((crr or {}).get("lag_seconds") or 0),
        },
    )


def diagnose_native_ha_issues(
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
        result = run_native_ha_checks(connector, fingerprint, registry)
        return ToolResponse(
            tool=TOOL_NAME,
            qm_name=qm_name,
            topology=fingerprint,
            findings=result.findings,
            raw_evidence=result.raw_evidence,
        ).to_dict()


# --- helpers ---------------------------------------------------------------


def _safe_rows(connector: MQConnector, command: str) -> list[dict[str, Any]]:
    try:
        result = connector.execute_mqsc(command)
    except Exception:  # noqa: BLE001 — best-effort
        return []
    return [dict(r) for r in result.rows]


def _safe_raw(connector: MQConnector, command: str) -> str:
    try:
        return connector.execute_mqsc(command).raw
    except Exception:  # noqa: BLE001
        return ""


def _parse_crr(raw: str) -> dict[str, Any] | None:
    """Parse RECOVERYGROUP output for CRR fields. Returns None if not enabled."""
    if not raw:
        return None
    rg_m = _RG_RE.search(raw)
    lag_m = _CRR_LAG_RE.search(raw)
    role_m = _CRR_ROLE_RE.search(raw)
    if not rg_m and not lag_m:
        return None
    return {
        "enabled": True,
        "recovery_group": rg_m.group(1) if rg_m else "",
        "lag_seconds": int(lag_m.group(1)) if lag_m else 0,
        "role": role_m.group(1) if role_m else "",
    }
