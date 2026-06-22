# MQ-Sentinel — Owner Vision & Principles

**Status:** Living document. Updated as the project evolves.

## Mission

Give AI agents (Claude, Cursor, Grok, etc.) safe, reliable, *verifiable* access to IBM MQ diagnostics in enterprise environments — without ever risking destructive actions or hallucinations.

MQ-Sentinel exists because handing raw MQ access to an LLM is unacceptable in banks, insurers, governments, and large enterprises. We solve the "how do I let an AI help me without getting fired?" problem.

## Core Product Principles (non-negotiable)

1. **Read-only by construction**
   - Three layers: tool allowlist, connector enforcement, MQ service account permissions.
   - We will never add a write/remediation tool.

2. **No LLM in the critical path**
   - The server never calls an LLM. All reasoning is deterministic pattern matching + curated knowledge.
   - This eliminates an entire class of prompt-injection and model-poisoning attacks.

3. **Verifiable citations**
   - Every diagnosis includes direct IBM Knowledge Center links.
   - CI fetches and validates those links daily. A dead citation fails the build.

4. **Defense in depth for untrusted data**
   - Prompt-injection firewall + strict output sanitizer on every byte that came from MQ.
   - URL allowlist (only www.ibm.com).
   - Hash-chained tamper-evident audit log.

5. **Production first, not demo first**
   - OIDC + RBAC with environment scoping.
   - Distroless, non-root, signed images, SBOM.
   - Helm with HPA, ServiceMonitor, NetworkPolicy.
   - Air-gapped packaging (RPM/DEB).

6. **Transparency over magic**
   - Full threat model.
   - Security posture one-pager.
   - SOC2 evidence checklist.
   - Every guarantee is backed by tests (including security-negative tests that gate CI).

## What Success Looks Like

- A platform/SRE team at a mid-to-large company can evaluate, deploy, and run MQ-Sentinel in production in under 4 hours following the docs.
- A security/compliance reviewer can answer 80%+ of standard questionnaires using artifacts in this repo.
- An MQ admin using Claude Desktop or Cursor says: "I finally have an AI that actually understands my 2035s and doesn't lie to me."
- The project is respected in both the MCP community and the IBM MQ community.

## How This Project Was Built

This project was developed with **Grok Build** (xAI) as the primary coding partner while maintaining strict engineering standards. The collaboration was used to accelerate architecture, implementation, documentation, deployment artifacts, and polish — while the human owner retained full design authority and review.

We executed a complete 7-phase org-readiness plan (see `docs/ORG-READINESS-PLAN.md`) because we wanted this to be credible for real organizations, not just a demo.

## Technical Philosophy

- Small trusted computing base.
- Strong static analysis (mypy strict, ruff).
- High test coverage with special emphasis on security and correctness invariants.
- Configuration over cleverness.
- Explicit is better than implicit (especially around security boundaries).

## Roadmap Direction (Owner View)

Short term (keep shipping trust + DX):
- Better self-diagnostics (`doctor` command, clearer error messages)
- Improved inventory for larger fleets
- More matcher coverage and edge cases from real production reports
- Smoother one-command local experience

Medium term:
- Knowledge pack versioning / signed updates
- Better integration stories (ServiceNow/Jira draft from findings)
- Optional lightweight web UI for non-AI users (read-only)

Longer term / strategic:
- Consider open-core or more permissive licensing path while protecting the core safety model.
- Become the reference implementation for "safe MCP servers for legacy enterprise systems".

## License & Ownership Intent

Currently released under a proprietary license owned by the project author. The intent is to keep the safety model and core extremely controlled while making the project useful and transparent.

We are open to thoughtful feedback and contributions under clear contribution terms.

## Owner Notes

- If something feels "good enough for a side project" — it is not good enough.
- Every change must be justifiable to a paranoid security reviewer and a tired on-call SRE.
- The reputation of this project is more important than any single feature.

---

Maintained with pride. Built to be trusted.
