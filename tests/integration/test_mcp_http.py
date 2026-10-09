"""MCP Streamable HTTP at /mcp: what Claude Code / Desktop / Cursor connect to.

Speaks raw MCP JSON-RPC over the ASGI app, the way a remote MCP client does.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from mq_sentinel import __version__
from mq_sentinel.auth.oidc import Principal, TokenVerificationError
from mq_sentinel.config import Settings
from mq_sentinel.connectors.fixture import FixtureConnector
from mq_sentinel.http_app import build_http_app
from mq_sentinel.inventory.models import QMEntry
from mq_sentinel.inventory.registry import InMemoryInventory
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.server import MQSentinelServer

pytestmark = pytest.mark.integration

_URL = "https://mq-sentinel.example.com"
_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}

_ALICE = Principal(subject="alice", tenant="t", roles=frozenset({"nonprod-read"}))
_BOB = Principal(subject="bob", tenant="t", roles=frozenset({"prod-read"}))


class _Verifier:
    def verify(self, token: str) -> Principal:
        try:
            return {"alice-token": _ALICE, "bob-token": _BOB}[token]
        except KeyError:
            raise TokenVerificationError("bad token") from None


class _Secrets:
    def resolve(self, secret_ref: str) -> MQCredential:
        return MQCredential(user="x", password="x")


def _qm(name: str, env: str) -> QMEntry:
    return QMEntry(
        qm_name=name, host="h", port=1414, channel="APP.SVRCONN", environment=env, secret_ref="x"
    )


def _settings(tmp_path: Path, *, local_dev: bool = False) -> Settings:
    s = Settings()
    s.audit.log_path = tmp_path / "audit.jsonl"
    s.auth.disable_auth_for_local_dev = local_dev
    s.auth.oidc_issuer = "https://idp.example.com"
    s.auth.oidc_scopes = "api://mq-sentinel/.default"
    s.server.public_url = f"{_URL}/mcp"
    return s


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    fixtures = Path(__file__).resolve().parents[2] / "demo-sandbox" / "fixtures"
    server = MQSentinelServer(
        _settings(tmp_path),
        inventory=InMemoryInventory([_qm("DEV_QM", "dev"), _qm("PROD_QM", "prod")]),
        secrets=_Secrets(),
        connector_factory=lambda: FixtureConnector(fixtures),
        verifier=_Verifier(),
    )
    with TestClient(build_http_app(server), base_url=_URL) as c:
        yield c


def _rpc(c: TestClient, method: str, params: dict[str, Any], token: str | None) -> Any:
    headers = dict(_HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return c.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        headers=headers,
    )


def _call(c: TestClient, token: str, tool: str, args: dict[str, Any]) -> dict[str, Any]:
    r = _rpc(c, "tools/call", {"name": tool, "arguments": args}, token)
    assert r.status_code == 200, r.text
    result: dict[str, Any] = r.json()["result"]
    return result


def test_missing_token_points_client_at_sso_metadata(client: TestClient) -> None:
    r = _rpc(client, "tools/list", {}, token=None)
    assert r.status_code == 401
    challenge = r.headers["www-authenticate"]
    assert 'resource_metadata="https://mq-sentinel.example.com/.well-known/' in challenge

    meta = client.get("/.well-known/oauth-protected-resource/mcp").json()
    assert meta["resource"] == f"{_URL}/mcp"
    assert meta["authorization_servers"] == ["https://idp.example.com"]
    assert meta["scopes_supported"] == ["api://mq-sentinel/.default"]


def test_invalid_token_rejected(client: TestClient) -> None:
    r = _rpc(client, "tools/list", {}, token="forged")
    assert r.status_code == 401
    assert 'error="invalid_token"' in r.headers["www-authenticate"]


def test_initialize_and_list_tools(client: TestClient) -> None:
    init = {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "t", "version": "1"},
    }
    result = _rpc(client, "initialize", init, "alice-token").json()["result"]
    assert result["serverInfo"] == {"name": "mq-sentinel", "version": __version__}
    assert "Call `health` first" in result["instructions"]
    tools = _rpc(client, "tools/list", {}, "alice-token").json()["result"]["tools"]
    assert len(tools) == 9
    channels = next(t for t in tools if t["name"] == "diagnose_failed_channels")
    assert set(channels["inputSchema"]["properties"]) == {"qm_name"}  # ctx is not exposed


def test_each_request_runs_as_its_own_caller(client: TestClient) -> None:
    for token, who in [("alice-token", "alice"), ("bob-token", "bob"), ("alice-token", "alice")]:
        health = _call(client, token, "health", {})["structuredContent"]
        assert health["principal"] == who


def test_rbac_applies_per_caller(client: TestClient) -> None:
    denied = _call(client, "alice-token", "diagnose_failed_channels", {"qm_name": "PROD_QM"})
    assert denied["isError"] is True
    assert "lacks required action" in denied["content"][0]["text"]

    allowed = _call(client, "bob-token", "diagnose_failed_channels", {"qm_name": "PROD_QM"})
    assert not allowed.get("isError")
    assert allowed["structuredContent"]["findings"]

    alice_view = _call(client, "alice-token", "health", {})["structuredContent"]
    assert [q["qm_name"] for q in alice_view["queue_managers"]] == ["DEV_QM"]


def test_calls_are_audited_with_caller_identity(client: TestClient, tmp_path: Path) -> None:
    _call(client, "bob-token", "diagnose_failed_channels", {"qm_name": "PROD_QM"})
    records = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    assert {
        "actor": "bob",
        "tool": "diagnose_failed_channels",
        "target_qm": "PROD_QM",
    }.items() <= records[-1].items()


def test_unknown_host_rejected(client: TestClient) -> None:
    headers = {**_HEADERS, "Authorization": "Bearer alice-token", "Host": "evil.example.net"}
    r = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers=headers
    )
    assert r.status_code == 421


def test_local_dev_needs_no_token(tmp_path: Path) -> None:
    server = MQSentinelServer(_settings(tmp_path, local_dev=True))
    with TestClient(build_http_app(server), base_url=_URL) as c:
        health = _call(c, "", "health", {})["structuredContent"]
        assert health["principal"] == "local-dev"
        assert [q["qm_name"] for q in health["queue_managers"]] == ["DEMO_QM"]
        # No IdP is advertised when auth is disabled.
        assert c.get("/.well-known/oauth-protected-resource/mcp").status_code == 404
