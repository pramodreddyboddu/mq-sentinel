# MQ-Sentinel

**Production-grade, read-only IBM MQ diagnostic MCP server that AI agents can safely use — with zero hallucinations.**

I built this as a serious side project to solve a real, high-stakes problem in enterprise environments. It is now a strong public portfolio piece demonstrating systems engineering, security, observability, production deployment, and building safe infrastructure for AI agents.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![mypy strict](https://img.shields.io/badge/mypy-strict-success.svg)](https://mypy.readthedocs.io/)
[![ruff](https://img.shields.io/badge/lint-ruff-orange.svg)](https://docs.astral.sh/ruff/)
[![tests 271 passing](https://img.shields.io/badge/tests-271%20passing-success.svg)]()
[![Org-Ready](https://img.shields.io/badge/org--ready-✓-blue)](docs/ORG-READINESS-PLAN.md)

> **0.3.0** — 8 diagnostic tools across all 10 IBM MQ flavors. Read-only by design. Prompt-injection firewall. OIDC + RBAC. Hash-chained audit. Verified IBM Knowledge Center citations (CI-enforced). Production Helm with HPA + air-gapped packaging.

**GitHub:** https://github.com/pramodreddyboddu/mq-sentinel  
**Live Demo:** https://mq-sentinel.io

---

## The Problem I Solved

Enterprise IBM MQ teams waste hours diagnosing issues like:
- 2035 NOT_AUTHORIZED storms
- Exploding DLQs
- Native HA replica lag and split-brain
- Stale cluster members
- z/OS mysteries

Traditional tools require deep expertise and manual log diving. Handing an LLM raw MQ access is unacceptable for security and compliance teams.

**MQ-Sentinel** gives Claude, Cursor, Grok, and other agents a safe MCP interface that returns accurate, cited diagnostics without ever hallucinating or executing destructive commands.

---

## The Problem

IBM MQ teams (banks, telcos, insurance, gov) waste hours on:
- `2035 NOT_AUTHORIZED` channel storms
- Exploding DLQs
- Native HA replica lag / split-brain
- Stale cluster members
- z/OS QSG mysteries

Traditional tools require deep MQSC knowledge and grepping logs. Giving an LLM direct MQ access is a non-starter for security/compliance teams.

**MQ-Sentinel solves this** by giving Claude, Cursor, Grok, etc. a safe, read-only MCP interface that returns **typed Root Cause + Fix Steps + verified IBM docs** — never fabricates, never executes destructive commands.

---

## 🎬 See it in 90 seconds

```bash
git clone https://github.com/pramodreddyboddu/mq-sentinel.git
cd mq-sentinel
make demo
```

Watch MQ-Sentinel diagnose a real `2035 NOT_AUTHORIZED`, an `INDOUBT` channel, a 1247-message DLQ, and a Native HA replica disconnect — all against the bundled fixture sandbox. No live IBM MQ required.

[![asciicast](https://img.shields.io/badge/%E2%96%B6-watch%20the%20cast-9333ea?style=for-the-badge)](demo/README.md) &nbsp; [![Try live demo](https://img.shields.io/badge/%F0%9F%8C%90-try%20live%20demo-3b82f6?style=for-the-badge)](https://mq-sentinel.io)

> Want to record it for sharing? `make demo-record` produces a browser-playable asciinema cast.

**Quick self-check (no MQ needed):**

```bash
uv run mq-sentinel doctor
uv run mq-sentinel tools     # list all diagnostics
uv run mq-sentinel info      # overview + security highlights
```

### Architecture at a Glance

```mermaid
flowchart TB
    subgraph Client["MCP Client (Claude / Cursor / Grok)"]
        P[Prompt]
    end

    subgraph Sentinel["MQ-Sentinel (read-only)"]
        OIDC[OIDC + RBAC]
        RL[Rate Limiter]
        DISP[Tool Dispatcher]
        ALLOW[MQSC Allowlist]
        CONN[Connector<br/>(pymqi / fixture)]
        RCS[RCS Engine +<br/>KC Registry]
        SAN[Output Sanitizer]
        AUDIT[Hash-chained<br/>Audit Log]
    end

    subgraph MQ["IBM MQ (read-only service account)"]
        QM[Queue Managers]
    end

    P -->|MCP stdio / HTTP| OIDC
    OIDC --> RL --> DISP
    DISP --> ALLOW
    ALLOW --> CONN
    CONN -->|raw output| RCS
    RCS --> SAN
    SAN --> AUDIT
    CONN --> QM
    QM -.->|DISPLAY only| CONN
```

Safe by design. No LLM inside the server. Every citation verified in CI.

---

## Why This Stands Out as a Portfolio Project

This is not a toy or weekend demo. It demonstrates real engineering depth:

- **Systems + Security Engineering**: Full threat model, multi-layer read-only enforcement, prompt-injection firewall, OIDC+RBAC, tamper-evident audit, hardened containers, SBOM + signed images.
- **Production Operations**: Production Helm (HPA, ServiceMonitor, NetworkPolicy), air-gapped packaging (RPM/DEB), observability out of the box.
- **AI Agent Infrastructure**: A complete, safe MCP server (stdio + HTTP) designed for real use by agents like Claude, Cursor, and Grok.
- **Enterprise Domain Expertise**: Deep coverage of IBM MQ across 10 topologies with version-aware, verified citations.
- **Systematic Delivery**: Executed a full 7-phase org-readiness plan with compliance artifacts that actual organizations need.

**Built with Grok Build** (primary coding partner) while maintaining strict engineering standards.

Full journey and plan: [docs/ORG-READINESS-PLAN.md](docs/ORG-READINESS-PLAN.md)

See also: [VISION.md](VISION.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [DEVELOPMENT.md](DEVELOPMENT.md)

---

## The Journey (Portfolio Story)

I built MQ-Sentinel to solve a painful, recurring problem in enterprise IBM MQ environments — and I treated the entire effort as a serious engineering and portfolio project.

I used **Grok Build** (xAI) as my primary coding partner from architecture through implementation, docs, Helm, compliance artifacts, and polish. Every major decision was deliberate: read-only first, citations that can't go stale, defense-in-depth, production packaging.

Key milestones:
- Designed threat model + multi-layer security architecture before writing the first tool
- Delivered 8 diagnostic tools across 10 MQ flavors with CI-enforced IBM Knowledge Center citations
- Production deployment (Helm + HPA + ServiceMonitor, distroless, air-gapped RPM/DEB)
- Full 7-phase org-readiness plan executed (see links above)
- 271+ tests (including security-negative tests), strict mypy, comprehensive docs for platform teams

This shows end-to-end ownership: deep domain knowledge, security by design, production operations, and shipping artifacts that real organizations can actually use.

**This is my public portfolio project.** It demonstrates systems engineering, security, observability, AI infrastructure, and disciplined delivery.

Built with Grok Build while holding high standards throughout.

## Security posture — baked in, not bolted on

- **Read-only always.** Static MQSC allowlist (`DISPLAY` / `DIS` / `PING CHANNEL` only). Destructive verbs are rejected by three layers: tool, connector, MQ-side `setmqaut`.
- **Prompt-injection firewall.** Every MQ-sourced string is sanitized (control chars, zero-width, ANSI, unicode tag chars, jailbreak markers) and wrapped in a quarantine envelope before leaving the server.
- **URL allowlist + live verification.** Responses may only cite `www.ibm.com`; all other URLs are redacted. Every citation in the registry (20+ reason codes, 8 AMQ codes, 18 topic pages) is fetched daily in CI — a dead link fails the build, not the customer.
- **Tamper-evident audit log.** Hash-chained JSONL; `mq-sentinel verify-audit` detects any retroactive edit.
- **OIDC + RBAC.** Principals scoped to `nonprod-read` / `prod-read` / `admin-audit`. Cannot query prod QMs from a nonprod token.
- **Hardened runtime.** Distroless image, non-root, read-only FS, dropped capabilities, seccomp, network egress allowlist.
- **Supply chain.** SBOM, cosign-signed images, `pip-audit` + Trivy in CI, every PR security-gated.

See [SECURITY.md](SECURITY.md) and [docs/threat-model.md](docs/threat-model.md).

**Org / Enterprise Ready?**  
This project was deliberately built for real organizations (banks, gov, large enterprises). See the complete journey:

See [VISION.md](VISION.md) for the owner product principles and long-term thinking.

- [Org-Readiness Plan](docs/ORG-READINESS-PLAN.md) — 7-phase plan executed end-to-end
- [Production Guide](docs/PRODUCTION.md) + [Platform Team Onboarding](docs/getting-started-platform-teams.md)
- [Security Posture](docs/SECURITY_POSTURE.md) + [SOC2 Evidence Checklist](docs/compliance/soc2-evidence-checklist.md)
- [RBAC & Auth Examples](docs/oidc-examples.md) (Okta, Entra ID, Keycloak)
- Production Helm with HPA, ServiceMonitor, network policies, and fleet support
- [Observability](observability/) — Grafana + Prometheus alerts ready to import

---

## Skills & Engineering Rigor (Portfolio Highlights)

**What this project demonstrates:**

- **Systems & Security Engineering** — Full threat model, prompt-injection defense, multi-layer read-only enforcement, OIDC+RBAC, hash-chained audit, distroless hardening.
- **Observability & Production Operations** — Metrics, dashboards, alerts, runbooks, air-gapped packaging, Helm productionization.
- **AI Agent Infrastructure** — Built a real, safe MCP server (stdio + HTTP) that LLMs can use without risk.
- **Enterprise Systems** — Deep IBM MQ knowledge across 10 topologies + version-aware diagnostics.
- **Software Craftsmanship** — 271+ tests (including security), strict mypy, ruff, CI-driven doc verification, SBOM + cosign signing.
- **End-to-End Delivery** — From idea to org-ready artifacts, including comprehensive documentation that platform teams can actually use.

Built iteratively using Grok Build as the primary coding partner while maintaining high engineering standards.

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

## Install — pick your path

| Scenario | Command | Time |
|---|---|---|
| **Solo / startup laptop (dev)** | `curl -fsSL https://raw.githubusercontent.com/pramodreddyboddu/mq-sentinel/main/scripts/install.sh \| MQS_DEV_MODE=true MQS_DEV_MODE_ACK_INSECURE=yes bash` | 5 min |
| **Solo / startup (prod)** | Same, with `MQS_AUTH_OIDC_*` env vars exported | 5 min |
| **Mid-org Kubernetes** | `helm install mq-sentinel oci://ghcr.io/pramodreddyboddu/charts/mq-sentinel --set oidc.issuer=… --set oidc.audience=… --set oidc.jwksUrl=…` | 30 min |
| **Local K8s POC (no live MQ)** | `cd examples/kind && ./install.sh` | 5 min |
| **RHEL / Rocky / OEL** | `sudo dnf install https://github.com/pramodreddyboddu/mq-sentinel/releases/latest/download/mq-sentinel-0.1.0-1.x86_64.rpm` | 5 min |
| **Debian / Ubuntu** | `sudo apt install ./mq-sentinel_0.1.0_amd64.deb` | 5 min |
| **Air-gapped (banks/gov)** | Mirror RPM internally, sign with org GPG, deploy via Satellite / Aptly | 1 evening |

Full guide: [docs/INSTALL.md](docs/INSTALL.md). For IBM MQ client libs: [docs/byom.md](docs/byom.md).

## Quick start (developer / contributor)

```bash
make install        # uv sync + editable install
make test           # pytest
make ci             # lint + type + tests + security suite (everything CI runs)
make docker         # build the production container image
make rpm deb        # build RPM + DEB packages (requires `gem install fpm`)
```

See:
- [DEVELOPMENT.md](DEVELOPMENT.md) — owner-level development guide
- [docs/usage-with-ai.md](docs/usage-with-ai.md) — best prompts and patterns when using with Claude / Cursor / Grok
- [docs/ORG-READINESS-PLAN.md](docs/ORG-READINESS-PLAN.md) — the full journey to org-ready

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

## Org-Readiness (7-Phase Plan Executed)

This project was deliberately taken through a complete org-readiness program (7 phases) so it is credible for real platform/SRE teams. See the full plan and status:

- [docs/ORG-READINESS-PLAN.md](docs/ORG-READINESS-PLAN.md)
- [docs/ORG-READINESS.md](docs/ORG-READINESS.md) — all 7 phases addressed (as of 2026-06-22)

Current state: Ready for platform team evaluation.

## Technical Roadmap

Phase 1 (MCP diagnostic tools) is complete. See [CHANGELOG.md](CHANGELOG.md) for future technical items:

- **0.4.0** — ServiceNow / Jira ticket auto-draft from RCS findings.
- **0.5.0** — SOC 2 evidence-pack generator.
- Historical telemetry, air-gapped improvements, etc.

Safe remediation is intentionally **out of scope**. MQ-Sentinel only reports.

## For Organizations

MQ-Sentinel is designed from the ground up for enterprise use:

- Read-only, prompt-injection resistant, OIDC + RBAC
- Verifiable IBM Knowledge Center citations
- Production deployment options (Kubernetes, RPM/DEB, air-gapped)
- Full audit trail

**Start here:**
- [Org Readiness Plan](docs/ORG-READINESS-PLAN.md)
- [Production Guide](docs/PRODUCTION.md)
- [Getting Started for Platform Teams](docs/getting-started-platform-teams.md)
- [OIDC Examples](docs/oidc-examples.md)
- [Security Posture](docs/SECURITY_POSTURE.md)

Helm chart includes production values, HPA, monitoring, and network policies.

## License

Proprietary — © 2026 MG. See [LICENSE](LICENSE). IBM® and IBM MQ® are trademarks of IBM Corporation; MG is not affiliated with IBM.
