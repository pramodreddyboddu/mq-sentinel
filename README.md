# MQ-Sentinel

**Read-only, enterprise-grade IBM MQ diagnostic MCP server.**
Root cause + recommended fix steps + IBM Knowledge Center citations — for every IBM MQ deployment flavor, with zero hallucinations.

> Status: **Alpha (Commit 1 — enterprise foundation)**. Diagnostic tools land in Phase 1 per the v1.0 spec.

---

## Why MQ-Sentinel

IBM MQ admins burn hours chasing `2035`s, DLQ storms, Native HA replica lag, and stale `CLUSQMGR` entries across 9.2 / 9.3 / 9.4 / z/OS. MQ-Sentinel plugs into any MCP-capable agent (Claude, Cursor, Claude Code) and returns a **typed Root Cause Summary** with:

- The detected issue + MQ reason / AMQ code
- The actual MQSC / log evidence
- Recommended **read-only** commands to run
- A **direct link to the IBM Knowledge Center page** for the detected version

The MCP itself never calls an LLM and never invents a fix — it pattern-matches raw MQ output against a curated, version-aware registry.

## Security posture — baked in, not bolted on

- **Read-only always.** Static MQSC allowlist (`DISPLAY` / `DIS` / `PING CHANNEL` only). Destructive verbs are rejected by three layers: tool, connector, MQ-side `setmqaut`.
- **Prompt-injection firewall.** Every MQ-sourced string is sanitized (control chars, zero-width, ANSI, unicode tag chars, jailbreak markers) and wrapped in a quarantine envelope before leaving the server.
- **URL allowlist.** Responses may only cite `www.ibm.com`; all other URLs are redacted.
- **Tamper-evident audit log.** Hash-chained JSONL; `mq-sentinel verify-audit` detects any retroactive edit.
- **OIDC + RBAC.** Principals scoped to `nonprod-read` / `prod-read` / `admin-audit`. Cannot query prod QMs from a nonprod token.
- **Hardened runtime.** Distroless image, non-root, read-only FS, dropped capabilities, seccomp, network egress allowlist.
- **Supply chain.** SBOM, cosign-signed images, `pip-audit` + Trivy in CI, every PR security-gated.

See [SECURITY.md](SECURITY.md) and [docs/threat-model.md](docs/threat-model.md).

## Supported IBM MQ flavors (Phase 1)

Standalone · Multi-Instance QM · RDQM · Native HA · Native HA + CRR · Uniform Cluster · Traditional Cluster · z/OS Queue Sharing Group · MQ Appliance · Containerized.

## Supported MQ versions

**9.2 LTS, 9.3, 9.4 (incl. 9.4.4+), z/OS.** Version is auto-detected at connect time; KC doc links are keyed to the detected version.

## Quick start (dev)

```bash
uv sync --all-extras --dev
uv run mq-sentinel version
uv run mq-sentinel health
uv run pytest -q
uv run pytest -q -m security   # security-only suite must stay green
```

## Transports

```bash
# stdio (default — for Claude Desktop, Cursor, Claude Code)
uv run mq-sentinel serve

# HTTP (production — OIDC bearer auth, /healthz, /readyz, /metrics)
uv run mq-sentinel serve --transport http --host 0.0.0.0 --port 8080
```

See [docs/http-transport.md](docs/http-transport.md) for the OIDC config,
endpoint reference, and operational notes.

## Repository layout

```
src/mq_sentinel/
  security/     command allowlist, output sanitizer, rate limiter
  audit/        hash-chained JSONL audit logger
  auth/         OIDC + RBAC
  inventory/    QM registry (pluggable)
  secrets/      pluggable secrets backend (default: filesystem/K8s)
  connectors/   MQ connection layer (pymqi + fixture)
  rcs/          Root Cause Summary engine + KC doc registry
  tools/        MCP tools (populated Phase 1+)
  telemetry/    OpenTelemetry + structured logging
  cli/          control-plane CLI
deploy/
  Dockerfile    distroless, non-root, read-only FS
  helm/         Kubernetes chart (security defaults on)
tests/
  security/     allowlist + injection firewall corpus (non-negotiable)
  unit/
```

## Roadmap

- **Phase 1** — topology auto-detect + core tools (QM/Channel/Queue/DLQ/Cluster/HA/z/OS).
- **Phase 2** — Native HA + CRR depth, Appliance specifics.
- **Phase 3** — composite `full_mq_health_check(topology=auto)` + demo sandbox with injected faults.
- **Phase 4+** — historical trends, SOC2 evidence pack, air-gapped KC snapshot.

Safe remediation is intentionally **out of scope**. MQ-Sentinel only reports.

## License

Proprietary — © 2026 MG. See [LICENSE](LICENSE). IBM® and IBM MQ® are trademarks of IBM Corporation; MG is not affiliated with IBM.
