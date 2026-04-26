"""Server dispatcher tests for the channels tool wiring + RBAC."""

from __future__ import annotations

from pathlib import Path

import pytest

from mq_sentinel.auth.rbac import AuthorizationError
from mq_sentinel.config import Settings
from mq_sentinel.connectors.fixture import FixtureConnector
from mq_sentinel.inventory.models import QMEntry, Topology
from mq_sentinel.inventory.registry import InMemoryInventory
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.server import MQSentinelServer


class _Secrets:
    def resolve(self, secret_ref: str) -> MQCredential:
        return MQCredential(user="x", password="x")


def _fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "demo-sandbox" / "fixtures"


def _settings(tmp_path: Path) -> Settings:
    s = Settings()
    s.audit.log_path = tmp_path / "a.jsonl"
    return s


def _server(tmp_path: Path, env: str) -> MQSentinelServer:
    inventory = InMemoryInventory(
        [
            QMEntry(
                qm_name="DEMO_QM",
                host="h",
                port=1414,
                channel="APP.SVRCONN",
                environment=env,
                topology_hint=Topology.STANDALONE,
                secret_ref="x",
            )
        ]
    )
    return MQSentinelServer(
        _settings(tmp_path),
        inventory=inventory,
        secrets=_Secrets(),
        connector_factory=lambda: FixtureConnector(_fixtures_dir()),
    )


def test_dispatch_diagnose_channels_dev_ok(tmp_path: Path) -> None:
    srv = _server(tmp_path, env="dev")
    out = srv.dispatch(
        token="dev",
        tool="diagnose_failed_channels",
        params={"qm_name": "DEMO_QM"},
    )
    assert out["tool"] == "diagnose_failed_channels"
    assert out["findings"]


def test_dispatch_prod_qm_denied_to_nonprod_role(tmp_path: Path) -> None:
    srv = _server(tmp_path, env="prod")
    with pytest.raises(AuthorizationError):
        srv.dispatch(
            token="dev",
            tool="diagnose_failed_channels",
            params={"qm_name": "DEMO_QM"},
        )


def test_dispatch_missing_qm_name_rejected(tmp_path: Path) -> None:
    srv = _server(tmp_path, env="dev")
    with pytest.raises(ValueError):
        srv.dispatch(token="dev", tool="diagnose_failed_channels", params={})
