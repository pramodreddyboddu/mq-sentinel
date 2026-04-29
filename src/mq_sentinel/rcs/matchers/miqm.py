"""Multi-Instance Queue Manager (MIQM) pattern matchers.

Inspects active/standby state, shared filesystem lock health, and recent
failover history. Read-only — never suggests endmqm/strmqm/dltmqm.
"""

from __future__ import annotations

import re
from typing import Any

from mq_sentinel.rcs.engine import RCSFinding, Severity
from mq_sentinel.rcs.kc_registry import KCRegistry

_AMQ_FAILOVER_RE = re.compile(r"\bAMQ7228\b|\bAMQ7230\b|\bAMQ7232\b")


def match_miqm_findings(
    raw: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None = None,
) -> list[RCSFinding]:
    """Build MIQM findings.

    Expected raw shape:
        {
            "instances": [{"qm_name": "QM1", "host": "h1", "status": "Running",
                           "role": "ACTIVE", "instance_type": "ACTIVE"|"STANDBY"|"NONE"}],
            "standby_permitted": True,
            "shared_fs_path": "/var/mqm/shared",
            "shared_fs_ok": True,
            "error_log_tail": "..."
        }
    """
    findings: list[RCSFinding] = []
    instances: list[dict[str, Any]] = raw.get("instances") or []
    permitted = bool(raw.get("standby_permitted"))
    fs_ok = raw.get("shared_fs_ok")
    log_tail = str(raw.get("error_log_tail") or "")

    if not instances and fs_ok is None and not log_tail:
        return findings

    findings.extend(_check_no_active(instances, registry, mq_version))
    findings.extend(_check_standby_permission(permitted, instances, registry, mq_version))
    findings.extend(_check_dual_active(instances, registry, mq_version))
    findings.extend(_check_shared_fs(fs_ok, raw, registry, mq_version))
    findings.extend(_check_failover_history(log_tail, registry, mq_version))
    return findings


def _check_no_active(
    instances: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    if not instances:
        return []
    actives = [
        i for i in instances
        if str(i.get("instance_type", i.get("role", ""))).upper() == "ACTIVE"
    ]
    if actives:
        return []
    return [
        RCSFinding(
            issue="MIQM has no ACTIVE instance",
            severity=Severity.CRITICAL,
            reason_code=None,
            amq_code=None,
            root_cause=(
                "Neither configured instance reports ACTIVE. Applications cannot "
                "connect until an instance assumes the active role. Check shared "
                "filesystem availability and lease renewal on each host."
            ),
            fix_steps=("dspmq -o standby", "dspmq -x"),
            verify_commands=("dspmq -x",),
            doc_refs=tuple(registry.lookup_topic("miqm_troubleshooting", mq_version)),
            confidence="High",
            evidence={"total_instances": str(len(instances))},
        )
    ]


def _check_standby_permission(
    permitted: bool,
    instances: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    if permitted or not instances:
        return []
    return [
        RCSFinding(
            issue="MIQM standby instances are not permitted",
            severity=Severity.HIGH,
            reason_code=None,
            amq_code=None,
            root_cause=(
                "The QM was started without `-x` (or STANDBY(NOT PERMITTED) is "
                "configured). Failover will not happen automatically — the active "
                "instance is a single point of failure."
            ),
            fix_steps=("dspmq -o standby",),
            verify_commands=("dspmq -o standby",),
            doc_refs=tuple(registry.lookup_topic("miqm_overview", mq_version)),
            confidence="High",
            evidence={"standby_permitted": "false"},
        )
    ]


def _check_dual_active(
    instances: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    actives = [
        i for i in instances
        if str(i.get("instance_type", i.get("role", ""))).upper() == "ACTIVE"
    ]
    if len(actives) <= 1:
        return []
    hosts = ", ".join(str(i.get("host", "?")) for i in actives)
    return [
        RCSFinding(
            issue=f"MIQM reports {len(actives)} ACTIVE instances ({hosts})",
            severity=Severity.CRITICAL,
            reason_code=None,
            amq_code=None,
            root_cause=(
                "Only one MIQM instance can hold the shared-filesystem lock. "
                "Two ACTIVE instances usually indicates the shared filesystem "
                "lost its lock semantics (NFS misconfiguration, GPFS quorum "
                "issue) — risking message corruption."
            ),
            fix_steps=("dspmq -x", "dspmq -o standby"),
            verify_commands=("dspmq -x",),
            doc_refs=tuple(registry.lookup_topic("miqm_troubleshooting", mq_version)),
            confidence="High",
            evidence={"active_count": str(len(actives)), "hosts": hosts},
        )
    ]


def _check_shared_fs(
    fs_ok: Any,
    raw: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    if fs_ok is None or fs_ok:
        return []
    path = str(raw.get("shared_fs_path") or "")
    return [
        RCSFinding(
            issue=f"MIQM shared filesystem health probe failed ({path or 'unknown path'})",
            severity=Severity.HIGH,
            reason_code=None,
            amq_code=None,
            root_cause=(
                "The shared filesystem hosting the QM data + log is unreachable "
                "or denying writes. Without it, the active instance will fence "
                "itself and standby cannot promote either."
            ),
            fix_steps=("dspmq -x", "dspmq -o standby"),
            verify_commands=("dspmq -x",),
            doc_refs=tuple(registry.lookup_topic("miqm_troubleshooting", mq_version)),
            confidence="Medium",
            evidence={"path": path},
        )
    ]


def _check_failover_history(
    log_tail: str,
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    if not log_tail or not _AMQ_FAILOVER_RE.search(log_tail):
        return []
    matches = _AMQ_FAILOVER_RE.findall(log_tail)
    return [
        RCSFinding(
            issue=f"MIQM error log shows {len(matches)} failover-related event(s)",
            severity=Severity.MEDIUM,
            reason_code=None,
            amq_code=None,
            root_cause=(
                "Recent AMQ7228/AMQ7230/AMQ7232 events indicate the QM "
                "transitioned active/standby. Investigate the trigger to "
                "ensure the cause is understood (network, FS, planned)."
            ),
            fix_steps=("dspmq -x",),
            verify_commands=("dspmq -x",),
            doc_refs=tuple(registry.lookup_topic("miqm_troubleshooting", mq_version)),
            confidence="Medium",
            evidence={"failover_events": str(len(matches))},
        )
    ]
