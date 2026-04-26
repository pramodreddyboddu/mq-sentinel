from __future__ import annotations

from datetime import UTC, datetime, timedelta

from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.rcs.matchers.cluster import match_cluster_findings


def _row(**kw: object) -> dict[str, object]:
    base: dict[str, object] = {
        "CLUSQMGR": "QM_X",
        "CLUSTER": "C1",
        "QMTYPE": "NORMAL",
        "STATUS": "RUNNING",
        "CHANNEL": "TO.QM_X",
        "CONNAME": "host(1414)",
        "DEFTYPE": "CLUSSDR",
        "SUSPEND": "NO",
        "CLUSDATE": datetime.now(UTC).strftime("%Y-%m-%d"),
        "CLUSTIME": "12:00:00",
    }
    base.update(kw)
    return base


def test_no_full_repo_visible_is_critical() -> None:
    raw = {
        "clusqmgrs": [_row(CLUSQMGR="A"), _row(CLUSQMGR="B")],
        "repos": "QMNAME(LOCAL) REPOS( ) REPOSNL( )",
        "this_qm": "LOCAL",
    }
    findings = match_cluster_findings(raw, KCRegistry())
    crits = [f for f in findings if f.severity.value == "CRITICAL"]
    assert crits and "no visible full repository" in crits[0].issue


def test_local_full_repo_suppresses_partial_repo_finding() -> None:
    raw = {
        "clusqmgrs": [_row(CLUSQMGR="A")],
        "repos": "QMNAME(LOCAL) REPOS(C1) REPOSNL( )",
        "this_qm": "LOCAL",
    }
    findings = match_cluster_findings(raw, KCRegistry())
    assert not any("no visible full repository" in f.issue for f in findings)


def test_unhealthy_channel_flagged_with_kc() -> None:
    raw = {
        "clusqmgrs": [_row(CLUSQMGR="X", STATUS="RETRYING")],
        "repos": "QMNAME(LOCAL) REPOS(C1)",
        "this_qm": "LOCAL",
    }
    findings = match_cluster_findings(raw, KCRegistry(), mq_version="9.4.0")
    bad = [f for f in findings if "RETRYING" in f.issue]
    assert bad
    assert bad[0].severity.value == "HIGH"
    assert any("www.ibm.com" in d.url for d in bad[0].doc_refs)


def test_stale_entry_flagged_with_age() -> None:
    old = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")
    raw = {
        "clusqmgrs": [_row(CLUSQMGR="STALE", CLUSDATE=old)],
        "repos": "REPOS(C1)",
        "this_qm": "LOCAL",
    }
    findings = match_cluster_findings(raw, KCRegistry(), mq_version="9.4.0")
    stale = [f for f in findings if "Stale" in f.issue]
    assert stale
    assert stale[0].amq_code == "AMQ9456"


def test_suspended_member_flagged() -> None:
    raw = {
        "clusqmgrs": [_row(CLUSQMGR="S", SUSPEND="YES")],
        "repos": "REPOS(C1)",
        "this_qm": "LOCAL",
    }
    findings = match_cluster_findings(raw, KCRegistry())
    assert any("SUSPEND(YES)" in f.issue for f in findings)


def test_self_only_membership_flagged() -> None:
    raw = {
        "clusqmgrs": [_row(CLUSQMGR="LOCAL")],
        "repos": "REPOS(C1)",
        "this_qm": "LOCAL",
    }
    findings = match_cluster_findings(raw, KCRegistry())
    assert any("only cluster member" in f.issue for f in findings)


def test_fix_steps_are_read_only() -> None:
    old = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")
    raw = {
        "clusqmgrs": [
            _row(CLUSQMGR="A", STATUS="RETRYING"),
            _row(CLUSQMGR="B", SUSPEND="YES"),
            _row(CLUSQMGR="C", CLUSDATE=old),
        ],
        "repos": "REPOS(C1)",
        "this_qm": "LOCAL",
    }
    for f in match_cluster_findings(raw, KCRegistry()):
        for step in f.fix_steps:
            for verb in (
                "ALTER ",
                "DELETE ",
                "DEFINE ",
                "REFRESH ",
                "RESET ",
                "CLEAR ",
                "SET ",
                "MOVE ",
                "START ",
                "STOP ",
                "RESUME ",
                "SUSPEND ",
                "RECOVER ",
            ):
                assert verb not in step.upper(), f"destructive verb in: {step}"


def test_empty_input_returns_empty() -> None:
    assert match_cluster_findings({"clusqmgrs": [], "repos": "", "this_qm": ""}, KCRegistry()) == []
