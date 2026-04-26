from __future__ import annotations

from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.rcs.matchers.dlq import match_dlq_findings


def _h(reason: int, dest: str = "Q1", backout: int = 0, app: str = "APP") -> dict:
    return {
        "reason_code": reason,
        "feedback": 0,
        "put_application_name": app,
        "put_application_type": "6",
        "put_date": "2026-04-26",
        "put_time": "10:00:00",
        "dest_q_name": dest,
        "dest_q_mgr_name": "QM",
        "backout_count": backout,
        "body_length": 100,
        "msg_id_hash": "x" * 64,
    }


def test_empty_dlq_no_findings() -> None:
    browse = {"queue_name": "DLQ", "queue_depth": 0, "sample_size": 0, "headers": []}
    assert match_dlq_findings(browse, KCRegistry()) == []


def test_depth_finding_critical_above_10k() -> None:
    browse = {"queue_name": "DLQ", "queue_depth": 50_000, "sample_size": 0, "headers": []}
    findings = match_dlq_findings(browse, KCRegistry())
    assert findings[0].severity.value == "CRITICAL"


def test_groups_by_reason_code_with_kc_links() -> None:
    browse = {
        "queue_name": "DLQ",
        "queue_depth": 5,
        "sample_size": 5,
        "headers": [
            _h(2035, "Q1"),
            _h(2035, "Q1"),
            _h(2030, "Q2"),
            _h(2053, "Q3"),
            _h(2051, "Q4"),
        ],
    }
    findings = match_dlq_findings(browse, KCRegistry(), mq_version="9.4.0")
    reasons = {f.reason_code for f in findings if f.reason_code is not None}
    assert {2035, 2030, 2053, 2051} <= reasons
    by_reason = {f.reason_code: f for f in findings if f.reason_code is not None}
    for r in (2035, 2030, 2053, 2051):
        assert by_reason[r].doc_refs, f"missing KC ref for {r}"
        assert all("www.ibm.com" in d.url for d in by_reason[r].doc_refs)


def test_backout_loop_flagged() -> None:
    browse = {
        "queue_name": "DLQ",
        "queue_depth": 3,
        "sample_size": 3,
        "headers": [_h(2035, "Q1", backout=8), _h(2035, "Q1", backout=6)],
    }
    findings = match_dlq_findings(browse, KCRegistry())
    assert any("backout_count >= 5" in f.issue for f in findings)


def test_fix_steps_are_read_only() -> None:
    browse = {
        "queue_name": "DLQ",
        "queue_depth": 2,
        "sample_size": 2,
        "headers": [_h(2035, "Q1"), _h(2030, "Q2")],
    }
    for f in match_dlq_findings(browse, KCRegistry()):
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
            ):
                assert verb not in step.upper(), f"destructive verb in: {step}"
