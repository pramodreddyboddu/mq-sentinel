"""MCP server entrypoint. Wires auth, audit, rate limit, sanitizer around every tool.

The dispatcher is framework-agnostic so unit tests can drive it without an
MCP transport. The MCP stdio transport is wired by `serve_stdio()`.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import orjson

from mq_sentinel import __version__
from mq_sentinel.audit import AuditEvent, AuditLogger
from mq_sentinel.auth.oidc import Principal, StubOIDCVerifier
from mq_sentinel.auth.rbac import Action, authorize
from mq_sentinel.config import Settings, load_settings
from mq_sentinel.connectors.base import MQConnector
from mq_sentinel.connectors.fixture import FixtureConnector
from mq_sentinel.inventory.registry import InMemoryInventory, InventoryRegistry
from mq_sentinel.secrets.backend import SecretsBackend
from mq_sentinel.security import RateLimiter, sanitize_mq_output
from mq_sentinel.telemetry import configure_telemetry, get_logger
from mq_sentinel.tools.channels import TOOL_NAME as CHANNELS_TOOL_NAME
from mq_sentinel.tools.channels import diagnose_failed_channels
from mq_sentinel.tools.dlq import TOOL_NAME as DLQ_TOOL_NAME
from mq_sentinel.tools.dlq import analyze_dlq


def _hash_params(params: dict[str, Any]) -> str:
    canonical = orjson.dumps(params, option=orjson.OPT_SORT_KEYS)
    return hashlib.sha256(canonical).hexdigest()


class _NullSecrets:
    """No-op secrets backend for fixture mode (no real credentials needed)."""

    def resolve(self, secret_ref: str) -> Any:
        from mq_sentinel.secrets.backend import MQCredential

        return MQCredential(user="fixture", password="fixture")  # noqa: S106


class MQSentinelServer:
    """Security-wrapped tool dispatcher."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        inventory: InventoryRegistry | None = None,
        secrets: SecretsBackend | None = None,
        connector_factory: Callable[[], MQConnector] | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        configure_telemetry(self._settings.telemetry)
        self._log = get_logger("mq_sentinel.server")
        self._audit = AuditLogger(self._settings.audit.log_path)
        self._rate = RateLimiter(
            rate_per_minute=self._settings.security.rate_limit_per_minute,
            burst=self._settings.security.rate_limit_per_minute,
        )
        self._verifier = StubOIDCVerifier()
        self._inventory: InventoryRegistry = inventory or InMemoryInventory()
        self._secrets: SecretsBackend = secrets or _NullSecrets()
        self._connector_factory: Callable[[], MQConnector] = (
            connector_factory or self._default_connector_factory
        )

    @staticmethod
    def _default_connector_factory() -> MQConnector:
        # In dev, fall back to a fixture connector pointed at demo-sandbox.
        return FixtureConnector(Path("./demo-sandbox/fixtures"))

    # --- tool surface -----------------------------------------------------

    def health(self, principal: Principal) -> dict[str, Any]:
        result: dict[str, Any] = sanitize_mq_output(
            {
                "status": "ok",
                "version": __version__,
                "environment": self._settings.server.environment,
                "principal": principal.subject,
            }
        )
        return result

    def diagnose_channels(self, qm_name: str, principal: Principal) -> dict[str, Any]:
        # RBAC: prod QMs require prod-read role.
        try:
            entry = self._inventory.get(qm_name)
        except LookupError:
            authorize(principal, Action.READ_NONPROD)
            raise
        action = Action.READ_PROD if entry.environment == "prod" else Action.READ_NONPROD
        authorize(principal, action)

        return diagnose_failed_channels(
            qm_name=qm_name,
            connector_factory=self._connector_factory,
            inventory=self._inventory,
            secrets=self._secrets,
        )

    def analyze_dlq(
        self,
        qm_name: str,
        principal: Principal,
        sample_size: int = 50,
    ) -> dict[str, Any]:
        try:
            entry = self._inventory.get(qm_name)
        except LookupError:
            authorize(principal, Action.READ_NONPROD)
            raise
        action = Action.READ_PROD if entry.environment == "prod" else Action.READ_NONPROD
        authorize(principal, action)
        return analyze_dlq(
            qm_name=qm_name,
            connector_factory=self._connector_factory,
            inventory=self._inventory,
            secrets=self._secrets,
            sample_size=sample_size,
        )

    # --- dispatch ---------------------------------------------------------

    def dispatch(
        self,
        *,
        token: str,
        tool: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        started = time.monotonic()
        principal: Principal | None = None
        outcome = "error"
        error: str | None = None
        target_qm = params.get("qm_name") if isinstance(params, dict) else None
        try:
            principal = self._verifier.verify(token)
            if not self._rate.allow(principal.subject):
                outcome = "denied"
                raise PermissionError("rate limit exceeded")

            if tool == "health":
                result = self.health(principal)
            elif tool == CHANNELS_TOOL_NAME:
                if not isinstance(target_qm, str):
                    raise ValueError("qm_name (str) parameter required")
                result = self.diagnose_channels(target_qm, principal)
            elif tool == DLQ_TOOL_NAME:
                if not isinstance(target_qm, str):
                    raise ValueError("qm_name (str) parameter required")
                sample = params.get("sample_size", 50)
                if not isinstance(sample, int):
                    raise ValueError("sample_size must be an int")
                result = self.analyze_dlq(target_qm, principal, sample_size=sample)
            else:
                raise LookupError(f"unknown tool: {tool}")

            outcome = "ok"
            return result
        except Exception as exc:
            error = type(exc).__name__
            self._log.warning("tool_dispatch_failed", tool=tool, error=error)
            raise
        finally:
            duration_ms = int((time.monotonic() - started) * 1000)
            self._audit.write(
                AuditEvent(
                    actor=principal.subject if principal else "unauthenticated",
                    tenant=principal.tenant if principal else None,
                    tool=tool,
                    target_qm=target_qm if isinstance(target_qm, str) else None,
                    params_hash=_hash_params(params or {}),
                    outcome=outcome,
                    duration_ms=duration_ms,
                    error=error,
                )
            )


# --- MCP stdio transport --------------------------------------------------


def serve_stdio(server: MQSentinelServer | None = None) -> None:
    """Run the MCP server over stdio.

    The MCP SDK API is imported lazily so unit tests don't require it.
    Each tool call is routed through `MQSentinelServer.dispatch` so all
    security middleware (auth, rate limit, allowlist, sanitizer, audit)
    runs uniformly regardless of transport.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("MCP SDK not installed. Run `uv sync --extra dev` to install.") from exc

    srv = server or MQSentinelServer()
    mcp = FastMCP("mq-sentinel")

    # In stdio mode the local agent is trusted; we issue a dev token for the
    # dispatcher's audit trail. Production deployments use the HTTP transport
    # with OIDC bearer tokens (lands in a later commit).
    dev_token = "stdio-local"  # noqa: S105

    @mcp.tool(description="Health probe — confirms the MCP is responding.")
    def health() -> dict[str, Any]:
        return srv.dispatch(token=dev_token, tool="health", params={})

    @mcp.tool(
        description=(
            "Scan a Queue Manager's channels and return RCS findings with "
            "IBM Knowledge Center references for each detected issue. "
            "READ-ONLY."
        ),
    )
    def diagnose_failed_channels(qm_name: str) -> dict[str, Any]:
        return srv.dispatch(
            token=dev_token,
            tool=CHANNELS_TOOL_NAME,
            params={"qm_name": qm_name},
        )

    @mcp.tool(
        description=(
            "Inspect the dead-letter queue (HEADERS ONLY — message bodies "
            "are never read). Groups DLQ entries by MQ reason code, surfaces "
            "backout-loop offenders, and returns RCS findings with IBM KC "
            "references. READ-ONLY."
        ),
    )
    def analyze_dlq_and_suggest_reprocessing(qm_name: str, sample_size: int = 50) -> dict[str, Any]:
        return srv.dispatch(
            token=dev_token,
            tool=DLQ_TOOL_NAME,
            params={"qm_name": qm_name, "sample_size": sample_size},
        )

    mcp.run()
