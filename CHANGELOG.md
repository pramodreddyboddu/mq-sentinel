# Changelog

All notable changes to MQ-Sentinel are documented here. The format is loosely based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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