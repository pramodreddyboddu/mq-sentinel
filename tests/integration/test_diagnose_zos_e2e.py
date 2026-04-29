"""End-to-end z/OS QSG diagnostic test against the demo sandbox."""

from __future__ import annotations

from pathlib import Path

import pytest

from mq_sentinel.connectors.fixture import FixtureConnector
from mq_sentinel.inventory.models import QMEntry, Topology
from mq_sentinel.inventory.registry import InMemoryInventory
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.tools.zos import diagnose_zos_qsg_issues

pytestmark = pytest.mark.integration


class _Secrets:
    def resolve(self, secret_ref: str) -> MQCredential:
        return MQCredential(user="demo", password="demo")


def _fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "demo-sandbox" / "fixtures"


def test_zos_e2e() -> None:
    inventory = InMemoryInventory(
        [
            QMEntry(
                qm_name="DEMO_QM",
                host="localhost",
                port=1414,
                channel="APP.SVRCONN",
                environment="dev",
                topology_hint=Topology.ZOS_QSG,
                secret_ref="demo",
            )
        ]
    )
    result = diagnose_zos_qsg_issues(
        qm_name="DEMO_QM",
        connector_factory=lambda: FixtureConnector(_fixtures_dir()),
        inventory=inventory,
        secrets=_Secrets(),
    )
    assert result["tool"] == "diagnose_zos_qsg_issues"
    issues = [f["issue"] for f in result["findings"]]

    assert any("MQA3" in i for i in issues), issues       # inactive QSG member
    assert any("Channel initiator" in i for i in issues), issues  # CHIN STOPPED
    assert any("Page set 2" in i for i in issues), issues # PSID 2 at 97%
    assert any("Buffer pool 1" in i for i in issues), issues
    assert any("APPLICATION2" in i for i in issues), issues  # CF FAILED

    for f in result["findings"]:
        for step in f["fix_steps"]:
            for verb in ("ALTER ", "DELETE ", "DEFINE ", "START ", "STOP ", "FORMAT ", "RECOVER "):
                assert verb not in step.upper(), f"destructive verb: {step}"
        for ref in f["doc_refs"]:
            assert "www.ibm.com" in ref["url"]
