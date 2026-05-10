"""diagnose_zos_qsg_issues — Queue Sharing Group, CHIN, page sets, buffer pools, CF."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mq_sentinel.connectors.base import MQConnector
from mq_sentinel.inventory.registry import InventoryRegistry
from mq_sentinel.rcs.engine import RCSFinding
from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.rcs.matchers.zos import match_zos_findings
from mq_sentinel.secrets.backend import SecretsBackend
from mq_sentinel.tools.base import ToolResponse, open_qm
from mq_sentinel.topology.detect import TopologyFingerprint

TOOL_NAME = "diagnose_zos_qsg_issues"


@dataclass(frozen=True, slots=True)
class ZosCheckResult:
    findings: tuple[RCSFinding, ...]
    raw_evidence: dict[str, Any]


def run_zos_checks(
    connector: MQConnector,
    fingerprint: TopologyFingerprint,
    registry: KCRegistry,
) -> ZosCheckResult:
    """Internal helper for use by the standalone tool and the composite."""
    group_rows = _safe_rows(connector, "DISPLAY GROUP")
    chinit_rows = _safe_rows(connector, "DISPLAY QMSTATUS CHINIT")
    pageset_rows = _safe_rows(connector, "DISPLAY USAGE PSID(*)")
    bufferpool_rows = _safe_rows(connector, "DISPLAY USAGE BUFFPOOL(*)")
    cf_rows = _safe_rows(connector, "DISPLAY CFSTATUS(*) ALL")

    qsg_name = ""
    members: list[dict[str, Any]] = []
    for row in group_rows:
        if "QSGNAME" in row and not qsg_name:
            qsg_name = str(row["QSGNAME"])
        if "QMNAME" in row:
            members.append({"name": str(row["QMNAME"]), "status": str(row.get("STATUS", ""))})

    chin_status = ""
    for row in chinit_rows:
        if "CHINIT" in row:
            chin_status = str(row["CHINIT"])
            break

    raw = {
        "group": {"qsg_name": qsg_name, "members": members},
        "chin": {"status": chin_status} if chin_status else {},
        "pagesets": pageset_rows,
        "bufferpools": bufferpool_rows,
        "cf_structures": cf_rows,
    }
    findings = match_zos_findings(raw, registry, mq_version=fingerprint.mq_version)
    return ZosCheckResult(
        findings=tuple(findings),
        raw_evidence={
            "qsg_name": qsg_name,
            "qsg_member_count": len(members),
            "pageset_count": len(pageset_rows),
            "bufferpool_count": len(bufferpool_rows),
            "cf_structure_count": len(cf_rows),
            "chin_status": chin_status,
        },
    )


def diagnose_zos_qsg_issues(
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
        result = run_zos_checks(connector, fingerprint, registry)
        return ToolResponse(
            tool=TOOL_NAME,
            qm_name=qm_name,
            topology=fingerprint,
            findings=result.findings,
            raw_evidence=result.raw_evidence,
        ).to_dict()


def _safe_rows(connector: MQConnector, command: str) -> list[dict[str, Any]]:
    try:
        result = connector.execute_mqsc(command)
    except Exception:  # noqa: BLE001 — best-effort
        return []
    return [dict(r) for r in result.rows]
