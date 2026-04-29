"""End-to-end MIQM diagnostic test against the demo sandbox."""

from __future__ import annotations

from pathlib import Path

import pytest

from mq_sentinel.connectors.fixture import FixtureConnector
from mq_sentinel.inventory.models import QMEntry, Topology
from mq_sentinel.inventory.registry import InMemoryInventory
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.tools.miqm import diagnose_multi_instance_issues

pytestmark = pytest.mark.integration


class _Secrets:
    def resolve(self, secret_ref: str) -> MQCredential:
        return MQCredential(user="demo", password="demo")


def _fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "demo-sandbox" / "fixtures"


def test_miqm_e2e() -> None:
    inventory = InMemoryInventory(
        [
            QMEntry(
                qm_name="DEMO_QM",
                host="localhost",
                port=1414,
                channel="APP.SVRCONN",
                environment="dev",
                topology_hint=Topology.MULTI_INSTANCE,
                secret_ref="demo",
            )
        ]
    )
    result = diagnose_multi_instance_issues(
        qm_name="DEMO_QM",
        connector_factory=lambda: FixtureConnector(_fixtures_dir()),
        inventory=inventory,
        secrets=_Secrets(),
    )
    assert result["tool"] == "diagnose_multi_instance_issues"
    assert result["raw_evidence"]["instance_count"] == 2

    issues = [f["issue"] for f in result["findings"]]
    # Both fixture instances are MODE(Active) → split-brain finding
    assert any("ACTIVE instances" in i for i in issues), issues

    for f in result["findings"]:
        for step in f["fix_steps"]:
            for verb in ("endmqm", "strmqm", "dltmqm", "ALTER ", "DELETE ", "START ", "STOP "):
                assert verb.lower() not in step.lower(), f"destructive verb: {step}"
        for ref in f["doc_refs"]:
            assert "www.ibm.com" in ref["url"]
