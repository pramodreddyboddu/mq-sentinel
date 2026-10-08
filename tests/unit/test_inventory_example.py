"""The shipped example inventory must load against the real QMEntry schema."""

from __future__ import annotations

from pathlib import Path

from mq_sentinel.inventory.models import Topology
from mq_sentinel.server import MQSentinelServer

_EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "org"


def test_example_inventory_loads() -> None:
    inv = MQSentinelServer.load_inventory_from_dir(_EXAMPLES)
    names = sorted(e.qm_name for e in inv.list_all())
    assert names == ["NONPROD_QM_EU1", "PROD_QM_EU1", "PROD_QM_US1", "ZOS_QSG_MAIN"]
    assert inv.get("ZOS_QSG_MAIN").topology_hint is Topology.ZOS_QSG
    assert inv.get("PROD_QM_EU1").cipher_spec == "ANY_TLS13_OR_HIGHER"
