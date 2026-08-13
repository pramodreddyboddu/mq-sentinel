# Running MQ-Sentinel in Production (Org / Enterprise Guidance)

This document is the single source of truth for platform/SRE teams who want to run MQ-Sentinel reliably at scale inside an organization.

## Core Principles (Non-Negotiable)

- **Read-only only.** We never execute destructive MQSC. All remediation suggestions are text only.
- **Least privilege.** Every principal gets the smallest possible scope (`nonprod-read`, `prod-read`).
- **Verifiable citations.** Every IBM link is checked daily in CI.
- **Audit everything.** Tamper-evident log that you can ship to your SIEM.

## Recommended Architecture for Mid-to-Large Orgs

```
[Claude / Cursor / Grok (in IDE or web)] 
          ↓ (MCP over HTTP + OIDC)
[MCP Gateway / Central MQ-Sentinel (K8s)]
          ↓ (OIDC + RBAC)
[Per-environment inventory + secrets]
          ↓
[IBM MQ Queue Managers]  (prod, nonprod, z/OS, RDQM, Native HA, etc.)
```

- Run one or more central instances (replicas ≥ 2) behind internal load balancer or service mesh.
- Use Kubernetes secrets or external secrets operator for OIDC config.
- Inventory can start as a ConfigMap / mounted YAML and evolve to a small registry service if you have hundreds of QMs.
- Ship audit logs to your existing log aggregation (Splunk, ELK, etc.).

## OIDC / Identity Provider Setup (Copy-Paste Starting Points)

### Keycloak (example)
```yaml
oidc:
  issuer: https://keycloak.example.com/realms/mq-platform
  audience: mq-sentinel
  jwksUrl: https://keycloak.example.com/realms/mq-platform/protocol/openid-connect/certs
```

Create a client with:
- Client authentication = confidential or public (depending on your gateway)
- Valid redirect URIs not needed for MCP bearer flow
- Audience mapper for "mq-sentinel"
- Groups or roles for `nonprod-read`, `prod-read`, `admin-audit`

### Okta / Entra ID (Azure AD)
Similar structure. Map groups to RBAC roles via the OIDC verifier claims.

See `docs/http-transport.md` for full environment variables.

**Important:** In production, never set `MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV=true`.

## Queue Manager Inventory

Start simple:

```yaml
# /etc/mq-sentinel/inventory.yaml
qms:
  - name: PROD_QM1
    host: mq-prod-1.internal
    port: 1414
    channel: SYSTEM.ADMIN.SVRCONN
    ssl: true
    tier: prod
  - name: NONPROD_QM1
    host: mq-np-1.internal
    port: 1414
    channel: SYSTEM.ADMIN.SVRCONN
    tier: nonprod
```

The server refuses to let a `nonprod-read` token touch a `prod` QM.

For large fleets, replace the in-memory registry with a small internal service or database-backed implementation (future extension point).

## Networking & Security

Helm values already include:
- `readOnlyRootFilesystem: true`
- `runAsNonRoot: true`
- `networkPolicy.enabled: true`
- `allowedEgressCIDRs` — restrict to only your QM subnets

Add a NetworkPolicy that only allows egress to MQ listener ports.

For HTTP transport, terminate TLS at ingress or service mesh (the container itself speaks plain HTTP internally in most setups).

## Observability

- `/healthz` and `/readyz`
- Prometheus metrics on `/metrics`
- Structured logs (structlog) — send to your logging platform
- OpenTelemetry traces if you have a collector

Recommended alerts:
- Error rate on diagnostic tools > X%
- Audit log write failures
- OIDC verification failures (possible token replay or misconfig)

## Secrets & Credentials

Preferred:
- Kubernetes secrets + external-secrets-operator
- Or HashiCorp Vault with the filesystem secrets backend mounted at a well-known path

Never put real MQ credentials in the inventory file.

## Air-Gapped / Regulated Environments

- Use the RPM or DEB packages (or build your own from source).
- Mirror the container image internally and sign with your org keys.
- Use the air-gapped KC bundle mode (see roadmap / future releases).
- Disable any outbound calls (the server makes none by default except for OIDC JWKS at startup).

## Operational Runbook (Minimum)

1. On-call gets paged for MQ issue.
2. Agent (Claude/Grok/...) connected to MQ-Sentinel via approved transport.
3. Run `full_mq_health_check` or specific tool (e.g. `diagnose_failed_channels`).
4. Review the Root Cause Summary + IBM KC links.
5. Execute suggested read-only commands manually if needed.
6. All activity is in the tamper-evident audit log.

Never let the MCP perform actual remediation.

## Common Gotchas

- Forgetting to set OIDC values in prod → server refuses to start (good).
- Wrong tier labels in inventory → RBAC blocks legitimate access.
- Missing IBM MQ client libs on the host → use the "bring your own" path or the container that bundles them if approved.
- Rate limiting kicking in during incident war rooms → tune `rate_limit_per_minute` per principal or add burst.

## Upgrade Strategy

- Follow semantic versioning.
- Read CHANGELOG before upgrading.
- Test in nonprod first using the fixture mode or a mirror QM.
- Audit log is append-only; old logs remain valid.

## SLOs and Alerting Recommendations

Define service level objectives for your deployment:

- Availability: 99.9% uptime for the MCP service (measured via /readyz)
- Latency: p95 diagnostic tool response < 5 seconds for standard checks
- Accuracy: 100% of citations must resolve to valid IBM KC pages (enforced by CI)
- Audit integrity: 0 undetected tampering (verified by `verify-audit` job)

Example Prometheus alerts (see observability/prometheus-alerts.yaml):

- High error rate
- Service down
- High latency
- Audit write failures

## Enterprise Checklist (Before Going Live)

- [ ] All OIDC values set and verified in prod (server refuses to start otherwise)
- [ ] NetworkPolicy restricts egress to MQ listener subnets only
- [ ] Audit logs shipped to central SIEM with integrity checks
- [ ] Inventory file reviewed for correct `tier: prod|nonprod` labels
- [ ] Secrets mounted read-only (0400) and not in Git
- [ ] Prometheus metrics + alerts configured (see observability/)
- [ ] Grafana dashboard imported and team has access
- [ ] Runbooks updated with MQ-Sentinel usage
- [ ] On-call team trained on "read-only only" policy
- [ ] SBOM and image provenance verified in your artifact repo
- [ ] Regular `mq-sentinel verify-audit` or equivalent automated check
- [ ] SLOs defined and monitored
- [ ] Capacity tested for expected query volume (use `make load-test` or similar)

## Support & Feedback for Internal Platform Teams

(Internal teams: replace with your support channel / Slack / ticket queue)

For the open source / early version, use GitHub issues.

---

This document should live next to your runbooks. Update it as you gain real production experience with MQ-Sentinel.