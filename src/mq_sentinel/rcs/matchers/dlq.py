"""DLQ pattern matchers — group headers by reason code and produce findings.

Inputs are MQDLH header projections (see connectors.base.DLQHeader). Bodies
are never available here by construction.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from mq_sentinel.connectors.base import DLQHeader
from mq_sentinel.rcs.engine import RCSFinding, RemediationScenario, Severity
from mq_sentinel.rcs.kc_registry import KCRegistry

# Severity per reason code. Conservative — bias toward HIGH on auth and full-Q
# conditions; MEDIUM for too-big and truncation; LOW for backout-flow.
_SEVERITY: dict[int, Severity] = {
    2035: Severity.HIGH,
    2080: Severity.MEDIUM,  # truncated_msg_failed
    2030: Severity.MEDIUM,  # msg_too_big_for_q
    2051: Severity.HIGH,  # put_inhibited
    2053: Severity.HIGH,  # q_full
    2079: Severity.LOW,  # truncated_msg_accepted
}

_DLQ_BACKOUT_THRESHOLD = 5


def match_dlq_findings(
    browse: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None = None,
) -> list[RCSFinding]:
    """Build findings from a BrowseResult-shaped dict.

    Expected shape:
        {
            "queue_name": "SYSTEM.DEAD.LETTER.QUEUE",
            "qm_name": "QM1",
            "queue_depth": 1234,
            "sample_size": 50,
            "headers": [DLQHeader-like dicts with reason_code, dest_q_name, ...]
        }
    """
    findings: list[RCSFinding] = []
    headers: list[dict[str, Any]] = browse.get("headers", []) or []
    queue_name = str(browse.get("queue_name", "SYSTEM.DEAD.LETTER.QUEUE"))
    queue_depth = int(browse.get("queue_depth", 0) or 0)
    sample_size = int(browse.get("sample_size", len(headers)) or len(headers))

    if queue_depth == 0 and not headers:
        return findings

    # Top-line: queue depth itself.
    if queue_depth > 0:
        findings.append(_finding_dlq_depth(queue_name, queue_depth, sample_size))

    # Group by reason code.
    by_reason: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for h in headers:
        reason = int(h.get("reason_code", 0) or 0)
        by_reason[reason].append(h)

    for reason, group in sorted(by_reason.items()):
        if reason == 0:
            continue
        findings.append(_finding_for_reason(queue_name, reason, group, registry, mq_version))

    # Backout-loop detection.
    high_backout = [
        h for h in headers if int(h.get("backout_count", 0) or 0) >= _DLQ_BACKOUT_THRESHOLD
    ]
    if high_backout:
        findings.append(_finding_backout_loop(queue_name, high_backout))

    return findings


def _finding_dlq_depth(queue_name: str, depth: int, sample: int) -> RCSFinding:
    severity = (
        Severity.CRITICAL
        if depth > 10_000
        else Severity.HIGH
        if depth > 1_000
        else Severity.MEDIUM
        if depth > 100
        else Severity.LOW
    )
    return RCSFinding(
        issue=f"Dead-letter queue {queue_name} depth={depth}",
        severity=severity,
        reason_code=None,
        amq_code=None,
        root_cause=(
            f"The DLQ has {depth} message(s); the MCP inspected the first {sample} "
            "headers (bodies never read). Persistent DLQ growth indicates "
            "downstream queues are unavailable, applications are putting to "
            "non-existent queues, or message handling is rejecting messages."
        ),
        fix_steps=(
            f"DISPLAY QUEUE('{queue_name}') CURDEPTH MAXDEPTH MSGAGE",
            "DISPLAY QUEUE(*) WHERE(CURDEPTH GT 0)",
            f"DISPLAY QSTATUS('{queue_name}') ALL",
        ),
        verify_commands=(f"DISPLAY QUEUE('{queue_name}') CURDEPTH",),
        doc_refs=(),
        confidence="High",
        evidence={"queue_name": queue_name, "queue_depth": str(depth), "sample_size": str(sample)},
        remediation_steps=(
            RemediationScenario(
                scenario="Drain processed messages back to their destinations",
                commands=(
                    "# Use IBM-supplied runmqdlq with a curated rules table:",
                    "runmqdlq SYSTEM.DEAD.LETTER.QUEUE QM_NAME < /etc/mqm/dlq.rules",
                ),
                notes="Configure /etc/mqm/dlq.rules per IBM KC 'Sample DLQ handler rules table'. "
                "Test the rules in a non-prod QM first — destructive consume.",
            ),
            RemediationScenario(
                scenario="Move messages off DLQ for manual inspection",
                commands=(
                    "# Browse-only sample (does NOT delete):",
                    f"dmpmqmsg -m QM_NAME -i {queue_name} -f /tmp/dlq.dump -k 0 -K 50",
                ),
                notes="Read-only browse; safe to run. After inspection, decide whether to "
                "requeue via runmqdlq or accept loss with CLEAR.",
            ),
        ),
    )


def _finding_for_reason(
    queue_name: str,
    reason: int,
    group: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> RCSFinding:
    refs = registry.lookup_reason(reason, mq_version)
    severity = _SEVERITY.get(reason, Severity.MEDIUM)

    dest_counts: Counter[str] = Counter(str(h.get("dest_q_name", "")) for h in group)
    apps: Counter[str] = Counter(str(h.get("put_application_name", "")) for h in group)
    top_dest = ", ".join(f"{q}={n}" for q, n in dest_counts.most_common(3) if q)
    top_apps = ", ".join(f"{a}={n}" for a, n in apps.most_common(3) if a)

    fix_steps = _fix_steps_for_reason(reason, dest_counts.most_common(1))

    top_dest_name = dest_counts.most_common(1)[0][0] if dest_counts else "<destination>"
    return RCSFinding(
        issue=f"DLQ contains {len(group)} message(s) with reason {reason}",
        severity=severity,
        reason_code=reason,
        amq_code=None,
        root_cause=_root_cause_for_reason(reason, top_dest, top_apps),
        fix_steps=fix_steps,
        verify_commands=(f"DISPLAY QUEUE('{queue_name}') CURDEPTH",),
        doc_refs=tuple(refs),
        confidence="High" if refs else "Medium",
        evidence={
            "reason_code": str(reason),
            "count": str(len(group)),
            "top_destinations": top_dest,
            "top_applications": top_apps,
        },
        remediation_steps=_remediation_for_reason(reason, top_dest_name),
    )


def _remediation_for_reason(reason: int, dest: str) -> tuple[RemediationScenario, ...]:
    """IBM-recommended fix recipes per DLQ reason code."""
    if reason == 2035:
        return (
            RemediationScenario(
                scenario="Grant putter the required permission on the destination queue",
                commands=(
                    f"SET AUTHREC PROFILE('{dest}') OBJTYPE(QUEUE) "
                    "PRINCIPAL('putter-user') AUTHADD(PUT, INQ)",
                ),
                notes="Replace 'putter-user' with the actual MCAUSER from the originating channel.",
            ),
        )
    if reason == 2080:
        return (
            RemediationScenario(
                scenario="Fix consumer buffer sizing (application change)",
                commands=(
                    "# No MQSC command — update the consumer to size its buffer to MAXMSGL.",
                ),
                notes="Application must call MQGET with a buffer >= queue MAXMSGL, or accept "
                "truncation with MQGMO_ACCEPT_TRUNCATED_MSG.",
            ),
        )
    if reason == 2030:
        return (
            RemediationScenario(
                scenario="Increase destination queue MAXMSGL",
                commands=(f"ALTER QLOCAL('{dest}') MAXMSGL(4194304)",),
                notes="4 MiB is the typical max. Channel MAXMSGL on inbound channels must "
                "also be >= this value: ALTER CHANNEL('...') MAXMSGL(...).",
            ),
            RemediationScenario(
                scenario="Increase QMGR MAXMSGL if multiple queues need higher limits",
                commands=("ALTER QMGR MAXMSGL(104857600)",),
                notes="100 MiB QMGR max. Set per-queue MAXMSGL appropriately afterwards.",
            ),
        )
    if reason == 2051:
        return (
            RemediationScenario(
                scenario="Re-enable PUT on the destination queue",
                commands=(f"ALTER QLOCAL('{dest}') PUT(ENABLED)",),
                notes="Only if disabling PUT was unintentional. Confirm with the team that "
                "owns the queue first.",
            ),
        )
    if reason == 2053:
        return (
            RemediationScenario(
                scenario="Drain the destination queue (consumer-side fix)",
                commands=(f"DISPLAY QSTATUS('{dest}') IPPROCS OPPROCS LGETDATE LGETTIME",),
                notes="If no consumer running (OPPROCS=0), start it. If consumer is slow, "
                "scale it. This is operational, not an MQSC fix.",
            ),
            RemediationScenario(
                scenario="Increase MAXDEPTH if it was undersized",
                commands=(f"ALTER QLOCAL('{dest}') MAXDEPTH(50000)",),
                notes="Use sparingly — large MAXDEPTH masks consumer-throughput problems.",
            ),
        )
    if reason == 2079:
        return (
            RemediationScenario(
                scenario="Fix consumer buffer sizing or accept truncation explicitly",
                commands=("# Application change — see MQGET with MQGMO_ACCEPT_TRUNCATED_MSG.",),
                notes="This reason means truncation succeeded but flagged. Either size the "
                "buffer properly or remove the MQGMO_FAIL_IF_QUIESCING / accept flag.",
            ),
        )
    return ()


def _root_cause_for_reason(reason: int, top_dest: str, top_apps: str) -> str:
    base = {
        2035: "Putter lacked authority on the destination queue (NOT_AUTHORIZED).",
        2080: "Receiving application supplied a buffer smaller than the message and "
        "did not accept truncation, so the message was rerouted to the DLQ.",
        2030: "Message exceeded the destination queue's MAXMSGL.",
        2051: "Destination queue had PUT(DISABLED) when the message arrived.",
        2053: "Destination queue was at MAXDEPTH (Q_FULL) when the message arrived.",
        2079: "Receiving application accepted a truncated message — likely a buffer "
        "sizing or schema mismatch on the consumer.",
    }.get(reason, f"DLQ messages with reason {reason}.")
    suffix = []
    if top_dest:
        suffix.append(f"Top destinations: {top_dest}.")
    if top_apps:
        suffix.append(f"Top putting apps: {top_apps}.")
    return " ".join([base, *suffix])


def _fix_steps_for_reason(reason: int, top_dest: list[tuple[str, int]]) -> tuple[str, ...]:
    dest = top_dest[0][0] if top_dest and top_dest[0][0] else "<destination>"
    if reason == 2035:
        return (
            f"DISPLAY AUTHREC OBJTYPE(QUEUE) PROFILE('{dest}')",
            "DISPLAY QMGR CONNAUTH",
        )
    if reason == 2080:
        return (
            f"DISPLAY QUEUE('{dest}') MAXMSGL",
            "DISPLAY CHANNEL(*) MAXMSGL",
        )
    if reason == 2030:
        return (
            f"DISPLAY QUEUE('{dest}') MAXMSGL",
            "DISPLAY QMGR MAXMSGL",
        )
    if reason == 2051:
        return (
            f"DISPLAY QUEUE('{dest}') PUT GET",
            f"DISPLAY QSTATUS('{dest}') ALL",
        )
    if reason == 2053:
        return (
            f"DISPLAY QUEUE('{dest}') CURDEPTH MAXDEPTH",
            f"DISPLAY QSTATUS('{dest}') ALL",
        )
    if reason == 2079:
        return (f"DISPLAY QUEUE('{dest}') MAXMSGL",)
    return (f"DISPLAY QUEUE('{dest}') ALL",)


def _finding_backout_loop(queue_name: str, headers: list[dict[str, Any]]) -> RCSFinding:
    counts = Counter(str(h.get("dest_q_name", "")) for h in headers)
    top = ", ".join(f"{q}={n}" for q, n in counts.most_common(3) if q)
    return RCSFinding(
        issue=f"DLQ contains {len(headers)} message(s) with backout_count >= "
        f"{_DLQ_BACKOUT_THRESHOLD}",
        severity=Severity.HIGH,
        reason_code=None,
        amq_code=None,
        root_cause=(
            "Messages have repeatedly failed processing on the original queue and "
            "rolled back. This typically indicates a poison message — verify the "
            "BOTHRESH / BOQNAME settings on the source queue."
        ),
        fix_steps=(
            f"DISPLAY QUEUE('{queue_name}') BOTHRESH BOQNAME",
            "DISPLAY QUEUE(*) WHERE(BOTHRESH GT 0)",
        ),
        verify_commands=(f"DISPLAY QUEUE('{queue_name}') CURDEPTH",),
        doc_refs=(),
        confidence="Medium",
        evidence={
            "queue_name": queue_name,
            "high_backout_count": str(len(headers)),
            "top_destinations": top,
        },
        remediation_steps=(
            RemediationScenario(
                scenario="Configure source-queue backout handling",
                commands=(
                    "ALTER QLOCAL('source.queue') BOTHRESH(5) BOQNAME('source.queue.BOQ')",
                    "DEFINE QLOCAL('source.queue.BOQ') REPLACE",
                ),
                notes="Replace 'source.queue' with the queue producing poison messages. "
                "BOTHRESH=5 is conservative; tune to your retry policy. After this, "
                "MQ routes the poison to the BOQ instead of looping on the source.",
            ),
            RemediationScenario(
                scenario="Inspect poison message headers manually",
                commands=(f"dmpmqmsg -m QM_NAME -i {queue_name} -f /tmp/poison.dump -k 0 -K 10",),
                notes="Browse-only. Look for malformed payloads, schema drift, or auth tokens.",
            ),
        ),
    )


def header_to_dict(h: DLQHeader) -> dict[str, Any]:
    """Convert a DLQHeader to the dict shape consumed by match_dlq_findings."""
    return {
        "reason_code": h.reason_code,
        "feedback": h.feedback,
        "put_application_name": h.put_application_name,
        "put_application_type": h.put_application_type,
        "put_date": h.put_date,
        "put_time": h.put_time,
        "dest_q_name": h.dest_q_name,
        "dest_q_mgr_name": h.dest_q_mgr_name,
        "backout_count": h.backout_count,
        "body_length": h.body_length,
        "msg_id_hash": h.msg_id_hash,
    }
