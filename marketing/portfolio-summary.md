## Portfolio Summary (for LinkedIn "About", GitHub profile, or bio)

**MQ-Sentinel** — Production-grade, read-only IBM MQ diagnostic MCP server.

I built MQ-Sentinel to solve a real enterprise problem: how do you let AI agents (Claude, Cursor, Grok) safely diagnose IBM MQ issues without hallucinations or any risk of destructive actions?

### Highlights:
- 8 diagnostic tools covering all 10 IBM MQ topologies (z/OS QSG, Native HA, RDQM, clusters, etc.)
- Read-only by design + prompt-injection firewall + output sanitizer (3 layers of enforcement)
- Verified IBM Knowledge Center citations (CI-enforced daily link checks)
- OIDC + RBAC, hash-chained audit, distroless containers, SBOM + signed images
- Production Helm (HPA, ServiceMonitor, NetworkPolicy), air-gapped RPM/DEB, full observability
- Executed a full 7-phase org-readiness plan (threat model, SOC2 checklist, platform runbooks, RBAC guides)

271+ tests, strict typing, security-negative tests that gate CI. Built as a public portfolio project using Grok Build as the primary coding partner while maintaining real engineering standards.

Designed to be credible for platform/SRE teams in regulated environments.

**Repo + live demo + complete story:** https://github.com/pramodreddyboddu/mq-sentinel

---

Use this as your LinkedIn "About" project blurb, GitHub repo description, or pinned project summary.