"""HTTP transport — Starlette ASGI app with OIDC bearer auth.

Exposes:
  - /mcp                — MCP Streamable HTTP (Bearer auth). What Claude Code,
                          Claude Desktop, Cursor etc. connect to.
  - GET  /.well-known/oauth-protected-resource/mcp — RFC 9728 metadata naming
                          the org IdP, so MCP clients can run the SSO sign-in
  - GET  /healthz       — liveness probe (no auth)
  - GET  /readyz        — readiness probe (no auth)
  - GET  /metrics       — Prometheus metrics (no auth; intended for cluster scrape)
  - GET  /mcp/tools     — list available tools (no auth — names + descriptions only)
  - POST /mcp/tools/call — invoke a tool (Bearer auth required)

Both /mcp and POST /mcp/tools/call forward (token, tool, params) to
MQSentinelServer.dispatch, so all middleware (auth verify, rate limit,
allowlist, sanitizer, audit) applies uniformly with the stdio transport.

TLS termination is expected at the ingress (K8s) — the app itself runs HTTP
internally. CORS is closed by default; add an origin allowlist if needed.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

import anyio
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from mcp.server.transport_security import TransportSecuritySettings
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from mq_sentinel import __version__
from mq_sentinel.auth.oidc import TokenVerificationError, parse_bearer
from mq_sentinel.auth.rbac import AuthorizationError
from mq_sentinel.config import Settings
from mq_sentinel.server import MQSentinelServer, build_mcp
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
    {
        "name": "diagnose_rdqm_issues",
        "description": "RDQM Pacemaker, DRBD replication, split-brain detection.",
    },
    {
        "name": "diagnose_zos_qsg_issues",
        "description": "z/OS QSG members, CHIN, page sets, buffer pools, CF structures.",
    },
    {
        "name": "diagnose_multi_instance_issues",
        "description": "MIQM active/standby state, dual-active detection, failover events.",
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
    return parse_bearer(request.headers.get("authorization"))


class _BearerGate:
    """Authenticate every request to the MCP endpoint before it reaches the SDK.

    Missing or invalid tokens get a 401 whose WWW-Authenticate header points at
    the OAuth protected-resource metadata, which is how MCP clients discover the
    org IdP and start the SSO sign-in. Authorization (RBAC per QM) still happens
    per tool call in MQSentinelServer.dispatch.
    """

    def __init__(
        self,
        app: ASGIApp,
        server: MQSentinelServer,
        *,
        allow_anonymous: bool,
        resource_metadata_url: str | None,
    ) -> None:
        self._app = app
        self._server = server
        self._allow_anonymous = allow_anonymous
        self._resource_metadata_url = resource_metadata_url

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            token = parse_bearer(Headers(scope=scope).get("authorization"))
            if token is None and not self._allow_anonymous:
                await self._deny(scope, receive, send, error=None)
                return
            if token is not None:
                try:
                    await anyio.to_thread.run_sync(self._server.authenticate, token)
                except TokenVerificationError:
                    await self._deny(scope, receive, send, error="invalid_token")
                    return
        await self._app(scope, receive, send)

    async def _deny(self, scope: Scope, receive: Receive, send: Send, *, error: str | None) -> None:
        challenge = 'Bearer realm="mq-sentinel"'
        if error:
            challenge += f', error="{error}"'
        if self._resource_metadata_url:
            challenge += f', resource_metadata="{self._resource_metadata_url}"'
        body = {"error": error or "missing_bearer_token"}
        response = JSONResponse(body, status_code=401, headers={"WWW-Authenticate": challenge})
        await response(scope, receive, send)


def _resource_url(settings: Settings) -> str:
    if settings.server.public_url:
        return settings.server.public_url.rstrip("/")
    return f"http://{settings.server.http_host}:{settings.server.http_port}/mcp"


def _metadata_path(resource_url: str) -> str:
    """RFC 9728: /.well-known/oauth-protected-resource + the resource's path."""
    return "/.well-known/oauth-protected-resource" + urlparse(resource_url).path


def _transport_security(settings: Settings) -> TransportSecuritySettings:
    """Host/Origin checks against DNS rebinding for loopback or a known public URL."""
    hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
    if settings.server.public_url:
        public = urlparse(settings.server.public_url)
        hosts.append(public.netloc)
        origins.append(f"{public.scheme}://{public.netloc}")
    elif settings.server.http_host not in ("127.0.0.1", "localhost", "::1"):
        # Behind an ingress with no public_url configured, the Host header is
        # unknown here; set MQS_SERVER_PUBLIC_URL to enable the check.
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True, allowed_hosts=hosts, allowed_origins=origins
    )


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
    settings = server.settings
    local_dev = settings.auth.disable_auth_for_local_dev
    mcp = build_mcp(
        server,
        # Local dev only: tokenless MCP clients act as the local-dev principal.
        default_token="http-local-dev" if local_dev else None,
        streamable_http_path="/mcp",
        # Stateless + JSON: any replica can serve any request (HPA, no sticky
        # sessions), and each request carries its own caller identity.
        stateless_http=True,
        json_response=True,
        transport_security=_transport_security(settings),
    )
    mcp.streamable_http_app()  # initialises mcp.session_manager

    resource_url = _resource_url(settings)
    advertise_idp = bool(settings.auth.oidc_issuer) and not local_dev
    metadata_path = _metadata_path(resource_url)
    metadata_url = (
        f"{urlparse(resource_url).scheme}://{urlparse(resource_url).netloc}{metadata_path}"
        if advertise_idp
        else None
    )

    async def protected_resource_metadata(_: Request) -> Response:
        doc: dict[str, Any] = {
            "resource": resource_url,
            "authorization_servers": [settings.auth.oidc_issuer],
            "bearer_methods_supported": ["header"],
            "resource_name": "MQ-Sentinel",
        }
        if settings.auth.oidc_scopes:
            doc["scopes_supported"] = settings.auth.oidc_scopes.split()
        return JSONResponse(doc)

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        async with mcp.session_manager.run():
            yield

    gate = _BearerGate(
        StreamableHTTPASGIApp(mcp.session_manager),
        server,
        allow_anonymous=local_dev,
        resource_metadata_url=metadata_url,
    )
    routes = [
        Route("/mcp", gate),
        Route("/healthz", _healthz, methods=["GET"]),
        Route("/readyz", _readyz, methods=["GET"]),
        Route("/metrics", _metrics, methods=["GET"]),
        Route("/mcp/tools", _tools_list, methods=["GET"]),
        Route("/mcp/tools/call", _make_tools_call(server), methods=["POST"]),
    ]
    if advertise_idp:
        routes.append(Route(metadata_path, protected_resource_metadata, methods=["GET"]))
    middleware = [Middleware(_MetricsMiddleware)]
    return Starlette(routes=routes, middleware=middleware, lifespan=lifespan)


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
