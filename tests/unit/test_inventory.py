from __future__ import annotations

import pytest
from pydantic import ValidationError

from mq_sentinel.inventory.models import QMEntry, Topology


def test_valid_entry() -> None:
    e = QMEntry(
        qm_name="QM1",
        host="mq.example.com",
        port=1414,
        channel="APP.SVRCONN",
        environment="prod",
        topology_hint=Topology.NATIVE_HA,
        secret_ref="prod/qm1",
    )
    assert e.qm_name == "QM1"


@pytest.mark.parametrize(
    "field,value",
    [
        ("qm_name", "q m"),
        ("qm_name", "A" * 49),
        ("port", 0),
        ("port", 70000),
        ("channel", "bad channel!"),
        ("environment", "unknown"),
        ("host", "bad host with spaces"),
    ],
)
def test_invalid_entry(field: str, value: object) -> None:
    base: dict[str, object] = {
        "qm_name": "QM1",
        "host": "mq.example.com",
        "port": 1414,
        "channel": "APP.SVRCONN",
        "environment": "prod",
        "secret_ref": "r",
    }
    base[field] = value
    with pytest.raises(ValidationError):
        QMEntry(**base)
