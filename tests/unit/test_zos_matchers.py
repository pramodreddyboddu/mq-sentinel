from __future__ import annotations

from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.rcs.matchers.zos import match_zos_findings


def test_empty_no_findings() -> None:
    assert match_zos_findings({}, KCRegistry()) == []


def test_inactive_qsg_member_high() -> None:
    raw = {
        "group": {
            "qsg_name": "QSG1",
            "members": [
                {"name": "MQA1", "status": "ACTIVE"},
                {"name": "MQA2", "status": "INACTIVE"},
            ],
        }
    }
    findings = match_zos_findings(raw, KCRegistry(), mq_version="9.4.0")
    assert any("MQA2" in f.issue and f.severity.value == "HIGH" for f in findings)


def test_chin_stopped_critical() -> None:
    raw = {"chin": {"status": "STOPPED"}}
    findings = match_zos_findings(raw, KCRegistry(), mq_version="9.4.0")
    assert any("Channel initiator" in f.issue and f.severity.value == "CRITICAL" for f in findings)


def test_pageset_high_and_critical() -> None:
    raw = {
        "pagesets": [
            {"PSID": "0", "USEPCT": "55"},
            {"PSID": "1", "USEPCT": "82"},
            {"PSID": "2", "USEPCT": "97"},
        ]
    }
    findings = match_zos_findings(raw, KCRegistry())
    by_psid = {f.evidence.get("psid"): f for f in findings if "Page set" in f.issue}
    assert "0" not in by_psid
    assert by_psid["1"].severity.value == "HIGH"
    assert by_psid["2"].severity.value == "CRITICAL"


def test_bufferpool_low_free_high() -> None:
    raw = {
        "bufferpools": [
            {"BUFFPOOL": "0", "FREEPCT": "45"},
            {"BUFFPOOL": "1", "FREEPCT": "5"},
        ]
    }
    findings = match_zos_findings(raw, KCRegistry())
    assert any("Buffer pool 1" in f.issue and f.severity.value == "HIGH" for f in findings)


def test_cf_failed_critical() -> None:
    raw = {
        "cf_structures": [
            {"STRUCTURE": "APPLICATION1", "STATUS": "ACTIVE"},
            {"STRUCTURE": "APPLICATION2", "STATUS": "FAILED"},
        ]
    }
    findings = match_zos_findings(raw, KCRegistry())
    bad = [f for f in findings if "APPLICATION2" in f.issue]
    assert bad and bad[0].severity.value == "CRITICAL"


def test_fix_steps_read_only() -> None:
    raw = {
        "group": {"qsg_name": "Q", "members": [{"name": "M", "status": "INACTIVE"}]},
        "chin": {"status": "STOPPED"},
        "pagesets": [{"PSID": "0", "USEPCT": "97"}],
        "bufferpools": [{"BUFFPOOL": "0", "FREEPCT": "5"}],
        "cf_structures": [{"STRUCTURE": "S", "STATUS": "FAILED"}],
    }
    for f in match_zos_findings(raw, KCRegistry()):
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
                "FORMAT ",
                "RECOVER ",
                "BACKUP ",
            ):
                assert verb not in step.upper(), f"destructive verb in: {step}"
