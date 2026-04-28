"""HTTP transport — bearer auth, error mapping, public + protected endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from mq_sentinel.auth.oidc import Principal, TokenVerificationError
from mq_sentinel.config import Settings
from mq_sentinel.connectors.fixture import FixtureConnector
from mq_sentinel.http_app import build_http_app
from mq_sentinel.inventory.models import QMEntry, Topology
from mq_sentinel.inventory.registry import InMemoryInventory
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.server import MQSentinelServer

pytestmark = pytest.mark.integration


class _FakeVerifier:
    """Per-test verifier: accepts a small set of known tokens, rejects others."""

    def __init__(self, mapping: dict[str, Principal]) -> None:
        self._mapping = mapping

    def verify(self, token: str) -> Principal:
        if token not in self._mapping:
            raise TokenVerificationError("bad token")
        return self._mapping[token]


class _Secrets:
    def resolve(self, secret_ref: str) -> MQCredential:
        return MQCredential(user="x", password="x")


def _fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "demo-sandbox" / "fixtures"


def _build(tmp_path: Path, mapping: dict[str, Principal], env: str = "dev") -> TestClient:
    settings = Settings()
    settings.audit.log_path = tmp_path / "a.jsonl"
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
    server = MQSentinelServer(
        settings,
        inventory=inventory,
        secrets=_Secrets(),
        connector_factory=lambda: FixtureConnector(_fixtures_dir()),
        verifier=_FakeVerifier(mapping),
    )
    return TestClient(build_http_app(server))


def _principal(roles: set[str], sub: str = "u1", tenant: str = "acme") -> Principal:
    return Principal(subject=sub, tenant=tenant, roles=frozenset(roles))


# --- public endpoints -------------------------------------------------------


def test_healthz_no_auth(tmp_path: Path) -> None:
    client = _build(tmp_path, {})
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_readyz_no_auth(tmp_path: Path) -> None:
    client = _build(tmp_path, {})
    r = client.get("/readyz")
    assert r.status_code == 200


def test_metrics_exposes_prometheus_format(tmp_path: Path) -> None:
    client = _build(tmp_path, {})
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]


def test_tools_list_no_auth(tmp_path: Path) -> None:
    client = _build(tmp_path, {})
    r = client.get("/mcp/tools")
    assert r.status_code == 200
    names = {t["name"] for t in r.json()["tools"]}
    assert {
        "diagnose_failed_channels",
        "analyze_dlq_and_suggest_reprocessing",
        "check_cluster_health",
        "full_mq_health_check",
    } <= names


# --- auth -------------------------------------------------------------------


def test_tools_call_without_bearer_returns_401(tmp_path: Path) -> None:
    client = _build(tmp_path, {})
    r = client.post("/mcp/tools/call", json={"tool": "health", "params": {}})
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers


def test_tools_call_with_invalid_bearer_returns_401(tmp_path: Path) -> None:
    client = _build(tmp_path, {})
    r = client.post(
        "/mcp/tools/call",
        json={"tool": "health", "params": {}},
        headers={"Authorization": "Bearer nope"},
    )
    assert r.status_code == 401


def test_tools_call_health_ok(tmp_path: Path) -> None:
    p = _principal({"nonprod-read"})
    client = _build(tmp_path, {"good-token": p})
    r = client.post(
        "/mcp/tools/call",
        json={"tool": "health", "params": {}},
        headers={"Authorization": "Bearer good-token"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# --- error mapping ----------------------------------------------------------


def test_tools_call_diagnose_channels_succeeds_for_nonprod_role(tmp_path: Path) -> None:
    p = _principal({"nonprod-read"})
    client = _build(tmp_path, {"t": p}, env="dev")
    r = client.post(
        "/mcp/tools/call",
        json={"tool": "diagnose_failed_channels", "params": {"qm_name": "DEMO_QM"}},
        headers={"Authorization": "Bearer t"},
    )
    assert r.status_code == 200
    assert r.json()["tool"] == "diagnose_failed_channels"


def test_tools_call_prod_qm_forbidden_for_nonprod_role(tmp_path: Path) -> None:
    p = _principal({"nonprod-read"})
    client = _build(tmp_path, {"t": p}, env="prod")
    r = client.post(
        "/mcp/tools/call",
        json={"tool": "diagnose_failed_channels", "params": {"qm_name": "DEMO_QM"}},
        headers={"Authorization": "Bearer t"},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "forbidden"


def test_tools_call_unknown_tool_returns_404(tmp_path: Path) -> None:
    p = _principal({"nonprod-read"})
    client = _build(tmp_path, {"t": p})
    r = client.post(
        "/mcp/tools/call",
        json={"tool": "no_such_tool", "params": {}},
        headers={"Authorization": "Bearer t"},
    )
    assert r.status_code == 404


def test_tools_call_missing_qm_returns_400(tmp_path: Path) -> None:
    p = _principal({"nonprod-read"})
    client = _build(tmp_path, {"t": p})
    r = client.post(
        "/mcp/tools/call",
        json={"tool": "diagnose_failed_channels", "params": {}},
        headers={"Authorization": "Bearer t"},
    )
    assert r.status_code == 400


def test_tools_call_malformed_body_400(tmp_path: Path) -> None:
    p = _principal({"nonprod-read"})
    client = _build(tmp_path, {"t": p})
    r = client.post(
        "/mcp/tools/call",
        content=b"not json",
        headers={
            "Authorization": "Bearer t",
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 400


def test_tools_call_oversized_body_413(tmp_path: Path) -> None:
    p = _principal({"nonprod-read"})
    client = _build(tmp_path, {"t": p})
    r = client.post(
        "/mcp/tools/call",
        content=b"x" * 10,
        headers={
            "Authorization": "Bearer t",
            "Content-Type": "application/json",
            "Content-Length": str(10 * 1024 * 1024),  # falsely declare 10MB
        },
    )
    assert r.status_code == 413


def test_full_health_check_via_http(tmp_path: Path) -> None:
    p = _principal({"nonprod-read"})
    client = _build(tmp_path, {"t": p})
    r = client.post(
        "/mcp/tools/call",
        json={"tool": "full_mq_health_check", "params": {"qm_name": "DEMO_QM"}},
        headers={"Authorization": "Bearer t"},
    )
    assert r.status_code == 200
    body: dict[str, Any] = r.json()
    assert body["tool"] == "full_mq_health_check"
    assert "summary" in body
    assert body["summary"]["overall_status"] in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "OK"}
