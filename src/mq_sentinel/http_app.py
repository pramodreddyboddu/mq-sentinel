"""HTTP transport — Starlette ASGI app with OIDC bearer auth.

Exposes:
  - GET  /healthz       — liveness probe (no auth)
  - GET  /readyz        — readiness probe (no auth)
  - GET  /metrics       — Prometheus metrics (no auth; intended for cluster scrape)
  - GET  /mcp/tools     — list available tools (no auth — names + descriptions only)
  - POST /mcp/tools/call — invoke a tool (Bearer auth required)

The POST endpoint forwards (token, tool, params) to MQSentinelServer.dispatch,
so all middleware (auth verify, rate limit, allowlist, sanitizer, audit)
applies uniformly with the stdio transport.

TLS termination is expected at the ingress (K8s) — the app itself runs HTTP
internally. CORS is closed by default; add an origin allowlist if needed.
"""

from __future__ import annotations

from typing import Any

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp

from mq_sentinel import __version__
from mq_sentinel.auth.oidc import TokenVerificationError
from mq_sentinel.auth.rbac import AuthorizationError
from mq_sentinel.server import MQSentinelServer
from mq_sentinel.telemetry import get_logger

_MAX_BODY_BYTES = 64 * 1024
_TOOLS_PUBLIC_LIST = [
    {"name": "health", "description": "Health probe."},
    {
        "name": "diagnose_failed_channels",
        "description": "Scan channels and return RCS findings.",
    },
    {
        "name": "analyze_dlq_and_suggest_reprocessing",
        "description": "Inspect DLQ headers (no bodies) and group by reason code.",
    },
    {
        "name": "check_cluster_health",
        "description": "Detect partial repos, stale entries, suspended members.",
    },
    {
        "name": "full_mq_health_check",
        "description": "Composite: channels + DLQ + cluster, ranked by severity.",
    },
    {
        "name": "diagnose_native_ha_issues",
        "description": "Native HA replica state, quorum, log replay lag, CRR.",
    },
]


# --- metrics ----------------------------------------------------------------

_REQ_COUNTER = Counter(
    "mq_sentinel_http_requests_total",
    "HTTP requests received by MQ-Sentinel",
    ["method", "path", "status"],
)
_REQ_LATENCY = Histogram(
    "mq_sentinel_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
)
_TOOL_COUNTER = Counter(
    "mq_sentinel_tool_calls_total",
    "Tool invocations through HTTP transport",
    ["tool", "outcome"],
)


# --- middleware -------------------------------------------------------------


class _MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path
        method = request.method
        with _REQ_LATENCY.labels(method=method, path=path).time():
            response: Response = await call_next(request)
        _REQ_COUNTER.labels(method=method, path=path, status=str(response.status_code)).inc()
        return response


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


# --- endpoints --------------------------------------------------------------


async def _healthz(_: Request) -> Response:
    return JSONResponse({"status": "ok", "version": __version__})


async def _readyz(_: Request) -> Response:
    return JSONResponse({"status": "ready", "version": __version__})


async def _metrics(_: Request) -> Response:
    payload = generate_latest()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)


async def _tools_list(_: Request) -> Response:
    return JSONResponse({"tools": _TOOLS_PUBLIC_LIST})


def _make_tools_call(server: MQSentinelServer) -> Any:
    log = get_logger("mq_sentinel.http")

    async def tools_call(request: Request) -> Response:
        # Enforce body size cap before reading.
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > _MAX_BODY_BYTES:
                    return JSONResponse({"error": "request_too_large"}, status_code=413)
            except ValueError:
                return JSONResponse({"error": "invalid_content_length"}, status_code=400)

        token = _extract_bearer(request)
        if not token:
            return JSONResponse(
                {"error": "missing_bearer_token"},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="mq-sentinel"'},
            )

        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 — malformed JSON
            return JSONResponse({"error": "invalid_json"}, status_code=400)

        if not isinstance(body, dict):
            return JSONResponse({"error": "body_must_be_object"}, status_code=400)
        tool = body.get("tool")
        params = body.get("params", {})
        if not isinstance(tool, str) or not tool:
            return JSONResponse({"error": "tool_required"}, status_code=400)
        if not isinstance(params, dict):
            return JSONResponse({"error": "params_must_be_object"}, status_code=400)

        try:
            result = server.dispatch(token=token, tool=tool, params=params)
        except TokenVerificationError:
            _TOOL_COUNTER.labels(tool=tool, outcome="unauthorized").inc()
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        except AuthorizationError:
            _TOOL_COUNTER.labels(tool=tool, outcome="forbidden").inc()
            return JSONResponse({"error": "forbidden"}, status_code=403)
        except LookupError:
            _TOOL_COUNTER.labels(tool=tool, outcome="not_found").inc()
            return JSONResponse({"error": "not_found"}, status_code=404)
        except PermissionError as exc:
            _TOOL_COUNTER.labels(tool=tool, outcome="rate_limited").inc()
            return JSONResponse({"error": "rate_limited", "detail": str(exc)}, status_code=429)
        except ValueError as exc:
            _TOOL_COUNTER.labels(tool=tool, outcome="bad_request").inc()
            return JSONResponse({"error": "bad_request", "detail": str(exc)}, status_code=400)
        except Exception as exc:  # noqa: BLE001 — top-level boundary
            _TOOL_COUNTER.labels(tool=tool, outcome="error").inc()
            log.warning("tools_call_failed", tool=tool, error=type(exc).__name__)
            return JSONResponse({"error": "internal_error"}, status_code=500)

        _TOOL_COUNTER.labels(tool=tool, outcome="ok").inc()
        return JSONResponse(result)

    return tools_call


# --- app factory ------------------------------------------------------------


def build_http_app(server: MQSentinelServer) -> ASGIApp:
    routes = [
        Route("/healthz", _healthz, methods=["GET"]),
        Route("/readyz", _readyz, methods=["GET"]),
        Route("/metrics", _metrics, methods=["GET"]),
        Route("/mcp/tools", _tools_list, methods=["GET"]),
        Route("/mcp/tools/call", _make_tools_call(server), methods=["POST"]),
    ]
    middleware = [Middleware(_MetricsMiddleware)]
    return Starlette(routes=routes, middleware=middleware)


def serve_http(
    server: MQSentinelServer | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> None:
    """Run the HTTP transport with uvicorn. TLS terminates at ingress."""
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("uvicorn not installed") from exc
    srv = server or MQSentinelServer()
    app = build_http_app(srv)
    uvicorn.run(app, host=host, port=port, log_level="info", access_log=True)
