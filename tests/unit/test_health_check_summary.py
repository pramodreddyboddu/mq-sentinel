"""Unit tests for the composite tool's summary + sorting logic."""

from __future__ import annotations

from mq_sentinel.rcs.engine import RCSFinding, Severity
from mq_sentinel.tools.health_check import _build_summary, _finding_sort_key


def _f(severity: Severity, issue: str = "x") -> RCSFinding:
    return RCSFinding(
        issue=issue,
        severity=severity,
        reason_code=None,
        amq_code=None,
        root_cause="",
        fix_steps=(),
        verify_commands=(),
        doc_refs=(),
        confidence="High",
    )


def test_sort_key_orders_critical_first() -> None:
    items = [
        ("dlq", _f(Severity.LOW)),
        ("cluster", _f(Severity.CRITICAL)),
        ("channels", _f(Severity.HIGH)),
        ("dlq", _f(Severity.MEDIUM)),
    ]
    sorted_items = sorted(items, key=_finding_sort_key)
    assert [f.severity.value for _, f in sorted_items] == [
        "CRITICAL",
        "HIGH",
        "MEDIUM",
        "LOW",
    ]


def test_sort_key_breaks_ties_by_category_order() -> None:
    items = [
        ("cluster", _f(Severity.HIGH, "c")),
        ("channels", _f(Severity.HIGH, "a")),
        ("dlq", _f(Severity.HIGH, "b")),
    ]
    sorted_items = sorted(items, key=_finding_sort_key)
    assert [cat for cat, _ in sorted_items] == ["channels", "dlq", "cluster"]


def test_summary_overall_status_critical_when_any_critical() -> None:
    findings = [
        ("channels", _f(Severity.HIGH)),
        ("cluster", _f(Severity.CRITICAL)),
        ("dlq", _f(Severity.LOW)),
    ]
    summary = _build_summary(findings)
    assert summary["overall_status"] == "CRITICAL"
    assert summary["total_findings"] == 3
    assert summary["by_severity"]["CRITICAL"] == 1
    assert summary["by_severity"]["HIGH"] == 1
    assert summary["by_category"]["channels"] == 1


def test_summary_overall_status_ok_when_no_findings() -> None:
    summary = _build_summary([])
    assert summary["overall_status"] == "OK"
    assert summary["total_findings"] == 0
    assert summary["top_issues"] == []


def test_summary_top_issues_capped_at_five() -> None:
    findings = [("channels", _f(Severity.HIGH, f"issue_{i}")) for i in range(10)]
    summary = _build_summary(findings)
    assert len(summary["top_issues"]) == 5
