"""Native HA pattern matchers — replica state, quorum, log replication, CRR.

Inputs are NATIVEHASTATUS rows + (optional) RECOVERYGROUP / CRR fields. All
recommended fix steps are read-only DISPLAY/PING — failover, suspend, resume
are intentionally NEVER suggested as commands the operator should run blind.
"""

from __future__ import annotations

from typing import Any

from mq_sentinel.rcs.engine import RCSFinding, RemediationScenario, Severity
from mq_sentinel.rcs.kc_registry import KCRegistry

_LAG_PCT_MEDIUM = 95  # < 95% replay → MEDIUM
_LAG_PCT_HIGH = 80  # < 80% replay → HIGH
_LAG_BYTES_HIGH = 10_000_000  # 10 MB
_CRR_LAG_HIGH = 60  # seconds
_CRR_LAG_CRITICAL = 300  # seconds


def match_native_ha_findings(
    raw: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None = None,
) -> list[RCSFinding]:
    """Build Native HA findings.

    Expected raw shape:
        {
            "instances": [{"INSTANCE": "QM-0", "ROLE": "ACTIVE",
                           "STATUS": "RUNNING", "INSYNC": "YES",
                           "BACKLOG": "0", "REPLAYPCT": "100"}, ...],
            "quorum_required": 2,
            "crr": {"enabled": True, "lag_seconds": 30,
                    "recovery_group": "EAST", "role": "LIVE"},
            "this_instance": "QM-0",
        }

    Empty `instances` returns no findings (caller targets non-HA QM).
    """
    findings: list[RCSFinding] = []
    instances: list[dict[str, Any]] = raw.get("instances", []) or []
    if not instances and not raw.get("crr"):
        return findings

    findings.extend(_check_quorum(instances, raw, registry, mq_version))
    findings.extend(_check_active_instance(instances, registry, mq_version))
    findings.extend(_check_replicas(instances, registry, mq_version))
    findings.extend(_check_log_replay_lag(instances, registry, mq_version))
    findings.extend(_check_crr_lag(raw, registry, mq_version))
    return findings


# --- individual checks -----------------------------------------------------


