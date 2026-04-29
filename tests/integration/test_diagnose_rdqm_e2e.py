"""End-to-end RDQM diagnostic test against the demo sandbox."""

from __future__ import annotations

from pathlib import Path

import pytest

from mq_sentinel.connectors.fixture import FixtureConnector
from mq_sentinel.inventory.models import QMEntry, Topology
from mq_sentinel.inventory.registry import InMemoryInventory
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.tools.rdqm import diagnose_rdqm_issues

pytestmark = pytest.mark.integration


class _Secrets:
    def resolve(self, secret_ref: str) -> MQCredential:
        return MQCredential(user="demo", password="demo")


def _fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "demo-sandbox" / "fixtures"


def test_rdqm_e2e() -> None:
    inventory = InMemoryInventory(
        [
            QMEntry(
                qm_name="DEMO_QM",
                host="localhost",
                port=1414,
                channel="APP.SVRCONN",
                environment="dev",
                topology_hint=Topology.RDQM,
                secret_ref="demo",
            )
        ]
    )
    result = diagnose_rdqm_issues(
        qm_name="DEMO_QM",
        connector_factory=lambda: FixtureConnector(_fixtures_dir()),
        inventory=inventory,
        secrets=_Secrets(),
    )
    assert result["tool"] == "diagnose_rdqm_issues"
    assert result["raw_evidence"]["pacemaker_total"] == 3
    assert result["raw_evidence"]["pacemaker_offline"] == 1
    # 2 peers under DEMO_QM + 1 under DEMO_QM_LOGS = 3 (resource, peer) pairs
    assert result["raw_evidence"]["drbd_resources"] == 3

    issues = [f["issue"] for f in result["findings"]]
    # Seeded faults:
    assert any("offline node" in i for i in issues), issues  # rdqm-3
    assert any("DEMO_QM-monitor" in i for i in issues), issues  # failed pacemaker resource
    assert any("WFConnection" in i for i in issues), issues  # DRBD peer disconnected
    assert any("SyncTarget" in i for i in issues), issues  # DEMO_QM_LOGS
    assert any("Inconsistent" in i for i in issues), issues  # DEMO_QM_LOGS local disk

    # Read-only invariants
    for f in result["findings"]:
        for step in f["fix_steps"]:
            for verb in (
                "pcs ",
                "crm ",
                "drbdadm primary",
                "drbdadm secondary",
                "drbdadm connect",
                "drbdadm disconnect",
                "drbdadm invalidate",
                "ALTER ",
                "DELETE ",
                "DEFINE ",
                "REFRESH ",
                "RESET ",
                "CLEAR ",
                "SET ",
                "START ",
                "STOP ",
                "RESUME ",
                "SUSPEND ",
                "FAILOVER ",
            ):
                assert verb.lower() not in step.lower(), f"destructive verb: {step}"

    # KC URL allowlist
    for f in result["findings"]:
        for ref in f["doc_refs"]:
            assert "www.ibm.com" in ref["url"]
