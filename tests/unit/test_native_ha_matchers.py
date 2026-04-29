from __future__ import annotations

from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.rcs.matchers.native_ha import match_native_ha_findings


def _i(
    name: str,
    role: str = "REPLICA",
    status: str = "RUNNING",
    insync: str = "YES",
    backlog: int = 0,
    replay: int = 100,
) -> dict[str, object]:
    return {
        "INSTANCE": name,
        "ROLE": role,
        "STATUS": status,
        "INSYNC": insync,
        "BACKLOG": str(backlog),
        "REPLAYPCT": str(replay),
    }


def test_empty_input_no_findings() -> None:
    assert match_native_ha_findings({}, KCRegistry()) == []


def test_quorum_lost_critical() -> None:
    raw = {
        "instances": [
            _i("a", role="ACTIVE", insync="YES"),
            _i("b", insync="NO", status="DISCONNECTED"),
            _i("c", insync="NO", status="DISCONNECTED"),
        ],
        "quorum_required": 2,
    }
    findings = match_native_ha_findings(raw, KCRegistry(), mq_version="9.4.0")
    crits = [f for f in findings if "quorum at risk" in f.issue]
    assert crits and crits[0].severity.value == "CRITICAL"


def test_no_active_instance_critical() -> None:
    raw = {"instances": [_i("a", role="REPLICA"), _i("b", role="REPLICA")]}
    findings = match_native_ha_findings(raw, KCRegistry())
    assert any("no ACTIVE instance" in f.issue and f.severity.value == "CRITICAL" for f in findings)


def test_split_brain_critical() -> None:
    raw = {
        "instances": [
            _i("a", role="ACTIVE"),
            _i("b", role="ACTIVE"),
            _i("c", role="REPLICA"),
        ]
    }
    findings = match_native_ha_findings(raw, KCRegistry())
    assert any("split-brain" in f.issue for f in findings)


def test_disconnected_replica_high_with_amq3209() -> None:
    raw = {
        "instances": [
            _i("a", role="ACTIVE"),
            _i("b", status="DISCONNECTED", insync="NO"),
            _i("c"),
        ]
    }
    findings = match_native_ha_findings(raw, KCRegistry(), mq_version="9.4.0")
    bad = [f for f in findings if "DISCONNECTED" in f.issue]
    assert bad
    assert bad[0].amq_code == "AMQ3209"
    assert any("www.ibm.com" in d.url for d in bad[0].doc_refs)


def test_log_replay_lag_severity() -> None:
    raw = {
        "instances": [
            _i("a", role="ACTIVE"),
            _i("b", replay=92),  # MEDIUM
            _i("c", replay=70),  # HIGH
        ]
    }
    findings = match_native_ha_findings(raw, KCRegistry())
    by_inst = {f.evidence.get("instance"): f for f in findings if "log replay lag" in f.issue}
    assert by_inst["b"].severity.value == "MEDIUM"
    assert by_inst["c"].severity.value == "HIGH"


def test_crr_lag_critical_above_300() -> None:
    raw = {
        "instances": [_i("a", role="ACTIVE"), _i("b"), _i("c")],
        "crr": {"enabled": True, "lag_seconds": 420, "recovery_group": "EAST", "role": "LIVE"},
    }
    findings = match_native_ha_findings(raw, KCRegistry(), mq_version="9.4.0")
    crrs = [f for f in findings if "Cross-region replication lag" in f.issue]
    assert crrs and crrs[0].severity.value == "CRITICAL"
    assert any("www.ibm.com" in d.url for d in crrs[0].doc_refs)


def test_crr_lag_under_threshold_no_finding() -> None:
    raw = {
        "instances": [_i("a", role="ACTIVE"), _i("b"), _i("c")],
        "crr": {"enabled": True, "lag_seconds": 5, "recovery_group": "EAST"},
    }
    findings = match_native_ha_findings(raw, KCRegistry())
    assert not any("Cross-region" in f.issue for f in findings)


def test_fix_steps_are_read_only() -> None:
    raw = {
        "instances": [
            _i("a", role="ACTIVE"),
            _i("b", status="DISCONNECTED", insync="NO"),
            _i("c", replay=70),
        ],
        "crr": {"enabled": True, "lag_seconds": 400, "recovery_group": "EAST"},
    }
    for f in match_native_ha_findings(raw, KCRegistry()):
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
                "FAILOVER ",
            ):
                assert verb not in step.upper(), f"destructive verb in: {step}"
