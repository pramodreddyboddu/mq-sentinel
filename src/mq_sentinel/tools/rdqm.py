"""diagnose_rdqm_issues — Pacemaker, DRBD, and rdqmstatus inspection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from mq_sentinel.connectors.base import MQConnector
from mq_sentinel.inventory.registry import InventoryRegistry
from mq_sentinel.rcs.engine import RCSFinding
from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.rcs.matchers.rdqm import match_rdqm_findings
from mq_sentinel.secrets.backend import SecretsBackend
from mq_sentinel.tools.base import ToolResponse, open_qm
from mq_sentinel.topology.detect import TopologyFingerprint

TOOL_NAME = "diagnose_rdqm_issues"


# --- shell parsers ---------------------------------------------------------

_MULTI_I = re.MULTILINE | re.IGNORECASE
_RDQM_QM_NAME_RE = re.compile(r"^Queue manager name:\s+(\S+)", re.MULTILINE)
_RDQM_HA_STATE_RE = re.compile(r"^(?:HA )?(?:current )?status:\s+(.+)$", _MULTI_I)
_RDQM_RUNNING_RE = re.compile(r"^(?:Running on|Current node):\s+(\S+)", _MULTI_I)
_RDQM_PREFERRED_RE = re.compile(r"^Preferred location:\s+(\S+)", _MULTI_I)
_RDQM_REPLICA_LINE_RE = re.compile(r"^\s*Node:\s+(\S+)\s+(?:HA replica|Status):\s+(.+)$", _MULTI_I)

_CRM_NODE_LINE_RE = re.compile(r"^\* Node\s+(\S+):\s+(\S+)", re.MULTILINE)
_CRM_ONLINE_LINE_RE = re.compile(r"^Online:\s*\[\s*([^\]]+)\s*\]", re.MULTILINE)
_CRM_OFFLINE_LINE_RE = re.compile(r"^OFFLINE:\s*\[\s*([^\]]+)\s*\]", re.MULTILINE)
_CRM_FAILED_RE = re.compile(
    r"\*\s+(\S+).*?(FAILED|Stopped|Stop \(disabled\)|unmanaged)\s+(?:on|because)?\s*(\S*)",
    re.IGNORECASE,
)

_DRBD_RESOURCE_HEADER_RE = re.compile(
    r"^(?P<name>\S+)\s+role:(?P<role>\S+)\s+disk:(?P<disk>\S+)\s*$"
)
_DRBD_PEER_HEADER_RE = re.compile(r"^\s+(?P<peer>\S+)\s+connection:(?P<conn>\S+)\s*$")
_DRBD_PEER_DETAIL_RE = re.compile(
    r"^\s+role:(?P<peer_role>\S+)\s+(?:peer-disk|peer disk):(?P<peer_disk>\S+)"
)
_DRBD_SPLIT_BRAIN_RE = re.compile(r"split.?brain", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class RDQMCheckResult:
    findings: tuple[RCSFinding, ...]
    raw_evidence: dict[str, Any]


def run_rdqm_checks(
    connector: MQConnector,
    fingerprint: TopologyFingerprint,
    registry: KCRegistry,
    *,
    qm_name: str = "",
) -> RDQMCheckResult:
    """Internal helper: gather RDQM inputs and produce findings."""
    rdqm_raw = _safe_shell(connector, ["rdqmstatus"])
    crm_raw = _safe_shell(connector, ["crm_mon", "-1"])
    drbd_raw = _safe_shell(connector, ["drbdadm", "status"])

    rdqm_status = _parse_rdqmstatus(rdqm_raw, fallback_qm=qm_name)
    pacemaker = _parse_crm_mon(crm_raw)
    drbd = _parse_drbd(drbd_raw)

    findings = match_rdqm_findings(
        {"rdqm_status": rdqm_status, "pacemaker": pacemaker, "drbd": drbd},
        registry,
        mq_version=fingerprint.mq_version,
    )
    return RDQMCheckResult(
        findings=tuple(findings),
        raw_evidence={
            "pacemaker_total": int(pacemaker.get("total_nodes") or 0),
            "pacemaker_online": len(pacemaker.get("online_nodes") or []),
            "pacemaker_offline": len(pacemaker.get("offline_nodes") or []),
            "pacemaker_failed_resources": len(pacemaker.get("failed_resources") or []),
            "drbd_resources": len(drbd),
            "drbd_split_brain": any(d.get("split_brain") for d in drbd),
            "rdqm_running_node": str(rdqm_status.get("running_node") or ""),
        },
    )


def diagnose_rdqm_issues(
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
        result = run_rdqm_checks(connector, fingerprint, registry, qm_name=qm_name)
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
    except Exception:  # noqa: BLE001 — best-effort, partial diagnostics still useful
        return ""


def _parse_rdqmstatus(raw: str, fallback_qm: str = "") -> dict[str, Any]:
    if not raw:
        return {}
    qm_m = _RDQM_QM_NAME_RE.search(raw)
    state_m = _RDQM_HA_STATE_RE.search(raw)
    running_m = _RDQM_RUNNING_RE.search(raw)
    preferred_m = _RDQM_PREFERRED_RE.search(raw)
    replicas: list[dict[str, str]] = [
        {"node": m.group(1), "status": m.group(2).strip()}
        for m in _RDQM_REPLICA_LINE_RE.finditer(raw)
    ]
    return {
        "qm_name": qm_m.group(1) if qm_m else fallback_qm,
        "ha_state": state_m.group(1).strip() if state_m else "",
        "running_node": running_m.group(1) if running_m else "",
        "preferred_location": preferred_m.group(1) if preferred_m else "",
        "ha_replicas": replicas,
    }


def _parse_crm_mon(raw: str) -> dict[str, Any]:
    if not raw:
        return {}

    online: list[str] = []
    offline: list[str] = []

    online_m = _CRM_ONLINE_LINE_RE.search(raw)
    if online_m:
        online = [n for n in online_m.group(1).split() if n]
    offline_m = _CRM_OFFLINE_LINE_RE.search(raw)
    if offline_m:
        offline = [n for n in offline_m.group(1).split() if n]

    # Fallback: per-node lines (`* Node host: state`)
    if not online and not offline:
        for m in _CRM_NODE_LINE_RE.finditer(raw):
            node, state = m.group(1), m.group(2).lower()
            if state == "online":
                online.append(node)
            elif state in {"offline", "standby"}:
                offline.append(node)

    failed: list[dict[str, str]] = []
    if "Failed Resource Actions" in raw or "Failed Actions" in raw:
        for m in _CRM_FAILED_RE.finditer(raw):
            failed.append(
                {
                    "resource": m.group(1),
                    "status": m.group(2),
                    "node": m.group(3) or "",
                }
            )

    return {
        "total_nodes": len(online) + len(offline),
        "online_nodes": online,
        "offline_nodes": offline,
        "failed_resources": failed,
    }


def _parse_drbd(raw: str) -> list[dict[str, Any]]:
    """Parse `drbdadm status` output into one entry per (resource, peer) pair.

    Format:
        RESOURCE_NAME role:R disk:D
          PEER_NAME connection:C
            role:PR peer-disk:PD
          PEER_NAME_2 connection:C2
            role:PR2 peer-disk:PD2
        OTHER_RESOURCE role:R disk:D
          ...
    """
    if not raw:
        return []
    out: list[dict[str, Any]] = []
    has_split_brain_marker = bool(_DRBD_SPLIT_BRAIN_RE.search(raw))

    current_resource: dict[str, str] | None = None
    pending_peer: dict[str, str] | None = None

    def _flush_peer() -> None:
        if current_resource is None or pending_peer is None:
            return
        out.append(
            {
                "resource": current_resource["name"],
                "role": current_resource["role"],
                "disk_state": current_resource["disk"],
                "peer": pending_peer.get("peer", ""),
                "connection_state": pending_peer.get("conn", ""),
                "peer_role": pending_peer.get("peer_role", ""),
                "peer_disk_state": pending_peer.get("peer_disk", ""),
                "split_brain": has_split_brain_marker,
            }
        )

    for line in raw.splitlines():
        rh = _DRBD_RESOURCE_HEADER_RE.match(line)
        if rh:
            _flush_peer()
            pending_peer = None
            current_resource = {
                "name": rh.group("name"),
                "role": rh.group("role"),
                "disk": rh.group("disk"),
            }
            continue
        ph = _DRBD_PEER_HEADER_RE.match(line)
        if ph and current_resource is not None:
            _flush_peer()
            pending_peer = {
                "peer": ph.group("peer"),
                "conn": ph.group("conn"),
                "peer_role": "",
                "peer_disk": "",
            }
            continue
        pd = _DRBD_PEER_DETAIL_RE.match(line)
        if pd and pending_peer is not None:
            pending_peer["peer_role"] = pd.group("peer_role")
            pending_peer["peer_disk"] = pd.group("peer_disk")
            continue

    _flush_peer()

    if not out and has_split_brain_marker:
        out.append(
            {
                "resource": "<unknown>",
                "role": "",
                "disk_state": "",
                "connection_state": "",
                "peer_role": "",
                "peer_disk_state": "",
                "split_brain": True,
            }
        )
    return out
