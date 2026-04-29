"""RDQM (Replicated Data Queue Manager) pattern matchers.

Inspects three signal sources:
  1. `rdqmstatus` — IBM's RDQM management view of the QM HA group.
  2. `crm_mon` (Pacemaker) — node + resource state across the 3-node cluster.
  3. `drbdadm status` — block-level replication state per resource.

Read-only: no `pcs`, `crm`, `drbdadm primary/secondary`, or other recovery
commands ever appear in fix steps. KC links carry the manual procedure for
resolving split-brain or quorum loss.
"""

from __future__ import annotations

from typing import Any

from mq_sentinel.rcs.engine import RCSFinding, Severity
from mq_sentinel.rcs.kc_registry import KCRegistry

_BAD_DRBD_CONN = {"WFConnection", "StandAlone", "Disconnecting", "Unconnected", "Timeout"}
_DEGRADED_DRBD_CONN = {
    "SyncTarget",
    "SyncSource",
    "VerifyS",
    "VerifyT",
    "PausedSyncT",
    "PausedSyncS",
}
_BAD_DRBD_DISK = {"Inconsistent", "Outdated", "DUnknown", "Failed", "Diskless"}


def match_rdqm_findings(
    raw: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None = None,
) -> list[RCSFinding]:
    """Build RDQM findings.

    Expected raw shape:
        {
            "rdqm_status": {"qm_name": "...", "ha_state": "Online",
                            "running_node": "rdqm-1",
                            "preferred_location": "rdqm-1",
                            "ha_replicas": [{"node": "...", "status": "..."}]},
            "pacemaker": {"total_nodes": 3, "online_nodes": [...],
                          "offline_nodes": [...],
                          "failed_resources": [{"resource", "node", "status"}]},
            "drbd": [{"resource": "...", "connection_state": "...",
                      "role": "Primary", "peer_role": "Secondary",
                      "disk_state": "UpToDate", "peer_disk_state": "UpToDate",
                      "split_brain": False}, ...],
        }
    """
    findings: list[RCSFinding] = []
    rdqm = raw.get("rdqm_status") or {}
    pace = raw.get("pacemaker") or {}
    drbd_resources: list[dict[str, Any]] = raw.get("drbd") or []

    if not rdqm and not pace and not drbd_resources:
        return findings

    findings.extend(_check_pacemaker_quorum(pace, registry, mq_version))
    findings.extend(_check_offline_nodes(pace, registry, mq_version))
    findings.extend(_check_failed_resources(pace, registry, mq_version))
    findings.extend(_check_drbd_split_brain(drbd_resources, registry, mq_version))
    findings.extend(_check_drbd_connection(drbd_resources, registry, mq_version))
    findings.extend(_check_drbd_disk_state(drbd_resources, registry, mq_version))
    findings.extend(_check_rdqm_no_running_node(rdqm, registry, mq_version))
    return findings


# --- individual checks -----------------------------------------------------


