# HTTP Transport + OIDC

The MQ-Sentinel HTTP transport is the production deployment path: one central
server, behind a TLS-terminating ingress, that every engineer's AI client
connects to. OIDC bearer authentication applies to every tool invocation.

```
Claude Code / Desktop / Cursor ──HTTPS /mcp + SSO token──> MQ-Sentinel (K8s / VM)
                                                            │ inventory + MQ credentials
                                                            └─ MQ client, TLS, display-only ─> QMs
```

Engineers need no MQ client and no MQ credentials. The server holds both, and
checks each caller's token and roles on every call.

## Endpoints

| Method | Path             | Auth   | Purpose                                   |
| ------ | ---------------- | ------ | ----------------------------------------- |
| any    | `/mcp`           | Bearer | **MCP Streamable HTTP**: what AI clients connect to |
| GET    | `/.well-known/oauth-protected-resource/mcp` | none | OAuth metadata naming your IdP (RFC 9728), so clients can run SSO sign-in |
| GET    | `/healthz`       | none   | Liveness probe                            |
| GET    | `/readyz`        | none   | Readiness probe                           |
| GET    | `/metrics`       | none   | Prometheus metrics (intended for scraper) |
| GET    | `/mcp/tools`     | none   | List available tools (names + descriptions) |
| POST   | `/mcp/tools/call`| Bearer | Invoke a tool — returns tool JSON         |

## Connecting AI clients to `/mcp`

`/mcp` is a standard MCP server (Streamable HTTP, stateless, JSON responses),
so any replica can serve any request. Each request carries its caller's
token, and each tool call runs as that caller: RBAC, rate limits and the
audit log are per person.

**Claude Code**: install the `mq-sentinel-org` plugin and export
`MQS_SENTINEL_URL` ([plugin README](../plugins/mq-sentinel-org/README.md)),
or add the server directly:

```bash
claude mcp add --transport http mq-sentinel https://mq-sentinel.internal.your-org.com/mcp
```

**Claude Desktop / Cursor / VS Code**: add a remote (HTTP) MCP server with the
same URL in the client's MCP settings.

**SSO sign-in.** A request without a valid token gets `401` with
`WWW-Authenticate: Bearer ... resource_metadata="<url>"`. MCP clients follow
that to the metadata, find your IdP in `authorization_servers`, and open its
login page. For this to work:

1. Set `MQS_SERVER_PUBLIC_URL` to the URL clients use, e.g.
   `https://mq-sentinel.internal.your-org.com/mcp`. The Helm chart derives it
   from the first ingress host. It's the OAuth resource identifier, and the
   only Host header accepted besides localhost.
2. Set the `MQS_AUTH_OIDC_*` variables below. If your IdP needs an explicit
   scope for the MQ-Sentinel API (Entra ID: `api://<app-id>/.default`), set
   `MQS_AUTH_OIDC_SCOPES`.
3. Tokens must carry MQ-Sentinel's audience (`MQS_AUTH_OIDC_AUDIENCE`) and the
   `roles` claim (`nonprod-read` / `prod-read`).
4. The IdP must let the MCP client sign in. With dynamic client registration
   (Okta and Keycloak can enable it) this is automatic. Otherwise (for example,
   Entra ID), register an OAuth client for your MCP clients with your IdP team.
   Until then, users can pass a token directly:

   ```bash
   claude mcp add --transport http mq-sentinel https://mq-sentinel.internal.your-org.com/mcp \
     --header "Authorization: Bearer $TOKEN"
   ```

## REST API (`/mcp/tools/call`) for scripts and CI

`/mcp/tools/call` request body:

```json
{ "tool": "full_mq_health_check", "params": { "qm_name": "DEMO_QM" } }
```

Headers:

```
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
Content-Type: application/json
```

## OIDC — required in production

Configure via env (or the Helm `oidc` block):

