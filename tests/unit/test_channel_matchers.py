from __future__ import annotations

from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.rcs.matchers.channels import match_channel_failures


def test_2035_finding_has_chlauth_fix_and_kc_link() -> None:
    raw = {
        "channels": [
            {"CHANNEL": "APP.SVRCONN", "STATUS": "RETRYING", "REASON": 2035},
        ],
        "error_log_tail": "",
    }
    findings = match_channel_failures(raw, KCRegistry(), mq_version="9.4.0")
    assert findings, "expected a 2035 finding"
    f = findings[0]
    assert f.reason_code == 2035
    assert f.severity.value == "HIGH"
    assert any("CHLAUTH" in step for step in f.fix_steps)
    assert f.doc_refs and "www.ibm.com" in f.doc_refs[0].url


def test_indoubt_critical_no_remediation_command() -> None:
    raw = {
        "channels": [{"CHANNEL": "RCVR.A", "STATUS": "INDOUBT", "REASON": 0}],
        "error_log_tail": "",
    }
    findings = match_channel_failures(raw, KCRegistry())
    assert findings[0].severity.value == "CRITICAL"
    # Read-only: never suggest RESOLVE / RESET / DELETE / ALTER
    for step in findings[0].fix_steps:
        for verb in ("RESOLVE", "RESET", "DELETE", "ALTER", "DEFINE", "REFRESH"):
            assert verb not in step.upper()


def test_amq9202_extracted_from_log_tail() -> None:
    raw = {
        "channels": [],
        "error_log_tail": "...AMQ9202E: Remote host not available...",
    }
    findings = match_channel_failures(raw, KCRegistry(), mq_version="9.4.0")
    assert any(f.amq_code == "AMQ9202" for f in findings)


def test_healthy_channel_produces_no_finding() -> None:
    raw = {
        "channels": [{"CHANNEL": "OK", "STATUS": "RUNNING", "REASON": 0}],
        "error_log_tail": "",
    }
    assert match_channel_failures(raw, KCRegistry()) == []
