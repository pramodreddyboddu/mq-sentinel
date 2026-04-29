"""End-to-end test: diagnose_native_ha_issues against the demo sandbox."""

from __future__ import annotations

from pathlib import Path

import pytest

from mq_sentinel.connectors.fixture import FixtureConnector
from mq_sentinel.inventory.models import QMEntry, Topology
from mq_sentinel.inventory.registry import InMemoryInventory
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.tools.native_ha import diagnose_native_ha_issues

pytestmark = pytest.mark.integration


class _Secrets:
    def resolve(self, secret_ref: str) -> MQCredential:
        return MQCredential(user="demo", password="demo")


def _fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "demo-sandbox" / "fixtures"


def test_native_ha_e2e() -> None:
    inventory = InMemoryInventory(
        [
            QMEntry(
                qm_name="DEMO_QM",
                host="localhost",
                port=1414,
                channel="APP.SVRCONN",
                environment="dev",
                topology_hint=Topology.NATIVE_HA,
                secret_ref="demo",
            )
        ]
    )
    result = diagnose_native_ha_issues(
        qm_name="DEMO_QM",
        connector_factory=lambda: FixtureConnector(_fixtures_dir()),
        inventory=inventory,
        secrets=_Secrets(),
    )
    assert result["tool"] == "diagnose_native_ha_issues"
    assert result["raw_evidence"]["instance_count"] == 3
    assert result["raw_evidence"]["active_count"] == 1
    assert result["raw_evidence"]["crr_enabled"] is True
    assert result["raw_evidence"]["crr_lag_seconds"] == 420

    issues = [f["issue"] for f in result["findings"]]
    # Seeded faults:
    assert any("DISCONNECTED" in i for i in issues), issues  # DEMO_QM-2 down
    assert any("log replay lag" in i for i in issues), issues  # DEMO_QM-2 at 60%
    assert any("Cross-region replication lag" in i for i in issues), issues  # CRR=420s

    # All fix steps read-only
    for f in result["findings"]:
        for step in f["fix_steps"]:
            for verb in (
                "ALTER ", "DELETE ", "DEFINE ", "REFRESH ", "RESET ",
                "CLEAR ", "SET ", "MOVE ", "START ", "STOP ", "RESUME ",
                "SUSPEND ", "FAILOVER ",
            ):
                assert verb not in step.upper(), f"destructive verb: {step}"

    # All KC URLs on IBM allowlist
    for f in result["findings"]:
        for ref in f["doc_refs"]:
            assert "www.ibm.com" in ref["url"]
