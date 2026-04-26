"""End-to-end test: check_cluster_health against the demo sandbox."""

from __future__ import annotations

from pathlib import Path

import pytest

from mq_sentinel.connectors.fixture import FixtureConnector
from mq_sentinel.inventory.models import QMEntry, Topology
from mq_sentinel.inventory.registry import InMemoryInventory
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.tools.cluster import check_cluster_health

pytestmark = pytest.mark.integration


class _Secrets:
    def resolve(self, secret_ref: str) -> MQCredential:
        return MQCredential(user="demo", password="demo")


def _fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "demo-sandbox" / "fixtures"


def test_cluster_health_e2e() -> None:
    inventory = InMemoryInventory(
        [
            QMEntry(
                qm_name="DEMO_QM",
                host="localhost",
                port=1414,
                channel="APP.SVRCONN",
                environment="dev",
                topology_hint=Topology.TRADITIONAL_CLUSTER,
                secret_ref="demo",
            )
        ]
    )
    result = check_cluster_health(
        qm_name="DEMO_QM",
        connector_factory=lambda: FixtureConnector(_fixtures_dir()),
        inventory=inventory,
        secrets=_Secrets(),
    )
    assert result["tool"] == "check_cluster_health"
    assert "PAYMENTS" in result["raw_evidence"]["clusters_seen"]

    issues = [f["issue"] for f in result["findings"]]

    # Seeded faults must be detected:
    assert any("RETRYING" in i for i in issues), issues  # PARTNER_QM
    assert any("STOPPED" in i for i in issues), issues  # ORPHAN_QM
    assert any("SUSPEND(YES)" in i for i in issues), issues  # MAINT_QM
    assert any("Stale CLUSQMGR" in i for i in issues), issues  # PARTNER_QM (old date)
    # No full repo visible for PAYMENTS or ORDERS (local QM is not REPOS)
    assert any("no visible full repository" in i for i in issues), issues

    # All fix steps are read-only
    for f in result["findings"]:
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
            ):
                assert verb not in step.upper(), f"destructive verb: {step}"

    # All KC URLs are on the IBM allowlist
    for f in result["findings"]:
        for ref in f["doc_refs"]:
            assert "www.ibm.com" in ref["url"]