| Variable                  | Example                                             |
| ------------------------- | --------------------------------------------------- |
| `MQS_AUTH_OIDC_ISSUER`    | `https://login.example.com/realms/mq-sentinel`      |
| `MQS_AUTH_OIDC_AUDIENCE`  | `mq-sentinel`                                       |
| `MQS_AUTH_OIDC_JWKS_URL`  | `https://login.example.com/.well-known/jwks.json`   |
| `MQS_AUTH_OIDC_SCOPES`    | `api://mq-sentinel/.default` (optional; advertised to MCP clients) |
| `MQS_SERVER_PUBLIC_URL`   | `https://mq-sentinel.internal.your-org.com/mcp`     |

If `MQS_SERVER_ENVIRONMENT=prod` and any of those are empty, the server
refuses to start. JWKS is fetched at startup, cached for 10 minutes, and
served stale on transient fetch errors.

### Token claims expected

| Claim     | Required | Notes                                                       |
| --------- | -------- | ----------------------------------------------------------- |
| `iss`     | yes      | must match configured issuer exactly                        |
| `aud`     | yes      | must match configured audience exactly                      |
| `exp`     | yes      | 30s leeway                                                  |
| `sub`     | yes      | becomes `Principal.subject` (audited)                       |
| `tenant`  | no       | becomes `Principal.tenant`                                  |
| `roles`   | no       | list[str], CSV, or space-delimited; or Keycloak `realm_access.roles` |

### RBAC

Role grants (from `auth/rbac.py`):

| Role           | Grants                              |
| -------------- | ----------------------------------- |
| `nonprod-read` | `read:nonprod`                      |
| `prod-read`    | `read:nonprod`, `read:prod`         |
| `admin-audit`  | `read:nonprod`, `read:prod`, `audit:view` |

A token without `prod-read` cannot invoke a tool against a QM whose
inventory `environment` is `prod` — the dispatcher returns 403.

## Error responses

| Status | Body example                                      | Meaning                            |
| ------ | ------------------------------------------------- | ---------------------------------- |
| 400    | `{"error": "tool_required"}`                      | malformed request                  |
| 401    | `{"error": "missing_bearer_token"}`               | no token, or token verify failed   |
| 403    | `{"error": "forbidden"}`                          | RBAC denied                        |
| 404    | `{"error": "not_found"}`                          | unknown tool or QM                 |
| 413    | `{"error": "request_too_large"}`                  | body > 64 KiB                      |
| 429    | `{"error": "rate_limited"}`                       | per-principal token bucket         |
| 500    | `{"error": "internal_error"}`                     | unexpected — never echoes details  |

## Local development

```bash
# Stub verifier (any non-empty token is accepted as local-dev / nonprod-read)
MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV=true \
uv run mq-sentinel serve --transport http --host 127.0.0.1 --port 8080

curl -s -H 'Authorization: Bearer dev' \
     -H 'Content-Type: application/json' \
     -d '{"tool":"full_mq_health_check","params":{"qm_name":"DEMO_QM"}}' \
     http://127.0.0.1:8080/mcp/tools/call | jq .summary

# Or as an MCP client. In local dev, /mcp accepts requests without a token.
claude mcp add --transport http mq-sentinel-local http://127.0.0.1:8080/mcp
```

## Operational notes

- **TLS terminates at ingress.** Run the pod on plain HTTP; require HTTPS at
  the load balancer / Ingress / Route. Never expose 8080 directly.
- **Rate limiting** is per-principal (token bucket, 60 rpm default — tunable
  via `MQS_SECURITY_RATE_LIMIT_PER_MINUTE`).
- **Audit log** continues to be hash-chained JSONL — every call is logged with
  the OIDC `sub`, tenant, tool, target QM, params hash, outcome, duration.
- **Metrics** emitted by `/metrics`:
  - `mq_sentinel_http_requests_total{method,path,status}`
  - `mq_sentinel_http_request_duration_seconds{method,path}`
  - `mq_sentinel_tool_calls_total{tool,outcome}`
- **CORS** is closed by default — the HTTP transport is intended for
  back-channel use by agents and CI, not browsers.
- **Host checks.** `/mcp` rejects Host headers other than localhost and
  `MQS_SERVER_PUBLIC_URL`'s host (`421`), which guards against DNS rebinding.
  With neither a loopback bind nor a public URL set, the check is off.
