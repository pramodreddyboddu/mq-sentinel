# HTTP Transport + OIDC

The MQ-Sentinel HTTP transport is the production deployment path: a Starlette
ASGI app behind a TLS-terminating ingress, with OIDC bearer authentication
on every tool invocation.

## Endpoints

| Method | Path             | Auth   | Purpose                                   |
| ------ | ---------------- | ------ | ----------------------------------------- |
| GET    | `/healthz`       | none   | Liveness probe                            |
| GET    | `/readyz`        | none   | Readiness probe                           |
| GET    | `/metrics`       | none   | Prometheus metrics (intended for scraper) |
| GET    | `/mcp/tools`     | none   | List available tools (names + descriptions) |
| POST   | `/mcp/tools/call`| Bearer | Invoke a tool — returns tool JSON         |

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
