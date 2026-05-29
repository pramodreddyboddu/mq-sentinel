# Changelog

All notable changes to MQ-Sentinel are documented here. The format is loosely based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] — 2026-05-04 — verified-citation knowledge base

Expands the Knowledge Center coverage that is MQ-Sentinel's real moat, and
adds infrastructure guaranteeing every IBM citation stays live.

### Added

- **16 new reason codes** in the KC registry, covering the most common
  on-call pages: connectivity/availability (2009, 2058, 2059, 2161, 2162),
  object resolution (2085, 2087, 2189), inhibited/capacity (2016, 2192, 2042),
  and TLS/security (2393, 2397, 2400). Registry now covers 23 reason codes,
  8 AMQ codes, and 18 topic pages.
- **`KCRegistry.all_refs()` / `.reason_codes()` / `.amq_codes()`** —
  enumeration accessors used by the link checker and structural tests.
- **`scripts/verify_kc_links.py`** — fetches every URL in the registry
  (concurrently, with soft-404 body detection) and exits non-zero on any
  dead link. `--json` for machine-readable output.
- **`.github/workflows/verify-kc-links.yml`** — runs the link checker daily
  (07:00 UTC) and on demand. Network-dependent, so it's a scheduled job, not
  a PR gate. Catches IBM doc reorganizations within a day.
- **`tests/unit/test_kc_registry_structure.py`** — offline structural
  validation that runs on every PR: every URL is `https://www.ibm.com/...`,
  reason-code slugs encode the same code they're keyed under (catches
  copy-paste errors like keying 2059 to the 2058 slug), AMQ slugs match
  their code, no duplicate URLs, and a coverage floor (≥20 reason codes,
  ≥7 AMQ codes) so a regression that drops codes fails CI.

### Verified

- All 47 registry URLs returned HTTP 200 at release time
  (`uv run python scripts/verify_kc_links.py`).

### Build status

- 271 tests passing (99 new — mostly the parametrized structural checks).
- `mypy --strict` clean. `ruff` lint + format clean.

### Why this matters

The entire trust story is "every recommendation cites IBM." A single 404 in
front of an IBM admin undermines the whole tool. This release makes a broken
citation a CI failure instead of a lost customer — and roughly triples the
reason-code coverage in the process.

---

## [0.2.0] — 2026-05-03 — IBM-recommended remediation recipes

This release turns MQ-Sentinel from a "what's wrong" diagnostic into a
complete on-call SRE assistant. Every finding now carries IBM-recommended
**fix commands** alongside the read-only diagnostic checks — returned as
text only, never executed.

### Added

- **`RemediationScenario` dataclass** in `mq_sentinel.rcs.engine`. Each
  finding can carry multiple scenario-specific fix recipes:
  ```python
  RemediationScenario(
      scenario="CHLAUTH BLOCKUSER rule incorrectly matching",
      commands=("SET CHLAUTH('APP.SVRCONN') TYPE(BLOCKUSER) ...",),
      notes="Optional prerequisites / warnings / rollback guidance.",
  )
  ```
- **`RCSFinding.remediation_steps`** field — `tuple[RemediationScenario, ...]`
  populated by every matcher.
- **`execution_policy` response field** on every finding —
  machine-readable safety statement: "MQ-Sentinel never executes
  remediation_steps. These are IBM-recommended fix commands returned as
  TEXT only for the operator to review and run manually in a change
  window. The MCP server is read-only by construction."
- **All 8 matchers updated** with IBM-recommended remediation recipes
  drawn from IBM Knowledge Center:
  - Channels: 2035 (3 scenarios — BLOCKUSER, MCAUSER perms, CONNAUTH),
    2009/2059 (listener restart, channel restart, TLS cipher), INDOUBT
    (RESOLVE CHANNEL with strong data-loss warning), generic bad status.
  - DLQ: 2035/2080/2030/2051/2053/2079 (one scenario each), depth
    (runmqdlq + dmpmqmsg), backout loop (BOTHRESH/BOQNAME config).
  - Cluster: partial repository, unhealthy cluster channel, stale
    CLUSQMGR, suspended member, self-only membership.
  - Native HA: quorum loss, no active, split-brain (IBM-support warning),
    replica disconnected, log replay lag, CRR lag.
  - RDQM: Pacemaker quorum, offline nodes, failed resources, DRBD
    split-brain (**explicit data-loss warning + IBM-support-first
    notice**), connection state, disk state, no running node.
  - z/OS: QSG member, CHIN, page set expansion, buffer pool sizing, CF
    structure recovery.
  - MIQM: no active, dual-active (corruption warning), no standby
    permission, shared FS, failover history.

### Safety invariants (new tests)

`tests/security/test_remediation_isolation.py` enforces three guarantees:

1. **`remediation_steps` is never iterated outside the model layer.** A
   source-code grep test fails CI if any non-engine, non-matcher file
   accesses `.remediation_steps` (which would be the path to
   execution).
2. **Matchers never call connectors.** The matcher source files contain
   no `connector.execute_mqsc`, `connector.execute_shell`, or
   `connector.browse_dlq` references.
3. **`fix_steps` ⊆ allowlist, `remediation_steps` ⊄ allowlist.** Every
   `fix_steps` string passes `assert_mqsc_allowed`. Every
   `remediation_steps` command (sample tested with `ALTER QMGR ...`)
   is REJECTED by the allowlist — proving they would not execute even
   if accidentally passed through.

### Changed

- `RCSFinding.as_dict()` now emits `remediation_steps` and
  `execution_policy` fields. All MCP responses across stdio and HTTP
  transports include them automatically.
- Demo script (`demo/run.sh`) Scene 3 expanded to show the new format
  with side-by-side diagnostic and remediation blocks, plus the
  explicit safety footer.

### Build status

- 172 tests passing (5 new in `tests/security/test_remediation_isolation.py`).
- `mypy --strict` clean across 50 source files.
- `ruff` lint + format clean.

### Why this matters

Banks, healthcare, telcos already trust read-only diagnostics. With
remediation recipes attached, **Tier-1 ops can resolve incidents
without paging the MQ SME** — they have the diagnosis, the exact
commands to type, the IBM doc citation, and a safe execution model
(the MCP never runs the destructive commands).

This is what closes the loop from "what's wrong?" to "how do I fix it?"
— while preserving the read-only safety posture that got the product
through InfoSec in the first place.

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
