# MQ-Sentinel

**Read-only, enterprise-grade IBM MQ diagnostic MCP server.**
Root cause + recommended fix steps + IBM Knowledge Center citations — for every IBM MQ deployment flavor, with zero hallucinations.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![mypy strict](https://img.shields.io/badge/mypy-strict-success.svg)](https://mypy.readthedocs.io/)
[![ruff](https://img.shields.io/badge/lint-ruff-orange.svg)](https://docs.astral.sh/ruff/)
[![tests 167 passing](https://img.shields.io/badge/tests-167%20passing-success.svg)]()
[![License Proprietary](https://img.shields.io/badge/license-proprietary-red.svg)](LICENSE)

> Status: **0.1.0 — Phase 1 complete.** Eight diagnostic tools across all ten IBM MQ flavors. stdio + HTTPS+OIDC transports. See [CHANGELOG](CHANGELOG.md).

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

## Supported IBM MQ flavors (Phase 1 complete)

Standalone · Multi-Instance QM · RDQM · Native HA · Native HA + CRR · Uniform Cluster · Traditional Cluster · z/OS Queue Sharing Group · MQ Appliance · Containerized.

## Diagnostic tools

| Tool | Covers | Demo finding |
|---|---|---|
| `diagnose_failed_channels` | Distributed channels | 2035 NOT_AUTHORIZED, 2009/2059 connection errors, INDOUBT, AMQ9202/9208/9503 |
| `analyze_dlq_and_suggest_reprocessing` | DLQ (headers only — never bodies) | Grouped by reason 2035/2080/2030/2051/2053/2079, backout-loop detection |
| `check_cluster_health` | Traditional + uniform cluster | Partial repository, stale CLUSQMGR, suspended members, unhealthy cluster channels |
| `diagnose_native_ha_issues` | K8s/OpenShift Native HA | Replica state, quorum, log replay lag, split-brain, CRR lag |
| `diagnose_rdqm_issues` | On-prem RHEL RDQM | Pacemaker quorum, offline nodes, DRBD connection/disk, split-brain |
| `diagnose_zos_qsg_issues` | z/OS Queue Sharing Group | QSG members, CHIN, page sets, buffer pools, CF structures |
| `diagnose_multi_instance_issues` | Traditional MIQM | Active/standby state, dual-active split, standby permission, failover events |
| `full_mq_health_check` | All of the above (composite) | Executive summary + ranked findings |

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

Phase 1 is complete (eight diagnostic tools, two transports, all ten flavors). See [CHANGELOG.md](CHANGELOG.md) for what's next:

- **0.2.0** — Air-gapped KC doc bundle; FIPS-140 build flag.
- **0.3.0** — Historical telemetry store for trend + anomaly detection.
- **0.4.0** — ServiceNow / Jira ticket auto-draft from RCS findings.
- **0.5.0** — SOC 2 evidence-pack generator.

Safe remediation is intentionally **out of scope**. MQ-Sentinel only reports.

## License

Proprietary — © 2026 MG. See [LICENSE](LICENSE). IBM® and IBM MQ® are trademarks of IBM Corporation; MG is not affiliated with IBM.