def _check_pacemaker_quorum(
    pace: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    if not pace:
        return []
    online: list[str] = list(pace.get("online_nodes") or [])
    total = int(pace.get("total_nodes") or 0)
    if total <= 0:
        return []
    required = (total // 2) + 1
    if len(online) >= required:
        return []
    return [
        RCSFinding(
            issue=(f"Pacemaker quorum lost: {len(online)}/{total} nodes online (need {required})"),
            severity=Severity.CRITICAL,
            reason_code=None,
            amq_code=None,
            root_cause=(
                "Pacemaker has lost quorum. Without a majority of nodes, the "
                "cluster cannot safely run resources and RDQM-managed QMs "
                "are stopped or fenced. Investigate node connectivity, "
                "fencing devices, and pacemaker.service status on each host."
            ),
            fix_steps=("crm_mon -1", "rdqmstatus"),
            verify_commands=("crm_mon -1",),
            doc_refs=tuple(registry.lookup_topic("rdqm_pacemaker", mq_version)),
            confidence="High",
            evidence={
                "online": ",".join(online),
                "total": str(total),
                "required": str(required),
            },
        )
    ]


def _check_offline_nodes(
    pace: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    offline: list[str] = list(pace.get("offline_nodes") or [])
    if not offline:
        return []
    # Quorum check is separate (CRITICAL); this is HIGH for the individual nodes.
    return [
        RCSFinding(
            issue=f"Pacemaker reports {len(offline)} offline node(s): {', '.join(offline)}",
            severity=Severity.HIGH,
            reason_code=None,
            amq_code=None,
            root_cause=(
                "One or more cluster nodes are offline from Pacemaker's view. "
                "Causes typically include the node being powered off, a "
                "network partition, or pacemaker.service / corosync stopped. "
                "The cluster runs degraded until the node returns."
            ),
            fix_steps=("crm_mon -1", "rdqmstatus"),
            verify_commands=("crm_mon -1",),
            doc_refs=tuple(registry.lookup_topic("rdqm_pacemaker", mq_version)),
            confidence="High",
            evidence={"offline": ",".join(offline)},
        )
    ]


def _check_failed_resources(
    pace: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    failed = pace.get("failed_resources") or []
    if not failed:
        return []
    findings: list[RCSFinding] = []
    for f in failed:
        resource = str(f.get("resource", "<unknown>"))
        node = str(f.get("node", ""))
        status = str(f.get("status", ""))
        findings.append(
            RCSFinding(
                issue=f"Pacemaker resource {resource} failed on {node or 'unknown node'}",
                severity=Severity.HIGH,
                reason_code=None,
                amq_code=None,
                root_cause=(
                    f"Resource {resource} reports {status or 'failed'}. Failed "
                    "resources block automatic failover and require manual "
                    "investigation of the underlying service (RDQM agent, "
                    "filesystem, virtual IP, or DRBD device)."
                ),
                fix_steps=("crm_mon -1", "rdqmstatus"),
                verify_commands=("crm_mon -1",),
                doc_refs=tuple(registry.lookup_topic("rdqm_troubleshooting", mq_version)),
                confidence="Medium",
                evidence={"resource": resource, "node": node, "status": status},
            )
        )
    return findings


def _check_drbd_split_brain(
    drbd_resources: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    findings: list[RCSFinding] = []
    for d in drbd_resources:
        if not d.get("split_brain"):
            continue
        name = str(d.get("resource", "<unknown>"))
        findings.append(
            RCSFinding(
                issue=f"DRBD split-brain detected on resource {name}",
                severity=Severity.CRITICAL,
                reason_code=None,
                amq_code=None,
                root_cause=(
                    "Both peers have written to the same DRBD resource while "
                    "disconnected, producing divergent block-level state. "
                    "Manual operator action is required to choose the "
                    "authoritative copy and discard the other — the MCP "
                    "intentionally does NOT suggest the destructive commands."
                ),
                fix_steps=(f"drbdadm status {name}", "rdqmstatus", "crm_mon -1"),
                verify_commands=(f"drbdadm status {name}",),
                doc_refs=tuple(registry.lookup_topic("rdqm_split_brain", mq_version)),
                confidence="High",
                evidence={"resource": name},
            )
        )
    return findings


def _check_drbd_connection(
    drbd_resources: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    findings: list[RCSFinding] = []
    for d in drbd_resources:
        if d.get("split_brain"):
            continue  # already covered as CRITICAL above
        name = str(d.get("resource", "<unknown>"))
        conn = str(d.get("connection_state", "")).strip()
        if not conn:
            continue
        if conn == "Connected":
            continue
        if conn in _BAD_DRBD_CONN:
            severity = Severity.HIGH
            cause = (
                f"DRBD resource {name} reports {conn}: replication is not "
                "active. Check inter-node network reachability, DRBD ports "
                "(7788+), and any firewall changes."
            )
        elif conn in _DEGRADED_DRBD_CONN:
            severity = Severity.MEDIUM
            cause = (
                f"DRBD resource {name} is in {conn}: a sync is in progress "
                "or paused. Monitor — promote-blocking states extend RPO."
            )
        else:
            severity = Severity.MEDIUM
            cause = (
                f"DRBD resource {name} reports unexpected connection state "
                f"{conn}. Verify against the DRBD manual."
            )
        findings.append(
            RCSFinding(
                issue=f"DRBD resource {name} connection_state={conn}",
                severity=severity,
                reason_code=None,
                amq_code=None,
                root_cause=cause,
                fix_steps=(f"drbdadm status {name}", "rdqmstatus"),
                verify_commands=(f"drbdadm status {name}",),
                doc_refs=tuple(registry.lookup_topic("rdqm_troubleshooting", mq_version)),
                confidence="Medium",
                evidence={"resource": name, "connection_state": conn},
            )
        )
    return findings


def _check_drbd_disk_state(
    drbd_resources: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    findings: list[RCSFinding] = []
    for d in drbd_resources:
        if d.get("split_brain"):
            continue
        name = str(d.get("resource", "<unknown>"))
        for who, key in (("local", "disk_state"), ("peer", "peer_disk_state")):
            state = str(d.get(key, "")).strip()
            if not state or state == "UpToDate":
                continue
            if state not in _BAD_DRBD_DISK:
                continue
            findings.append(
                RCSFinding(
                    issue=f"DRBD {who} disk on {name} is {state}",
                    severity=Severity.HIGH,
                    reason_code=None,
                    amq_code=None,
                    root_cause=(
                        f"The {who} disk for DRBD resource {name} reports "
                        f"{state}. Promotion of this side risks data loss "
                        "until the disk returns to UpToDate via a successful "
                        "resync from a healthy peer."
                    ),
                    fix_steps=(f"drbdadm status {name}", "rdqmstatus"),
                    verify_commands=(f"drbdadm status {name}",),
                    doc_refs=tuple(registry.lookup_topic("rdqm_troubleshooting", mq_version)),
                    confidence="High",
                    evidence={"resource": name, "side": who, "state": state},
                )
            )
    return findings


def _check_rdqm_no_running_node(
    rdqm: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    if not rdqm:
        return []
    qm = str(rdqm.get("qm_name", "<unknown>"))
    running = str(rdqm.get("running_node") or "").strip()
    ha_state = str(rdqm.get("ha_state", "")).strip()
    if running:
        return []
    return [
        RCSFinding(
            issue=f"RDQM {qm} has no running node (ha_state={ha_state or 'unknown'})",
            severity=Severity.CRITICAL,
            reason_code=None,
            amq_code=None,
            root_cause=(
                "rdqmstatus reports no node currently running the QM. "
                "Pacemaker may have failed to start the resource, the "
                "preferred node may be offline, or DRBD is not promoting. "
                "The QM is unavailable to applications."
            ),
            fix_steps=("rdqmstatus", "crm_mon -1"),
            verify_commands=("rdqmstatus",),
            doc_refs=tuple(registry.lookup_topic("rdqm_overview", mq_version)),
            confidence="Medium",
            evidence={"qm_name": qm, "ha_state": ha_state},
        )
    ]
