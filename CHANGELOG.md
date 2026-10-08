# Changelog

All notable changes to MQ-Sentinel are documented here. The format is loosely based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.4.0] — Live queue managers, Claude Code plugin, install fixes

### Live IBM MQ
- `mq-sentinel serve` can now diagnose real queue managers. `MQS_SERVER_CONNECTOR` (`auto` | `fixture` | `pymqi`): `auto` goes live when `MQS_SERVER_INVENTORY_DIR` is set. Credentials come from `MQS_SERVER_SECRETS_DIR` (filesystem / K8s Secret layout).
- New MQSC reply parser: the live connector turns `MQCMD_ESCAPE` EscapedReply text into the same `{ATTR: value}` rows the fixtures and matchers use. Before this, live rows were keyed by numeric PCF ids and every check came back empty.
- TLS: inventory `cipher_spec`, plus the secret's `cert_label`.
- Connection errors now include the MQ reason code (`MQRC 2035`, `2059`, `2393`, ...) and never the connection details.
- DLQ browse opens with `MQOO_BROWSE | MQOO_INQUIRE` only. It needs no `+get` and never blocks an exclusive-input DLQ handler.
- Host-local diagnostics (`dspmq`, `rdqmstatus`, `crm_mon`, `drbdadm`) only run when the inventory host is `localhost`, so a remote QM is never judged by another machine's state.
- Channels in doubt are detected from `INDOUBT(YES)` as live CHSTATUS reports it. MQ `VERSION(09040000)` is normalized to `9.4.0.0` so version-specific IBM doc links resolve.
- `health` reports `connector` (live / demo-fixtures) and the queue managers the caller may read.
- `prod` refuses to start on the demo fixture connector. **Breaking** for prod deployments that ran without an inventory: they had been serving demo data.
- `docs/onboard-new-qm.md` rewritten with least-privilege `setmqaut` grants, a CHLAUTH rule, and the real inventory schema. `examples/org/inventory-example.yaml` now matches the schema and is tested.

### Claude Code plugin
- Claude Code plugin marketplace: `/plugin marketplace add pramodreddyboddu/mq-sentinel`. Bundles the MCP server (via `uvx`), an `mq-triage` skill, and `/mq-health` and `/mq-status` commands. `MQS_PACKAGE=mq-sentinel[mq]==0.4.0` switches it to live mode.

### Packaging and CI
- Fixed: `mq_sentinel.secrets` was excluded from git and the 0.3.0 wheel by a broad `secrets/` ignore rule, so `uvx mq-sentinel serve` crashed on import. The rule now applies to the repo root only.
- Fixed: pinned `mcp<2`. mcp 2.x removed `FastMCP`, so fresh installs failed to start.
- Demo fixtures ship inside the wheel, and `serve` seeds a `DEMO_QM` entry when `environment=dev` and local-dev auth is on. A fresh install works from any directory.
- Added the missing `pyyaml` runtime dependency (the inventory loader imported it).
- CI was red since June (`--all-extras` tried to build pymqi without MQ headers). It now installs `--extra dev`, tests on 3.12 and 3.13, audits the locked dependency set, and smoke-runs the Docker image.
- Dockerfile: the builder (3.12) and distroless runtime (debian12 = 3.11) had different Python minors. Both are now 3.13.
- Dependency upgrades clear the starlette and urllib3 CVEs.
- Release workflow publishes to PyPI via trusted publishing, after checking the tag matches the version and smoke-importing the wheel.

## [Unreleased] — MCP distribution (any client)

- Official MCP Registry manifest at repo-root `server.json` (`io.github.pramodreddyboddu/mq-sentinel`).
- PyPI package `mq-sentinel` 0.3.0 is the public install target (`uvx mq-sentinel serve`).
- Docker label `io.modelcontextprotocol.server.name` required by the official registry.
- README `mcp-name` marker so a future PyPI package can be verified.
- `docs/mcp-clients.md` — copy-paste install for Grok, Claude Desktop, Claude Code, Cursor, Gemini CLI, ChatGPT.
- Project-scoped `.grok/config.toml` so Grok launched from this repo loads MQ-Sentinel.
- Replaced the fake `@modelcontextprotocol/server-mq-sentinel` npm snippet.
- Registry submit path rewritten: official registry first, then Smithery — not the old servers README PR.

## [Unreleased] — Owner Polish & DX (Full Ownership Mode)

Treated the project as a long-term owned artifact:
- Added `mq-sentinel tools` command — clean discovery of all diagnostics.
- Added `mq-sentinel doctor` — environment, pymqi, config, and audit path self-check.
- Added professional GitHub templates (PULL_REQUEST_TEMPLATE, bug/feature issue templates).
- Added VISION.md (owner principles, success criteria, roadmap philosophy).
- Added CONTRIBUTING.md with high bar for security-sensitive changes.
- Added DEVELOPMENT.md — detailed owner-level guide for contributors and future maintainers.
- Updated mcp-manifest.json, smithery metadata, CLI help text, and README for stronger owned-product voice.
- Consistent maintainer/author metadata across packaging.

These are additive, non-breaking improvements focused on discoverability, contributor experience, and long-term ownership quality.

## [Unreleased] — Org-Readiness Hardening

Major push to make MQ-Sentinel production- and org-ready for mid-to-large enterprises.

### Added
- Comprehensive Org-Readiness Plan (docs/ORG-READINESS-PLAN.md) with 7 phases.
- `docs/getting-started-platform-teams.md`, `docs/onboard-new-qm.md`, `docs/rbac-best-practices.md`.
- `docs/compliance/soc2-evidence-checklist.md`.
- Enhanced SECURITY_POSTURE.md and PRODUCTION.md (SLOs, full enterprise checklist).
- `docs/oidc-examples.md` with real IdP configs (Okta, Entra ID, Keycloak).
- `docs/metrics.md`.
- Helm improvements: HPA, ServiceMonitor, Ingress template, affinity, production values, ServiceAccount support.
- Fleet-scale inventory: `load_from_multiple` and directory loading, `inventory_dir` config support.
- Example org inventory in `examples/org/`.
- Grafana dashboard and Prometheus alerts in `observability/`.
- Updated smithery.yaml and launch materials with org positioning.
- Ingress and better volume support in Helm templates.

### Changed
- Chart.yaml bumped, better metadata for orgs.
- INSTALL.md and README updated with org focus and plan links.
- Inventory and server enhanced for large fleets.