"""Cluster pattern matchers — partial repos, stale entries, suspended members,
unhealthy cluster channels.

Inputs are raw CLUSQMGR rows + DISPLAY QMGR REPOS/REPOSNL output. All
recommended fix steps are read-only (DISPLAY/PING). REFRESH CLUSTER is
mentioned only as KC-linked GUIDANCE — never as a fix step the operator
should run blind.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from mq_sentinel.rcs.engine import RCSFinding, Severity
from mq_sentinel.rcs.kc_registry import KCRegistry

_STALE_DAYS = 7
_BAD_CHANNEL_STATUS = {"RETRYING", "STOPPED", "PAUSED", "INACTIVE_FAILED"}


def match_cluster_findings(
    raw: dict[str, Any],
    registry: KCRegistry,
    mq_version: str | None = None,
) -> list[RCSFinding]:
    """Build cluster findings from CLUSQMGR rows + REPOS query output.

    Expected raw shape:
        {
            "clusqmgrs": [{CLUSQMGR, CLUSTER, QMTYPE, STATUS, CHANNEL,
                           CONNAME, DEFTYPE, SUSPEND, CLUSDATE, CLUSTIME}, ...],
            "repos": "REPOS()  REPOSNL(...)",  # raw text from DISPLAY QMGR
            "this_qm": "QMNAME",
        }
    """
    findings: list[RCSFinding] = []
    rows: list[dict[str, Any]] = raw.get("clusqmgrs", []) or []
    repos_text = str(raw.get("repos") or "")
    this_qm = str(raw.get("this_qm") or "")

    if not rows and not repos_text:
        # Nothing to analyze — caller likely targets a non-clustered QM.
        return findings

    findings.extend(_check_full_repos(rows, repos_text, registry, mq_version))
    findings.extend(_check_unhealthy_channels(rows, registry, mq_version))
    findings.extend(_check_stale_entries(rows, registry, mq_version))
    findings.extend(_check_suspended_members(rows))
    findings.extend(_check_self_only_membership(rows, this_qm))
    return findings


# --- individual checks -----------------------------------------------------


def _check_full_repos(
    rows: list[dict[str, Any]],
    repos_text: str,
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    """Each cluster must have at least one visible full repository (QMTYPE=REPOS)."""
    findings: list[RCSFinding] = []
    by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        cluster = str(r.get("CLUSTER", "")).strip()
        if cluster:
            by_cluster[cluster].append(r)

    self_full_clusters = _self_full_repo_clusters(repos_text)

    for cluster, members in by_cluster.items():
        full_repos = [m for m in members if str(m.get("QMTYPE", "")).upper() == "REPOS"]
        if cluster in self_full_clusters:
            # Local QM is itself a full repository for this cluster — fine.
            continue
        if not full_repos:
            findings.append(
                RCSFinding(
                    issue=f"Cluster {cluster} has no visible full repository",
                    severity=Severity.CRITICAL,
                    reason_code=None,
                    amq_code=None,
                    root_cause=(
                        f"No CLUSQMGR entry in cluster {cluster} reports "
                        "QMTYPE(REPOS), and this QM is not itself a full "
                        "repository. New cluster definitions cannot propagate "
                        "until at least one full repository is reachable."
                    ),
                    fix_steps=(
                        f"DISPLAY CLUSQMGR(*) WHERE(CLUSTER EQ {cluster})",
                        "DISPLAY QMGR REPOS REPOSNL",
                    ),
                    verify_commands=(f"DISPLAY CLUSQMGR(*) WHERE(CLUSTER EQ {cluster}) QMTYPE",),
                    doc_refs=tuple(registry.lookup_topic("cluster_partial_repository", mq_version)),
                    confidence="High",
                    evidence={
                        "cluster": cluster,
                        "members_visible": str(len(members)),
                        "full_repos_visible": "0",
                    },
                )
            )
    return findings


def _check_unhealthy_channels(
    rows: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    findings: list[RCSFinding] = []
    for r in rows:
        status = str(r.get("STATUS", "")).upper()
        if status in _BAD_CHANNEL_STATUS:
            channel = str(r.get("CHANNEL") or r.get("CLUSQMGR") or "<unknown>")
            cluster = str(r.get("CLUSTER", ""))
            conname = str(r.get("CONNAME", ""))
            findings.append(
                RCSFinding(
                    issue=f"Cluster channel {channel} status is {status}",
                    severity=Severity.HIGH,
                    reason_code=None,
                    amq_code="AMQ9764",
                    root_cause=(
                        f"Cluster channel {channel} (cluster {cluster}) reports "
                        f"{status}. Cluster sender/receiver channels must remain "
                        "RUNNING for repository updates and workload distribution."
                    ),
                    fix_steps=(
                        f"DISPLAY CHSTATUS('{channel}') ALL",
                        f"DISPLAY CHANNEL('{channel}') CONNAME XMITQ SSLCIPH",
                        "DISPLAY LSSTATUS(*) ALL",
                        f"PING CHANNEL({channel})",
                    ),
                    verify_commands=(f"DISPLAY CHSTATUS('{channel}') CURRENT",),
                    doc_refs=tuple(registry.lookup_amq("AMQ9764", mq_version)),
                    confidence="High",
                    evidence={
                        "channel": channel,
                        "cluster": cluster,
                        "conname": conname,
                        "status": status,
                    },
                )
            )
    return findings


def _check_stale_entries(
    rows: list[dict[str, Any]],
    registry: KCRegistry,
    mq_version: str | None,
) -> list[RCSFinding]:
    findings: list[RCSFinding] = []
    cutoff = datetime.now(UTC) - timedelta(days=_STALE_DAYS)
    for r in rows:
        clusdate = str(r.get("CLUSDATE", "")).strip()
        if not clusdate:
            continue
        try:
            # MQ format: YYYY-MM-DD
            parsed = datetime.strptime(clusdate, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError:
            continue
        if parsed >= cutoff:
            continue
        name = str(r.get("CLUSQMGR", "<unknown>"))
        cluster = str(r.get("CLUSTER", ""))
        age_days = (datetime.now(UTC) - parsed).days
        findings.append(
            RCSFinding(
                issue=f"Stale CLUSQMGR entry for {name} (last updated {age_days} days ago)",
                severity=Severity.MEDIUM,
                reason_code=None,
                amq_code="AMQ9456",
                root_cause=(
                    f"CLUSQMGR {name} in cluster {cluster} has not received an "
                    f"update from a full repository for {age_days} days "
                    f"(threshold: {_STALE_DAYS}). This usually indicates the "
                    "cluster sender channel to the full repository is broken or "
                    "the remote QM is offline."
                ),
                fix_steps=(
                    f"DISPLAY CLUSQMGR('{name}') ALL",
                    f"DISPLAY CHSTATUS('{r.get('CHANNEL', name)}') ALL",
                    "DISPLAY QMGR REPOS REPOSNL",
                ),
                verify_commands=(f"DISPLAY CLUSQMGR('{name}') CLUSDATE CLUSTIME",),
                doc_refs=tuple(registry.lookup_amq("AMQ9456", mq_version)),
                confidence="Medium",
                evidence={
                    "clusqmgr": name,
                    "cluster": cluster,
                    "last_update": clusdate,
                    "age_days": str(age_days),
                },
            )
        )
    return findings


def _check_suspended_members(rows: list[dict[str, Any]]) -> list[RCSFinding]:
    findings: list[RCSFinding] = []
    for r in rows:
        if str(r.get("SUSPEND", "")).upper() == "YES":
            name = str(r.get("CLUSQMGR", "<unknown>"))
            cluster = str(r.get("CLUSTER", ""))
            findings.append(
                RCSFinding(
                    issue=f"Cluster member {name} is SUSPEND(YES) in cluster {cluster}",
                    severity=Severity.MEDIUM,
                    reason_code=None,
                    amq_code=None,
                    root_cause=(
                        "A suspended cluster member does not receive workload "
                        "from the cluster. This may be intentional (maintenance) "
                        "or a forgotten state from a prior incident."
                    ),
                    fix_steps=(f"DISPLAY CLUSQMGR('{name}') SUSPEND",),
                    verify_commands=(f"DISPLAY CLUSQMGR('{name}') SUSPEND",),
                    doc_refs=(),
                    confidence="Medium",
                    evidence={"clusqmgr": name, "cluster": cluster},
                )
            )
    return findings


def _check_self_only_membership(rows: list[dict[str, Any]], this_qm: str) -> list[RCSFinding]:
    if not this_qm or not rows:
        return []
    other_members = [r for r in rows if str(r.get("CLUSQMGR", "")) != this_qm]
    if other_members:
        return []
    return [
        RCSFinding(
            issue=f"QM {this_qm} sees itself as the only cluster member",
            severity=Severity.HIGH,
            reason_code=None,
            amq_code=None,
            root_cause=(
                "DISPLAY CLUSQMGR returns only the local QM. Either no other "
                "members are reachable, or the cluster sender channel to the "
                "full repository has never started successfully."
            ),
            fix_steps=(
                "DISPLAY CHSTATUS(*) WHERE(CHLTYPE EQ CLUSSDR)",
                "DISPLAY QMGR REPOS REPOSNL",
                "DISPLAY CLUSQMGR(*) ALL",
            ),
            verify_commands=("DISPLAY CLUSQMGR(*) ALL",),
            doc_refs=(),
            confidence="Medium",
            evidence={"this_qm": this_qm, "members_visible": "1"},
        )
    ]


# --- helpers ---------------------------------------------------------------


def _self_full_repo_clusters(repos_text: str) -> set[str]:
    """Extract cluster names where the local QM is itself a full repository."""
    if not repos_text:
        return set()
    clusters: set[str] = set()
    text = repos_text.upper()
    # `REPOS(NAME)` and any names listed under `REPOSNL(NL)` resolve via name list.
    # We only look at REPOS() here; resolving REPOSNL would require a follow-up
    # DISPLAY NAMELIST. Keep it conservative.
    idx = text.find("REPOS(")
    while idx != -1:
        end = text.find(")", idx)
        if end == -1:
            break
        cluster_name = text[idx + 6 : end].strip()
        if cluster_name and cluster_name != " ":
            clusters.add(cluster_name)
        idx = text.find("REPOS(", end)
    return clusters
