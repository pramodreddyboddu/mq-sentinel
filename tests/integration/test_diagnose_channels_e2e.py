"""End-to-end test of diagnose_failed_channels via the demo-sandbox fixtures.

Exercises: connector → topology detect → tool → matchers → RCS → sanitizer.
No live MQ required.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mq_sentinel.connectors.fixture import FixtureConnector
from mq_sentinel.inventory.models import QMEntry, Topology
from mq_sentinel.inventory.registry import InMemoryInventory
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.tools.channels import diagnose_failed_channels

pytestmark = pytest.mark.integration


class _Secrets:
    def resolve(self, secret_ref: str) -> MQCredential:
        return MQCredential(user="demo", password="demo")


def _fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "demo-sandbox" / "fixtures"


def test_demo_sandbox_e2e() -> None:
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

    result = diagnose_failed_channels(
        qm_name="DEMO_QM",
        connector_factory=lambda: FixtureConnector(_fixtures_dir()),
        inventory=inventory,
        secrets=_Secrets(),
    )

    assert result["tool"] == "diagnose_failed_channels"
    assert result["qm_name"] == "DEMO_QM"
    assert result["topology"]["mq_version"] == "9.4.0.0"

    findings = result["findings"]
    issues = {f["issue"] for f in findings}
    reason_codes = {f["reason_code"] for f in findings}

    # Must catch the 2035 (the headline demo)
    assert 2035 in reason_codes
    assert any("APP.SVRCONN" in i for i in issues)

    # Must catch the in-doubt channel as CRITICAL
    indoubt = [f for f in findings if "INDOUBT" in f["issue"]]
    assert indoubt and indoubt[0]["severity"] == "CRITICAL"

    # Must produce only IBM doc URLs (sanitizer enforced)
    for f in findings:
        for ref in f["doc_refs"]:
            assert "www.ibm.com" in ref["url"]

    # Must NOT include destructive verbs in fix_steps (read-only guarantee)
    for f in findings:
        for step in f["fix_steps"]:
            for verb in ("ALTER ", "DELETE ", "START ", "STOP ", "REFRESH "):
                assert verb not in step.upper(), f"destructive verb in fix step: {step}"