def _check_quorum(
    instances: list[dict[str, Any]],
    raw: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    if not instances:
        return []
    in_sync = [i for i in instances if str(i.get("INSYNC", "")).upper() == "YES"]
    required = int(raw.get("quorum_required") or _required_quorum(len(instances)))
    if len(in_sync) >= required:
        return []
    return [
        RCSFinding(
            issue=(
                f"Native HA quorum at risk: {len(in_sync)}/{len(instances)} "
                f"replicas in sync (need {required})"
            ),
            severity=Severity.CRITICAL,
            reason_code=None,
            amq_code=None,
            root_cause=(
                "Fewer in-sync replicas than the required quorum. The active "
                "instance can continue to serve while a single peer remains, "
                "but a further loss will halt the QM. Investigate replica "
                "connectivity, log device health, and pod scheduling."
            ),
            fix_steps=(
                "DISPLAY NATIVEHASTATUS",
                "DISPLAY QMSTATUS",
            ),
            verify_commands=("DISPLAY NATIVEHASTATUS",),
            doc_refs=tuple(registry.lookup_topic("native_ha_quorum_lost", mq_version)),
            confidence="High",
            evidence={
                "in_sync": str(len(in_sync)),
                "total": str(len(instances)),
                "required": str(required),
            },
            remediation_steps=(
                RemediationScenario(
                    scenario="Restart unhealthy replica pods in Kubernetes",
                    commands=("kubectl -n mq rollout restart statefulset/QM_NAME",),
                    notes="Replace 'mq' namespace and statefulset name with yours. "
                    "Watch INSYNC=YES return for each replica.",
                ),
                RemediationScenario(
                    scenario="Verify PVC + storage class health",
                    commands=(
                        "kubectl -n mq get pvc",
                        "kubectl -n mq describe pvc data-QM_NAME-1",
                    ),
                    notes="Common quorum-loss cause: a replica's PVC stuck in Pending.",
                ),
            ),
        )
    ]


def _check_active_instance(
    instances: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    actives = [i for i in instances if str(i.get("ROLE", "")).upper() == "ACTIVE"]
    if len(actives) == 1:
        return []
    if len(actives) == 0:
        return [
            RCSFinding(
                issue="Native HA group has no ACTIVE instance",
                severity=Severity.CRITICAL,
                reason_code=None,
                amq_code=None,
                root_cause=(
                    "No instance reports ROLE(ACTIVE). The QM is offline to "
                    "applications until an instance is elected active. This "
                    "usually follows a quorum loss or a coordinated restart."
                ),
                fix_steps=("DISPLAY NATIVEHASTATUS", "DISPLAY QMSTATUS"),
                verify_commands=("DISPLAY NATIVEHASTATUS",),
                doc_refs=tuple(registry.lookup_topic("native_ha_quorum_lost", mq_version)),
                confidence="High",
                evidence={"actives": "0", "total": str(len(instances))},
                remediation_steps=(
                    RemediationScenario(
                        scenario="Election will run automatically once quorum returns",
                        commands=(
                            "kubectl -n mq get pods -l app.kubernetes.io/name=ibm-mq",
                            "kubectl -n mq logs QM_NAME-0 | tail -100",
                        ),
                        notes="Bring replicas back online (PVC, node, network). MQ elects "
                        "ACTIVE within seconds of quorum returning.",
                    ),
                ),
            )
        ]
    # > 1 active = split-brain symptom
    return [
        RCSFinding(
            issue=f"Native HA reports {len(actives)} ACTIVE instances (split-brain)",
            severity=Severity.CRITICAL,
            reason_code=None,
            amq_code=None,
            root_cause=(
                "Two or more replicas claim the ACTIVE role simultaneously. "
                "This indicates a split-brain or stale election state. Stop "
                "client traffic and engage IBM support before manual intervention."
            ),
            fix_steps=("DISPLAY NATIVEHASTATUS",),
            verify_commands=("DISPLAY NATIVEHASTATUS",),
            doc_refs=tuple(registry.lookup_topic("native_ha_quorum_lost", mq_version)),
            confidence="High",
            evidence={"actives": str(len(actives))},
            remediation_steps=(
                RemediationScenario(
                    scenario="STOP client traffic, then engage IBM support",
                    commands=(
                        "# 1. Update upstream load balancer to drain traffic.",
                        "# 2. Open IBM support case — Native HA split-brain.",
                        "# 3. Do NOT manually elect — risk of data loss.",
                    ),
                    notes="⚠️ This is rare and dangerous. Two ACTIVE replicas means the "
                    "quorum logic failed, possibly due to a network partition during "
                    "a leader transition. Manual override risks unrecoverable data loss.",
                ),
            ),
        )
    ]


def _check_replicas(
    instances: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    findings: list[RCSFinding] = []
    for inst in instances:
        role = str(inst.get("ROLE", "")).upper()
        if role == "ACTIVE":
            continue
        name = str(inst.get("INSTANCE", "<unknown>"))
        status = str(inst.get("STATUS", "")).upper()
        in_sync = str(inst.get("INSYNC", "")).upper()
        if status not in {"RUNNING", "REPLICA"} or in_sync == "NO":
            findings.append(
                RCSFinding(
                    issue=(
                        f"Native HA replica {name} status={status or 'UNKNOWN'} "
                        f"insync={in_sync or 'UNKNOWN'}"
                    ),
                    severity=Severity.HIGH,
                    reason_code=None,
                    amq_code="AMQ3209",
                    root_cause=(
                        "Replica is not actively replicating. Common causes: "
                        "pod scheduled on tainted node, persistent volume "
                        "unavailable, network partition between replicas, or "
                        "the replica process not yet caught up after restart."
                    ),
                    fix_steps=(
                        "DISPLAY NATIVEHASTATUS",
                        "DISPLAY QMSTATUS",
                    ),
                    verify_commands=("DISPLAY NATIVEHASTATUS",),
                    doc_refs=tuple(registry.lookup_amq("AMQ3209", mq_version)),
                    confidence="High",
                    evidence={
                        "instance": name,
                        "role": role or "UNKNOWN",
                        "status": status or "UNKNOWN",
                        "insync": in_sync or "UNKNOWN",
                    },
                    remediation_steps=(
                        RemediationScenario(
                            scenario="Restart the unhealthy replica pod",
                            commands=(f"kubectl -n mq delete pod {name}",),
                            notes=(
                                "StatefulSet recreates it; INSYNC=YES returns "
                                "once log replay completes."
                            ),
                        ),
                        RemediationScenario(
                            scenario="Inspect the replica's log for replication errors",
                            commands=(
                                f"kubectl -n mq logs {name} --tail=200 | grep -E 'AMQ32|AMQ30'",
                            ),
                            notes=(
                                "Look for AMQ3209/AMQ3035 series — those name the "
                                "underlying cause."
                            ),
                        ),
                    ),
                )
            )
    return findings


def _check_log_replay_lag(
    instances: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    findings: list[RCSFinding] = []
    for inst in instances:
        if str(inst.get("ROLE", "")).upper() == "ACTIVE":
            continue
        name = str(inst.get("INSTANCE", "<unknown>"))
        try:
            pct = int(inst.get("REPLAYPCT", 100))
        except (TypeError, ValueError):
            pct = 100
        try:
            backlog = int(inst.get("BACKLOG", 0))
        except (TypeError, ValueError):
            backlog = 0

        severity: Severity | None = None
        reason: str | None = None
        if pct < _LAG_PCT_HIGH or backlog > _LAG_BYTES_HIGH:
            severity = Severity.HIGH
            reason = (
                f"Replica {name} is far behind the active log "
                f"({pct}% replay, {backlog} bytes backlog). At this rate the "
                "replica may not catch up under sustained load."
            )
        elif pct < _LAG_PCT_MEDIUM:
            severity = Severity.MEDIUM
            reason = (
                f"Replica {name} replay is at {pct}%. Watch for trend; if "
                "replay percentage continues to drop, escalate to HIGH."
            )

        if severity is None:
            continue

        findings.append(
            RCSFinding(
                issue=f"Native HA replica {name} log replay lag ({pct}%)",
                severity=severity,
                reason_code=None,
                amq_code=None,
                root_cause=reason or "",
                fix_steps=(
                    "DISPLAY NATIVEHASTATUS",
                    "DISPLAY QMSTATUS",
                ),
                verify_commands=("DISPLAY NATIVEHASTATUS",),
                doc_refs=tuple(registry.lookup_topic("native_ha_log_replication", mq_version)),
                confidence="High",
                evidence={
                    "instance": name,
                    "replay_pct": str(pct),
                    "backlog_bytes": str(backlog),
                },
                remediation_steps=(
                    RemediationScenario(
                        scenario="Increase IOPS on the lagging replica's storage",
                        commands=(
                            f"kubectl -n mq describe pod {name} | grep -A5 'Volumes:'",
                            "# Then resize PVC (StorageClass must support it):",
                            "kubectl -n mq patch pvc data-QM_NAME-1 -p \\\n"
                            '  \'{"spec":{"resources":{"requests":{"storage":"200Gi"}}}}\'',
                        ),
                        notes="Persistent lag with low backlog often means IOPS-bound. "
                        "Resize the PVC or migrate to a faster StorageClass.",
                    ),
                ),
            )
        )
    return findings


def _check_crr_lag(
    raw: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    crr = raw.get("crr") or {}
    if not crr or not crr.get("enabled"):
        return []
    try:
        lag = int(crr.get("lag_seconds", 0))
    except (TypeError, ValueError):
        lag = 0
    if lag < _CRR_LAG_HIGH:
        return []
    severity = Severity.CRITICAL if lag >= _CRR_LAG_CRITICAL else Severity.HIGH
    rg = str(crr.get("recovery_group", ""))
    role = str(crr.get("role", ""))
    return [
        RCSFinding(
            issue=f"Cross-region replication lag is {lag}s (group {rg or 'UNKNOWN'})",
            severity=severity,
            reason_code=None,
            amq_code=None,
            root_cause=(
                f"CRR async replication to recovery group {rg or '<unknown>'} "
                f"is {lag} seconds behind. RPO degrades linearly with lag; "
                "investigate inter-region network and replica health."
            ),
            fix_steps=(
                "DISPLAY QMSTATUS RECOVERYGROUP",
                "DISPLAY NATIVEHASTATUS",
            ),
            verify_commands=("DISPLAY QMSTATUS RECOVERYGROUP",),
            doc_refs=tuple(registry.lookup_topic("native_ha_crr", mq_version)),
            confidence="High",
            evidence={
                "lag_seconds": str(lag),
                "recovery_group": rg,
                "role": role,
            },
            remediation_steps=(
                RemediationScenario(
                    scenario="Investigate inter-region network bandwidth/latency",
                    commands=(
                        "# From the LIVE region, to the RECOVERY region's CRR endpoint:",
                        "iperf3 -c recovery.region.example -t 30",
                        "ping -c 100 recovery.region.example",
                    ),
                    notes="CRR throughput tracks available bandwidth. RTT > 50ms with sustained "
                    "write load is a common cause of growing lag.",
                ),
                RemediationScenario(
                    scenario="Verify recovery-group QMs are healthy",
                    commands=(
                        "# In the RECOVERY region:",
                        "DISPLAY QMSTATUS",
                        "DISPLAY NATIVEHASTATUS",
                    ),
                    notes="If the recovery side has its own replica issue, CRR lag will grow "
                    "regardless of network.",
                ),
            ),
        )
    ]


# --- helpers ---------------------------------------------------------------


def _required_quorum(total: int) -> int:
    """Standard majority quorum: floor(n/2) + 1."""
    return (total // 2) + 1
