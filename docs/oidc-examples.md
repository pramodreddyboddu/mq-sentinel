# OIDC Configuration Examples for Enterprise IdPs

This guide provides copy-paste starting points for common enterprise identity providers.

**Important notes:**
- MQ-Sentinel expects JWT bearer tokens with standard OIDC claims.
- The `MQS_AUTH_OIDC_*` environment variables (or Helm values) are required in production.
- RBAC is driven by claims (groups/roles). Map your IdP groups to: `nonprod-read`, `prod-read`, `admin-audit`.
- Always set `MQS_SERVER_ENVIRONMENT=prod` in production.

## General Requirements

Your IdP client/app registration should:
- Support OAuth2 / OIDC (Authorization Code or Client Credentials for service accounts).
- Expose JWKS endpoint.
- Issue tokens with `aud` matching your `MQS_AUTH_OIDC_AUDIENCE`.
- Include groups/roles claim for RBAC.

See `docs/http-transport.md` for all supported environment variables.

---

## Okta (OIDC)

### App Integration Settings (Admin Console)
- Application type: Web or Native (for service accounts use "API Services" / Client Credentials)
- Sign-in redirect: not strictly needed for pure bearer MCP use
- Grant types: Authorization Code + Refresh Token (or Client Credentials)
- Controlled access: Assign to groups
- Claims: Ensure `groups` claim is included in ID and Access tokens.

### Helm / Env Vars
```yaml
oidc:
  issuer: https://your-org.okta.com/oauth2/default
  audience: mq-sentinel
  jwksUrl: https://your-org.okta.com/oauth2/default/v1/keys
```

Environment:
```bash
export MQS_AUTH_OIDC_ISSUER=https://your-org.okta.com/oauth2/default
export MQS_AUTH_OIDC_AUDIENCE=mq-sentinel
export MQS_AUTH_OIDC_JWKS_URL=https://your-org.okta.com/oauth2/default/v1/keys
```

### RBAC Group Mapping Example
Create Okta groups:
- `mq-nonprod-readers`
- `mq-prod-readers`
- `mq-auditors`

Map these in your token claims or use Okta's claims mapping.

---

## Microsoft Entra ID (Azure AD)

### App Registration
1. Register a new app (or use existing).
2. Expose an API or use "App roles".
3. Add redirect URIs if using interactive flow (often not needed).
4. Create App Roles: `nonprod-read`, `prod-read`, `admin-audit`.
5. Assign users/groups to these roles.

### Helm / Env Vars
```yaml
oidc:
  issuer: https://login.microsoftonline.com/<tenant-id>/v2.0
  audience: <your-application-client-id>
  jwksUrl: https://login.microsoftonline.com/<tenant-id>/discovery/v2.0/keys
```

Environment:
```bash
export MQS_AUTH_OIDC_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0
export MQS_AUTH_OIDC_AUDIENCE=<your-application-client-id>
export MQS_AUTH_OIDC_JWKS_URL=https://login.microsoftonline.com/<tenant-id>/discovery/v2.0/keys
```

### RBAC
Use App Roles or Security Groups. The OIDC verifier in code can be extended to read `roles` or `groups` claim.

---

## Keycloak

### Client Configuration
- Client ID: `mq-sentinel`
- Client Protocol: openid-connect
- Access Type: confidential or public
- Valid Redirect URIs: (can be empty for bearer-only)
- Mappers:
  - Add "Group Membership" mapper (token and ID token)
  - Or use "User Attribute" / "Hardcoded role" for fine-grained control.

### Helm / Env Vars
```yaml
oidc:
  issuer: https://keycloak.your-org.com/realms/mq-platform
  audience: mq-sentinel
  jwksUrl: https://keycloak.your-org.com/realms/mq-platform/protocol/openid-connect/certs
```

Environment variables same pattern.

### Groups for RBAC
Create realm groups `nonprod-read`, `prod-read`, `admin-audit` and assign users.

---

## Generic / Other IdPs (PingFederate, Auth0, etc.)

Use the standard OIDC fields:
- `issuer`
- `audience`
- `jwksUrl` (or `jwks_uri` in discovery)

For custom claims, you may need to extend `src/mq_sentinel/auth/oidc.py` to map your groups/roles claim name.

---

## Service Account / Machine Clients (for agents)

For CI/CD or long-running agent services, prefer Client Credentials grant:
- Create a confidential client.
- Exchange client_id + secret for token.
- Pass the token in `Authorization: Bearer <token>` to the HTTP MCP endpoint.

---

## Troubleshooting Common Org Issues

- **Token audience mismatch**: Ensure `aud` claim exactly matches `MQS_AUTH_OIDC_AUDIENCE`.
- **Clock skew**: Use NTP on both sides; OIDC libraries tolerate small skew.
- **JWKS caching**: The verifier caches keys; restart or implement cache invalidation if rotating keys.
- **RBAC not working**: Log the Principal claims. Check your IdP group/role claim name against `rbac.py`.
- **Prod refuses to start**: You must set all three OIDC values when `MQS_SERVER_ENVIRONMENT=prod`.

For more, run `mq-sentinel doctor` or check logs at startup.

---

See also:
- `docs/http-transport.md`
- `docs/PRODUCTION.md`
- `src/mq_sentinel/auth/oidc.py` for verifier implementation.