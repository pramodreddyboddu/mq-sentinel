"""z/OS Queue Sharing Group pattern matchers.

Inspects QSG membership, channel initiator (CHIN) status, page set utilization,
buffer pool free pages, and coupling facility (CF) structure status.

Read-only: no START/STOP CHINIT, FORMAT, or CF recovery commands appear in
fix_steps. Procedural guidance is via IBM Knowledge Center links.
"""

from __future__ import annotations

from typing import Any

from mq_sentinel.rcs.engine import RCSFinding, RemediationScenario, Severity
from mq_sentinel.rcs.kc_registry import KCRegistry

_PAGESET_HIGH = 80  # %
_PAGESET_CRITICAL = 95
_BUFFERPOOL_LOW_FREE_PCT = 10  # < 10% free pages → HIGH


def match_zos_findings(
    raw: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None = None,
) -> list[RCSFinding]:
    """Build z/OS QSG findings.

    Expected raw shape:
        {
            "group": {"qsg_name": "QSG1", "members": [{"name": "QM1", "status": "ACTIVE"}, ...]},
            "chin": {"status": "RUNNING"},
            "pagesets": [{"PSID": "0", "USEPCT": "55"}, ...],
            "bufferpools": [{"BUFFPOOL": "0", "FREEPCT": "5"}, ...],
            "cf_structures": [{"STRUCTURE": "APPLICATION1", "STATUS": "ACTIVE"}, ...],
        }
    """
    findings: list[RCSFinding] = []
    group = raw.get("group") or {}
    chin = raw.get("chin") or {}
    pagesets: list[dict[str, Any]] = raw.get("pagesets") or []
    bufferpools: list[dict[str, Any]] = raw.get("bufferpools") or []
    cf_structures: list[dict[str, Any]] = raw.get("cf_structures") or []

    if not (group or chin or pagesets or bufferpools or cf_structures):
        return findings

    findings.extend(_check_qsg_members(group, registry, mq_version))
    findings.extend(_check_chin(chin, registry, mq_version))
    findings.extend(_check_pagesets(pagesets, registry, mq_version))
    findings.extend(_check_bufferpools(bufferpools, registry, mq_version))
    findings.extend(_check_cf_structures(cf_structures, registry, mq_version))
    return findings


