# SOC 2 Evidence Checklist for MQ-Sentinel

This is a starter template organizations can use when including MQ-Sentinel in their SOC 2 / compliance program.

## Control Area: Security (Common Criteria)

### CC6.1 - Logical Access
- Evidence: OIDC + RBAC implementation (`auth/oidc.py`, `auth/rbac.py`)
- Evidence: Principals scoped by environment tier (prod / nonprod)
- Evidence: No shared credentials; all access via short-lived tokens

### CC6.2 - Authentication
- Evidence: JWT validation on every request (HTTP transport)
- Evidence: Support for modern IdPs (Okta, Entra ID, Keycloak documented)
- Evidence: Dev mode explicitly disabled in production

### CC6.3 - Authorization
- Evidence: Tool-level allowlist + MQ-side permissions
- Evidence: Read-only by design (no destructive MQSC accepted)

### CC6.6 - Encryption
- Evidence: TLS recommended for HTTP transport
- Evidence: Secrets never logged (redacted in `MQCredential`)
- Evidence: Distroless image + non-root user

### CC6.7 - Vulnerability Management
- Evidence: `pip-audit` + Trivy in CI
- Evidence: SBOM generated on every release (CycloneDX)
- Evidence: Dependabot / Renovate recommended

### CC6.8 - Change Management
- Evidence: All changes go through PR + CI (tests, security suite, link verification)
- Evidence: Signed container images (cosign)

## Control Area: Availability

- Health and readiness endpoints (`/healthz`, `/readyz`)
- Prometheus metrics and alerts for monitoring
- Rate limiting to prevent DoS
- Audit logging for incident investigation

## Control Area: Confidentiality

- Prompt injection firewall (sanitizer + quarantine envelope)
- DLQ analysis returns headers only (never message bodies)
- All MQ output sanitized before returning to LLM

## Control Area: Processing Integrity

- Every diagnostic result includes verified IBM Knowledge Center citations
- CI job (`verify-kc-links.yml`) ensures no dead links
- Pattern matching against curated, version-aware registry (no LLM invention of fixes)

## Evidence Artifacts Provided by MQ-Sentinel

- Threat model (`docs/threat-model.md`)
- Security posture summary (`docs/SECURITY_POSTURE.md`)
- Audit log format and verification tool
- SBOM + signed images
- OpenTelemetry + Prometheus metrics
- Hash-chained tamper-evident audit
- Full test suite (unit + integration + security)

## Recommended Additional Controls (Org Side)

- Run MQ-Sentinel in a dedicated namespace with strict NetworkPolicy
- Ship audit logs to your SIEM with retention and alerting
- Include MQ-Sentinel in your change management and access review processes
- Periodically run `mq-sentinel verify-audit` as part of compliance evidence collection

---

This checklist is a starting point. Adapt it to your specific trust services criteria and control framework. MQ-Sentinel is designed to make many of these controls easier to satisfy.