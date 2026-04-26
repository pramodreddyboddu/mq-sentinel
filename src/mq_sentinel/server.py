"""MCP server entrypoint. Wires auth, audit, rate limit, sanitizer around every tool.

Phase 1 commit 1: scaffold only. Registers a single `health` tool to prove the
security middleware pipeline end to end. Real diagnostic tools arrive in
subsequent commits.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

import orjson

from mq_sentinel import __version__
from mq_sentinel.audit import AuditEvent, AuditLogger
from mq_sentinel.auth.oidc import Principal, StubOIDCVerifier
from mq_sentinel.config import Settings, load_settings
from mq_sentinel.security import RateLimiter, sanitize_mq_output
from mq_sentinel.telemetry import configure_telemetry, get_logger


def _hash_params(params: dict[str, Any]) -> str:
    canonical = orjson.dumps(params, option=orjson.OPT_SORT_KEYS)
    return hashlib.sha256(canonical).hexdigest()


class MQSentinelServer:
    """Security-wrapped tool dispatcher. Framework-agnostic so we can test without MCP."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or load_settings()
        configure_telemetry(self._settings.telemetry)
        self._log = get_logger("mq_sentinel.server")
        self._audit = AuditLogger(self._settings.audit.log_path)
        self._rate = RateLimiter(
            rate_per_minute=self._settings.security.rate_limit_per_minute,
            burst=self._settings.security.rate_limit_per_minute,
        )
        self._verifier = StubOIDCVerifier()

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
