"""End-to-end DLQ analyzer test against the demo sandbox."""

from __future__ import annotations

from pathlib import Path

import pytest

from mq_sentinel.connectors.fixture import FixtureConnector
from mq_sentinel.inventory.models import QMEntry, Topology
from mq_sentinel.inventory.registry import InMemoryInventory
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.tools.dlq import analyze_dlq

pytestmark = pytest.mark.integration


class _Secrets:
    def resolve(self, secret_ref: str) -> MQCredential:
        return MQCredential(user="demo", password="demo")


def _fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "demo-sandbox" / "fixtures"


def test_dlq_e2e() -> None:
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

    result = analyze_dlq(
        qm_name="DEMO_QM",
        connector_factory=lambda: FixtureConnector(_fixtures_dir()),
        inventory=inventory,
        secrets=_Secrets(),
        sample_size=50,
    )

    assert result["tool"] == "analyze_dlq_and_suggest_reprocessing"
    assert result["raw_evidence"]["dlq_name"] == "SYSTEM.DEAD.LETTER.QUEUE"
    assert result["raw_evidence"]["bodies_read"] is False  # critical guarantee

    findings = result["findings"]
    reasons = {f["reason_code"] for f in findings if f["reason_code"]}
    # Seeded fixture has 2035, 2030, 2053, 2051
    assert {2035, 2030, 2053, 2051} <= reasons

    # Depth finding present and HIGH/CRITICAL (1247 > 1000)
    depth_findings = [f for f in findings if "depth=" in f["issue"]]
    assert depth_findings
    assert depth_findings[0]["severity"] in {"HIGH", "CRITICAL"}

    # Backout-loop detected (POISON.PROCESSOR has backout=7 and 6)
    assert any("backout_count" in f["issue"] for f in findings)

    # Every doc_ref URL must be on the IBM allowlist
    for f in findings:
        for ref in f["doc_refs"]:
            assert "www.ibm.com" in ref["url"]

    # No destructive verbs leaked into fix_steps anywhere
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
                "START ",
                "STOP ",
                "MOVE ",
            ):
                assert verb not in step.upper(), f"destructive verb: {step}"
