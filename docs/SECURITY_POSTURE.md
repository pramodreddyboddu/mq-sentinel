# MQ-Sentinel Security Posture for Organizations

**Version:** 0.3.0  
**Date:** 2026-06-22

This document is intended for security, compliance, and platform teams evaluating MQ-Sentinel for production use.

## Design Principles

- **Read-only by default and by architecture.** No tool can execute destructive MQSC commands.
- **Defense in depth.** Allowlisting at tool + connector + MQ `setmqaut` level.
- **Prompt injection resistant.** All MQ output is sanitized before reaching the LLM.
- **Audit everything.** Tamper-evident, hash-chained logs.
- **Least privilege identity.** OIDC + RBAC with environment scoping (prod vs nonprod).

## Key Security Controls

| Control | Implementation | Verification |
|---------|----------------|--------------|
| Command Allowlist | Static list of safe DISPLAY / PING verbs | `tests/security/` + fuzzing |
| Output Sanitizer | Strips control chars, zero-width, ANSI, jailbreak markers | `security/sanitizer.py` + tests |
| Prompt Quarantine | MQ data wrapped so LLM treats it as untrusted | Code + docs |
| OIDC Authentication | JWT verification on every request (HTTP) | `auth/oidc.py` |
| RBAC | Principals scoped by tier (nonprod-read, prod-read, admin-audit) | `auth/rbac.py` |
| Audit Logging | Hash-chained JSONL with subject, tool, params hash, target QM | `audit/logger.py` + `verify-audit` CLI |
| URL Verification | Only `www.ibm.com` allowed; daily CI link checker | `scripts/verify_kc_links.py` |
| Container Hardening | Distroless, non-root, read-only FS, dropped caps, seccomp | Dockerfile + Helm securityContext |
| Supply Chain | SBOM (CycloneDX), cosign signatures, pip-audit + Trivy in CI | `.github/workflows`, packaging/ |
| Rate Limiting | Token bucket per principal | `security/ratelimit.py` |
| No Data Exfil | DLQ analysis returns headers + hashes only (never message bodies) | `tools/dlq.py` + tests |

## Threat Model

See full [docs/threat-model.md](threat-model.md) (STRIDE analysis).

Major risks mitigated:
- Prompt injection from attacker-controlled MQ data
- Credential leakage
- Unauthorized prod access from nonprod tokens
- Tampering with audit history
- Destructive commands smuggled through MCP

## Compliance Alignment

- **Read-only + audit trail** supports many control objectives.
- **SOC 2** evidence pack generator is on the roadmap (0.5.0).
- **Air-gapped** support via RPM/DEB + mirrored images + offline KC bundle (planned).
- SBOM and signed images help with supply chain controls (SSDF, SLSA).

**Note:** MQ-Sentinel does not execute remediation. Organizations must still follow their change management processes for any actions suggested by the tool.

## Recommendations for Enterprise Adoption

1. Run in a dedicated namespace/project with strict NetworkPolicy.
2. Use external secrets management (not plain Kubernetes Secrets for prod).
3. Enable audit log shipping and integrity monitoring.
4. Require OIDC from your corporate IdP (disable local dev auth).
5. Review and customize the allowlist + sanitizer if you have custom MQSC needs.
6. Include the tool in your threat modeling and incident response playbooks.

## Reporting Security Issues

See [SECURITY.md](../SECURITY.md) for responsible disclosure.

---

This posture is the result of deliberate design choices made before the first line of diagnostic logic. We treat the LLM as an untrusted consumer of data.