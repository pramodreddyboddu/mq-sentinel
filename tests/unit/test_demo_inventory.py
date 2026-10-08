"""The built-in DEMO_QM is only seeded for local dev with auth explicitly disabled."""

from __future__ import annotations

from pathlib import Path

import pytest

from mq_sentinel.auth.oidc import StubOIDCVerifier
from mq_sentinel.config import Settings
from mq_sentinel.server import MQSentinelServer, _demo_fixtures_dir


def _server(tmp_path: Path, *, env: str, auth_disabled: bool) -> MQSentinelServer:
    s = Settings()
    s.audit.log_path = tmp_path / "a.jsonl"
    s.server.environment = env  # type: ignore[assignment]
    s.server.inventory_dir = None
    s.auth.disable_auth_for_local_dev = auth_disabled
    return MQSentinelServer(s, verifier=StubOIDCVerifier())


def test_demo_qm_seeded_in_local_dev(tmp_path: Path) -> None:
    srv = _server(tmp_path, env="dev", auth_disabled=True)
    assert srv._inventory.get("DEMO_QM").environment == "dev"


@pytest.mark.parametrize(
    ("env", "auth_disabled"),
    [("dev", False), ("staging", True), ("prod", False)],
)
def test_demo_qm_not_seeded_outside_local_dev(
    tmp_path: Path, env: str, auth_disabled: bool
) -> None:
    srv = _server(tmp_path, env=env, auth_disabled=auth_disabled)
    with pytest.raises(LookupError):
        srv._inventory.get("DEMO_QM")


def test_demo_fixtures_dir_resolves_from_checkout() -> None:
    assert (_demo_fixtures_dir() / "mqsc" / "DISPLAY_CHSTATUS_ALL__ALL.json").is_file()


def test_connector_auto_goes_live_with_inventory() -> None:
    s = Settings()
    s.server.connector = "auto"
    s.server.inventory_dir = None
    assert s.server.resolved_connector() == "fixture"
    s.server.inventory_dir = "/etc/mq-sentinel"
    assert s.server.resolved_connector() == "pymqi"
    s.server.connector = "fixture"
    assert s.server.resolved_connector() == "fixture"


def test_prod_refuses_demo_fixtures() -> None:
    s = Settings()
    s.server.environment = "prod"
    s.server.inventory_dir = None
    s.server.connector = "auto"
    s.auth.disable_auth_for_local_dev = False
    with pytest.raises(RuntimeError, match="fixture connector is not permitted"):
        s.assert_production_safe()
    s.server.inventory_dir = "/etc/mq-sentinel"
    s.assert_production_safe()