def _check_qsg_members(
    group: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    findings: list[RCSFinding] = []
    members = group.get("members") or []
    qsg = str(group.get("qsg_name") or "")
    for m in members:
        name = str(m.get("name", "<unknown>"))
        status = str(m.get("status", "")).upper()
        if status in {"ACTIVE", "RUNNING"}:
            continue
        findings.append(
            RCSFinding(
                issue=f"QSG member {name} status={status or 'UNKNOWN'}",
                severity=Severity.HIGH,
                reason_code=None,
                amq_code=None,
                root_cause=(
                    f"Queue manager {name} in QSG {qsg or 'unknown'} is not ACTIVE. "
                    "Inactive QSG members reduce capacity for shared-queue workload "
                    "and may indicate the QM is stopped, abended, or partitioned "
                    "from the coupling facility."
                ),
                fix_steps=("DISPLAY GROUP", "DISPLAY QMSTATUS"),
                verify_commands=("DISPLAY GROUP",),
                doc_refs=tuple(registry.lookup_topic("zos_qsg_overview", mq_version)),
                confidence="High",
                evidence={"qsg": qsg, "member": name, "status": status},
                remediation_steps=(
                    RemediationScenario(
                        scenario="Start the inactive QM (z/OS operator command)",
                        commands=(
                            f"/{name} START QMGR",
                            "DISPLAY GROUP",
                        ),
                        notes="z/OS console / SDSF. Replace {name} with the started-task prefix.",
                    ),
                ),
            )
        )
    return findings


def _check_chin(
    chin: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    if not chin:
        return []
    status = str(chin.get("status", "")).upper()
    if status in {"RUNNING", "ACTIVE", "STARTED"}:
        return []
    return [
        RCSFinding(
            issue=f"Channel initiator (CHIN) status is {status or 'UNKNOWN'}",
            severity=Severity.CRITICAL,
            reason_code=None,
            amq_code=None,
            root_cause=(
                "The CHIN address space is not running. All distributed channel "
                "traffic to and from this z/OS QM is halted. Investigate the "
                "CHIN log and JES output for abend codes."
            ),
            fix_steps=("DISPLAY QMSTATUS CHINIT", "DISPLAY CHSTATUS(*) ALL"),
            verify_commands=("DISPLAY QMSTATUS CHINIT",),
            doc_refs=tuple(registry.lookup_topic("zos_chin", mq_version)),
            confidence="High",
            evidence={"chin_status": status},
            remediation_steps=(
                RemediationScenario(
                    scenario="Start the channel initiator address space",
                    commands=(
                        "+CSQ8 START CHINIT",
                        "DISPLAY QMSTATUS CHINIT",
                    ),
                    notes="z/OS operator command (SDSF or console). Replace 'CSQ8' "
                    "with your QM's command prefix.",
                ),
            ),
        )
    ]


def _check_pagesets(
    pagesets: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    findings: list[RCSFinding] = []
    for ps in pagesets:
        psid = str(ps.get("PSID") or ps.get("psid") or "?")
        try:
            use_pct = int(ps.get("USEPCT") or ps.get("use_pct") or 0)
        except (TypeError, ValueError):
            use_pct = 0
        if use_pct < _PAGESET_HIGH:
            continue
        severity = Severity.CRITICAL if use_pct >= _PAGESET_CRITICAL else Severity.HIGH
        findings.append(
            RCSFinding(
                issue=f"Page set {psid} utilization is {use_pct}%",
                severity=severity,
                reason_code=None,
                amq_code=None,
                root_cause=(
                    f"Page set {psid} is {use_pct}% full. At 100% the QM cannot "
                    "accept further messages routed to queues backed by this page "
                    "set. Add an extension or expand the page set."
                ),
                fix_steps=(
                    f"DISPLAY USAGE PSID({psid})",
                    "DISPLAY QUEUE(*) STGCLASS",
                ),
                verify_commands=(f"DISPLAY USAGE PSID({psid})",),
                doc_refs=tuple(registry.lookup_topic("zos_pageset", mq_version)),
                confidence="High",
                evidence={"psid": psid, "use_pct": str(use_pct)},
                remediation_steps=(
                    RemediationScenario(
                        scenario="Expand the page set with an extension dataset",
                        commands=(
                            "# Allocate new dataset via JCL (sample):",
                            "//ALLOCNEW EXEC PGM=IEFBR14",
                            f"//NEWPS DD DSN=CSQ.PAGESET.PS{psid}.EXT01,DISP=(NEW,CATLG,DELETE),",
                            "//            SPACE=(CYL,(100,100,0)),LIKE=CSQ.PAGESET.PS{psid}",
                            "# Then define to MQ via CSQUTIL FORMAT/EXTEND or DSN command.",
                        ),
                        notes="Coordinate with z/OS storage team. Adding an extension is "
                        "non-disruptive but requires DASD allocation.",
                    ),
                    RemediationScenario(
                        scenario="Rebalance queues to a different page set",
                        commands=(
                            f"DISPLAY QUEUE(*) WHERE(STGCLASS LIKE 'PS{psid}*')",
                            "# Move high-traffic queues to a less-full STGCLASS:",
                            "ALTER QLOCAL('NOISY.QUEUE') STGCLASS('STGCLASS_FOR_PS2')",
                        ),
                        notes="STGCLASS change affects new messages only. Drain queue first "
                        "if you need existing messages migrated.",
                    ),
                ),
            )
        )
    return findings


def _check_bufferpools(
    bufferpools: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    findings: list[RCSFinding] = []
    for bp in bufferpools:
        bpid = str(bp.get("BUFFPOOL") or bp.get("bufferpool") or "?")
        try:
            free_pct = int(bp.get("FREEPCT") or bp.get("free_pct") or 100)
        except (TypeError, ValueError):
            free_pct = 100
        if free_pct >= _BUFFERPOOL_LOW_FREE_PCT:
            continue
        findings.append(
            RCSFinding(
                issue=f"Buffer pool {bpid} free pages at {free_pct}%",
                severity=Severity.HIGH,
                reason_code=None,
                amq_code=None,
                root_cause=(
                    f"Buffer pool {bpid} has only {free_pct}% free pages. "
                    "Low free counts cause page-stealing and degrade message "
                    "throughput. Increase the buffer pool size or rebalance "
                    "page set allocation."
                ),
                fix_steps=(f"DISPLAY USAGE BUFFPOOL({bpid})",),
                verify_commands=(f"DISPLAY USAGE BUFFPOOL({bpid})",),
                doc_refs=tuple(registry.lookup_topic("zos_bufferpool", mq_version)),
                confidence="High",
                evidence={"bufferpool": bpid, "free_pct": str(free_pct)},
                remediation_steps=(
                    RemediationScenario(
                        scenario="Increase buffer pool size dynamically",
                        commands=(
                            f"ALTER BUFFPOOL({bpid}) BUFFERS(50000)",
                            f"DISPLAY USAGE BUFFPOOL({bpid})",
                        ),
                        notes=(
                            "Persists across restart. Sized in 4KiB pages — 50,000 "
                            "buffers ≈ 200MB. Region size (REGION=) on the MSTR "
                            "JCL must accommodate."
                        ),
                    ),
                ),
            )
        )
    return findings


def _check_cf_structures(
    cf_structures: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    findings: list[RCSFinding] = []
    for s in cf_structures:
        name = str(s.get("STRUCTURE") or s.get("structure") or "<unknown>")
        status = str(s.get("STATUS") or s.get("status") or "").upper()
        if status in {"ACTIVE", "AVAILABLE"}:
            continue
        severity = (
            Severity.CRITICAL
            if status in {"FAILED", "DAMAGED", "FAILED-CONNECTED", "INACCESSIBLE"}
            else Severity.HIGH
        )
        findings.append(
            RCSFinding(
                issue=f"CF structure {name} status={status or 'UNKNOWN'}",
                severity=severity,
                reason_code=None,
                amq_code=None,
                root_cause=(
                    f"Coupling facility structure {name} is in {status or 'UNKNOWN'} "
                    "state. Shared queues backed by this structure are unavailable "
                    "until the structure is recovered or reallocated."
                ),
                fix_steps=(f"DISPLAY CFSTATUS({name}) ALL",),
                verify_commands=(f"DISPLAY CFSTATUS({name})",),
                doc_refs=tuple(registry.lookup_topic("zos_cf_structure", mq_version)),
                confidence="High",
                evidence={"structure": name, "status": status},
                remediation_steps=(
                    RemediationScenario(
                        scenario="Recover the failed structure (sysplex operator)",
                        commands=(
                            f"D XCF,STR,STRNAME={name}",
                            f"SETXCF FORCE,STR,STRNAME={name}",
                            "# Then re-allocate via CFRM policy ACTIVATE if needed.",
                        ),
                        notes="⚠️ SETXCF FORCE discards in-flight structure data. Engage IBM "
                        "Support before running. Verify alternate CF exists in CFRM policy first.",
                    ),
                ),
            )
        )
    return findings
