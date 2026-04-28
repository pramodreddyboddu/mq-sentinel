"""End-to-end test: full_mq_health_check against the demo sandbox.

This is the headline composite tool — it must stitch all category checks
together, sort by severity, build an executive summary, and never leak
destructive recommendations or non-IBM URLs.
"""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import pytest

from mq_sentinel.connectors.fixture import FixtureConnector
from mq_sentinel.inventory.models import QMEntry, Topology
from mq_sentinel.inventory.registry import InMemoryInventory
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.tools.health_check import full_mq_health_check

pytestmark = pytest.mark.integration


class _Secrets:
    def resolve(self, secret_ref: str) -> MQCredential:
        return MQCredential(user="demo", password="demo")


def _fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "demo-sandbox" / "fixtures"


def test_full_health_check_e2e() -> None:
    inventory = InMemoryInventory(
        [
            QMEntry(
                qm_name="DEMO_QM",
                host="localhost",
                port=1414,
                channel="APP.SVRCONN",
                environment="dev",
                topology_hint=Topology.STANDALONE,
                secret_ref="demo",
            )
        ]
    )

    result = full_mq_health_check(
        qm_name="DEMO_QM",
        connector_factory=lambda: FixtureConnector(_fixtures_dir()),
        inventory=inventory,
        secrets=_Secrets(),
    )

    assert result["tool"] == "full_mq_health_check"
    assert result["qm_name"] == "DEMO_QM"
    assert result["topology"]["mq_version"] == "9.4.0.0"

    # All three categories ran successfully
    assert set(result["checks_run"]) == {"channels", "dlq", "cluster"}
    assert result["checks_skipped"] == []

    # Findings present and sorted by severity (CRITICAL first)
    findings = result["findings"]
    assert findings
    severities = [f["severity"] for f in findings]
    rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    for a, b in pairwise(severities):
        assert rank[a] <= rank[b], f"findings not sorted: {severities}"

    # Each finding has its category tagged
    for f in findings:
        assert f["category"] in {"channels", "dlq", "cluster"}

    # Executive summary
    summary = result["summary"]
    assert summary["total_findings"] == len(findings)
    assert summary["overall_status"] in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "OK"}
    assert summary["overall_status"] == "CRITICAL"  # demo sandbox seeds CRITICAL findings
    assert sum(summary["by_severity"].values()) == len(findings)
    assert sum(summary["by_category"].values()) == len(findings)
    assert summary["top_issues"]
    assert len(summary["top_issues"]) <= 5

    # Cross-category coverage: must have findings from each category present
    cats_with_findings = {f["category"] for f in findings}
    assert {"channels", "dlq", "cluster"}.issubset(cats_with_findings)

    # Read-only invariant across the whole composite output
    for f in findings:
        for step in f["fix_steps"]:
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
                assert verb not in step.upper(), f"destructive verb: {step}"

    # Sanitizer / KC allowlist enforced across all findings
    for f in findings:
        for ref in f["doc_refs"]:
            assert "www.ibm.com" in ref["url"]

    # Per-category raw evidence is present
    assert "channels" in result["raw_evidence"]
    assert "dlq" in result["raw_evidence"]
    assert "cluster" in result["raw_evidence"]
    assert result["raw_evidence"]["dlq"]["bodies_read"] is False
