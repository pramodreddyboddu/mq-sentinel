"""check_cluster_health — partial-repo / stale / suspended / unhealthy channels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mq_sentinel.connectors.base import MQConnector
from mq_sentinel.inventory.registry import InventoryRegistry
from mq_sentinel.rcs.engine import RCSFinding
from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.rcs.matchers.cluster import match_cluster_findings
from mq_sentinel.secrets.backend import SecretsBackend
from mq_sentinel.tools.base import ToolResponse, open_qm
from mq_sentinel.topology.detect import TopologyFingerprint

TOOL_NAME = "check_cluster_health"


@dataclass(frozen=True, slots=True)
class ClusterCheckResult:
    findings: tuple[RCSFinding, ...]
    raw_evidence: dict[str, Any]


def run_cluster_checks(
    connector: MQConnector,
    fingerprint: TopologyFingerprint,
    registry: KCRegistry,
    *,
    fallback_qm_name: str = "",
) -> ClusterCheckResult:
    """Internal helper for use by the standalone tool and the composite."""
    clusqmgrs = _safe_rows(connector, "DISPLAY CLUSQMGR(*) ALL")
    repos_raw = _safe_raw(connector, "DISPLAY QMGR REPOS REPOSNL")
    this_qm = _safe_attr(connector, "DISPLAY QMGR QMNAME", "QMNAME") or fallback_qm_name
    findings = match_cluster_findings(
        {"clusqmgrs": clusqmgrs, "repos": repos_raw, "this_qm": this_qm},
        registry,
        mq_version=fingerprint.mq_version,
    )
    clusters_seen = sorted({str(r.get("CLUSTER", "")) for r in clusqmgrs if r.get("CLUSTER")})
    return ClusterCheckResult(
        findings=tuple(findings),
        raw_evidence={
            "clusqmgr_rows": len(clusqmgrs),
            "clusters_seen": clusters_seen,
            "this_qm": this_qm,
        },
    )


def check_cluster_health(
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
        result = run_cluster_checks(connector, fingerprint, registry, fallback_qm_name=qm_name)
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


def _safe_raw(connector: MQConnector, command: str) -> str:
    try:
        return connector.execute_mqsc(command).raw
    except Exception:  # noqa: BLE001
        return ""


def _safe_attr(connector: MQConnector, command: str, attr: str) -> str | None:
    try:
        result = connector.execute_mqsc(command)
    except Exception:  # noqa: BLE001
        return None
    for row in result.rows:
        if attr in row:
            return str(row[attr])
    return None
