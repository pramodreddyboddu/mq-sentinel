# MQ-Sentinel — Architecture (Commit 1)

```
                ┌────────────────────────────────────────────────┐
                │                MCP Client (Claude/Cursor)       │
                └─────────────────┬──────────────────────────────┘
                                  │ MCP (stdio / streamable HTTP)
                ┌─────────────────▼──────────────────────────────┐
                │                MQ-Sentinel Server              │
                │  ┌──────────────┐  ┌──────────────┐  ┌──────┐  │
                │  │ OIDC verify  │→ │ Rate limiter │→ │ RBAC │  │
                │  └──────────────┘  └──────────────┘  └──┬───┘  │
                │                                          ▼      │
                │  ┌──────────────────────────────────────────┐  │
                │  │            Tool dispatcher                │  │
                │  └─────────────┬────────────────────┬───────┘  │
                │                ▼                    ▼           │
                │      ┌──────────────┐      ┌──────────────┐    │
                │      │ MQSC allow-  │      │   Sanitizer  │    │
                │      │   list       │      │ (output)     │    │
                │      └───────┬──────┘      └──────┬───────┘    │
                │              ▼                    ▲             │
                │      ┌──────────────┐     ┌──────────────┐     │
                │      │  Connector   │ → raw→ RCS engine  │     │
                │      │  (pymqi/fix) │     │ + KC registry │     │
                │      └───────┬──────┘     └──────────────┘     │
                │              │                                  │
                │      ┌───────▼──────────────────────────────┐  │
                │      │   Audit (hash-chained JSONL)         │  │
                │      └───────────────────────────────────────┘  │
                └─────────────────┬──────────────────────────────┘
                                  │ TLS 1.3, mTLS, CONNAUTH
                ┌─────────────────▼──────────────────────────────┐
                │         IBM MQ Queue Managers (read-only SA)    │
                └────────────────────────────────────────────────┘
```

## Key modules (src/mq_sentinel)

- `security/allowlist.py` — static MQSC + shell allowlist. Read-only enforcement.
- `security/sanitizer.py` — prompt-injection firewall. Applied to every MQ-sourced string.
- `security/ratelimit.py` — token bucket.
- `audit/logger.py` — SHA-256 chained JSONL audit log.
- `auth/oidc.py` + `auth/rbac.py` — identity + role scoping.
- `inventory/` — QM registry; credentials held only by refs.
- `secrets/` — pluggable backend (filesystem default; Vault/ASM/CyberArk adapters).
- `connectors/base.py` + `connectors/fixture.py` — connector protocol; fixture impl for tests/demo. pymqi impl arrives with Phase 1 commit 2.
- `rcs/engine.py` + `rcs/kc_registry.py` — hallucination-free finding builder + version-aware KC doc registry.
- `server.py` — dispatcher wiring all of the above.
- `cli/main.py` — `serve`, `health`, `verify-audit`, `version`.
