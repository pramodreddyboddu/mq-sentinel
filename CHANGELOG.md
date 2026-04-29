# Changelog

All notable changes to MQ-Sentinel are documented here. The format is loosely based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-04-28 — Phase 1 complete

First end-to-end release. Eight diagnostic tools covering every IBM MQ flavor in
the v1.0 spec, two transports (stdio + HTTPS+OIDC), and a hardened deployment
path with audit, RBAC, and CI security gates.

### Added

**Diagnostic tools (read-only — DISPLAY/PING/dspmq/rdqmstatus/crm_mon/drbdadm only)**
- `health` — server liveness probe.
- `diagnose_failed_channels` — channel state + AMQERR log analysis (2035, 2009, 2059, INDOUBT, AMQ9202/9208/9503).
- `analyze_dlq_and_suggest_reprocessing` — safe DLQ inspection (HEADERS ONLY — bodies never read), grouped by reason code (2035/2080/2030/2051/2053/2079) with backout-loop detection.
- `check_cluster_health` — partial repository, stale CLUSQMGR entries, suspended members, unhealthy cluster channels, orphan QM detection.
- `diagnose_native_ha_issues` — replica state, quorum, log replay lag, split-brain, Cross-Region Replication lag.
- `diagnose_rdqm_issues` — Pacemaker quorum + offline nodes + failed resources, DRBD connection/disk/split-brain across multiple peers.
- `diagnose_zos_qsg_issues` — QSG members, CHIN, page set utilization, buffer pool free pages, coupling facility structure status.
- `diagnose_multi_instance_issues` — active/standby state, dual-active split detection, standby permission, failover events.
- `full_mq_health_check` — composite running channels + DLQ + cluster against a single connection, with executive summary (overall status, severity counts, top issues).

**Security foundation**
- Static MQSC + shell command allowlist (read-only verbs + diagnostic binaries with per-binary regex). Multi-statement / NUL-injected / case-obfuscated / comment-hidden destructive commands rejected by negative-test corpus.
- Prompt-injection firewall on every output: ANSI/control/zero-width/tag-character strip, jailbreak marker redaction, URL allowlist (`www.ibm.com` only), quarantine envelope.
- Hash-chained tamper-evident JSONL audit log; `mq-sentinel verify-audit` detects any retroactive edit.
- OIDC bearer auth with JWKS caching, configurable issuer/audience/roles/tenant claims, Keycloak `realm_access.roles` fallback.
- RBAC scopes: `nonprod-read`, `prod-read`, `admin-audit` — prod QMs gated by `prod-read`.
- Token-bucket rate limiter per principal.
- Pluggable secrets backend (filesystem/K8s default; Vault/AWS Secrets Manager/CyberArk adapters interface-ready).
- Distroless non-root container, read-only FS, dropped Linux capabilities, seccomp profile.
- CI security gates: ruff, mypy strict, pytest (incl. `-m security` corpus), pip-audit, CycloneDX SBOM, Trivy image scan, cosign signing.

**Transports**
- `stdio` (default) — for Claude Desktop, Cursor, Claude Code.
- `http` (production) — Starlette ASGI app, OIDC bearer auth, public `/healthz` `/readyz` `/metrics` `/mcp/tools`, protected `POST /mcp/tools/call`. 64 KiB body cap; error mapping never echoes internal details.

**Topology auto-detection** across Standalone, Multi-Instance, RDQM, Native HA (incl. CRR), Uniform Cluster, Traditional Cluster, z/OS QSG, MQ Appliance, Containerized — via `DISPLAY QMGR` + `DISPLAY QMSTATUS` + `dspmq` + `rdqmstatus`.

**MQ version awareness** — KC document URLs keyed to `(version, reason_code)` and `(version, AMQ code)` so 9.2 LTS / 9.3 / 9.4 / z/OS responses cite the correct page.

**Demo sandbox** — fully fixture-backed; runs end-to-end without any live IBM MQ. Seeded faults across every topology (channel 2035, DLQ depth 1247 with mixed reasons, cluster partial-repo + stale + suspended, Native HA replica disconnect + 60% replay + 420s CRR lag, RDQM Pacemaker offline + DRBD WFConnection + Inconsistent disk, z/OS PSID 97% + CHIN STOPPED + CF FAILED, MIQM dual-active).

### Build status

- 167 tests passing (40+ security negative tests, 8 e2e integration).
- `mypy --strict` clean across 50 source files.
- `ruff` lint + format clean.
- 77% line coverage.

### Out of scope (intentional)

- Safe remediation / auto-fix.
- Any command other than DISPLAY/PING/dspmq/rdqmstatus/crm_mon/drbdadm.
- LLM calls from the MCP server itself.

---

## Roadmap

- **0.2.0** — Air-gapped KC doc bundle for regulated environments; FIPS-140 build flag.
- **0.3.0** — Historical telemetry store (Postgres/Timescale) for trend + baseline anomaly detection.
- **0.4.0** — ServiceNow / Jira ticket auto-draft from RCS findings.
- **0.5.0** — SOC 2 evidence-pack generator.
