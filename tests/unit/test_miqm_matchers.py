from __future__ import annotations

from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.rcs.matchers.miqm import match_miqm_findings


def test_empty_no_findings() -> None:
    assert match_miqm_findings({}, KCRegistry()) == []


def test_no_active_critical() -> None:
    raw = {
        "instances": [
            {"qm_name": "Q", "host": "h1", "instance_type": "STANDBY"},
            {"qm_name": "Q", "host": "h2", "instance_type": "NONE"},
        ],
        "standby_permitted": True,
    }
    findings = match_miqm_findings(raw, KCRegistry())
    assert any("no ACTIVE instance" in f.issue and f.severity.value == "CRITICAL" for f in findings)


def test_dual_active_critical() -> None:
    raw = {
        "instances": [
            {"qm_name": "Q", "host": "h1", "instance_type": "ACTIVE"},
            {"qm_name": "Q", "host": "h2", "instance_type": "ACTIVE"},
        ],
        "standby_permitted": True,
    }
    findings = match_miqm_findings(raw, KCRegistry())
    crits = [f for f in findings if "ACTIVE instances" in f.issue]
    assert crits and crits[0].severity.value == "CRITICAL"


def test_standby_not_permitted_high() -> None:
    raw = {
        "instances": [{"qm_name": "Q", "host": "h1", "instance_type": "ACTIVE"}],
        "standby_permitted": False,
    }
    findings = match_miqm_findings(raw, KCRegistry())
    assert any("standby instances are not permitted" in f.issue for f in findings)


def test_shared_fs_failure_high() -> None:
    raw = {
        "instances": [{"qm_name": "Q", "host": "h1", "instance_type": "ACTIVE"}],
        "standby_permitted": True,
        "shared_fs_ok": False,
        "shared_fs_path": "/var/mqm/shared",
    }
    findings = match_miqm_findings(raw, KCRegistry())
    assert any("shared filesystem" in f.issue for f in findings)


def test_failover_events_medium() -> None:
    raw = {
        "instances": [{"qm_name": "Q", "host": "h1", "instance_type": "ACTIVE"}],
        "standby_permitted": True,
        "error_log_tail": "...AMQ7228...AMQ7232...",
    }
    findings = match_miqm_findings(raw, KCRegistry())
    assert any("failover-related event" in f.issue for f in findings)


def test_fix_steps_read_only() -> None:
    raw = {
        "instances": [
            {"qm_name": "Q", "host": "h1", "instance_type": "ACTIVE"},
            {"qm_name": "Q", "host": "h2", "instance_type": "ACTIVE"},
        ],
        "standby_permitted": False,
        "shared_fs_ok": False,
        "error_log_tail": "AMQ7230",
    }
    for f in match_miqm_findings(raw, KCRegistry()):
        for step in f.fix_steps:
            for verb in (
                "endmqm",
                "strmqm",
                "dltmqm",
                "crtmqm",
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
                "FAILOVER ",
            ):
                assert verb.lower() not in step.lower(), f"destructive verb in: {step}"
