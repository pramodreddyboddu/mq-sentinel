# RBAC Best Practices for Organizations

MQ-Sentinel uses a simple but effective RBAC model based on OIDC claims.

## Core Roles

- `nonprod-read`: Can query only QMs tagged with `tier: nonprod`
- `prod-read`: Can query QMs tagged with `tier: prod` (and nonprod)
- `admin-audit`: Can read audit logs (future extension)

## Recommended IdP Setup

### Group Naming
Use consistent naming:
- `mq-nonprod-read`
- `mq-prod-read`
- `mq-audit`

Map these groups into the token claims that MQ-Sentinel reads (default: `groups` or `roles` claim).

### Principle of Least Privilege
- Most human users → `nonprod-read`
- On-call / SREs → `prod-read`
- Auditors / Compliance → `admin-audit` (read-only)

Never give broad access. Use separate service accounts for different environments.

## Service Accounts (Machine Clients)

For CI/CD, monitoring bots, or long-running agents:
- Create dedicated clients with Client Credentials grant.
- Assign the minimal role needed.
- Rotate secrets regularly.
- Scope to specific QMs if possible (via custom claims or inventory filtering).

## Multi-Tenant / Large Org Patterns

For organizations with many teams or business units:
- Tag QMs with additional metadata (business_unit, environment, region).
- Extend the RBAC logic (see `src/mq_sentinel/auth/rbac.py`) to enforce finer-grained rules.
- Consider running separate MQ-Sentinel instances per major tenant with different OIDC audiences.

## Audit Everything

All tool calls are logged with:
- OIDC subject
- Timestamp
- Tool name + parameters (hashed)
- Target QM
- Outcome

Regularly review or forward these logs to your SIEM.

## Common Pitfalls to Avoid

- Using the same OIDC client for dev and prod.
- Giving everyone `prod-read`.
- Forgetting to update inventory when adding new QMs (RBAC is enforced client-side via inventory labels).

## Verification

Use the built-in tools:
- `mq-sentinel doctor` (CLI)
- Call the `full_mq_health_check` tool with different tokens to validate scoping.

For production, run periodic access reviews on the IdP groups mapped to MQ-Sentinel roles.