# MQ-Sentinel — Threat Model (v0.1)

STRIDE analysis for the initial enterprise scaffold.

## Assets

1. **IBM MQ Queue Managers** (integrity, availability).
2. **MQ credentials & TLS keystores** (confidentiality).
3. **Audit log** (integrity, non-repudiation).
4. **Downstream LLM context** — the Claude/Cursor/agent session that consumes MCP output. A compromise here pivots to every other tool the agent can call.
5. **MCP host** (K8s pod / VM / laptop).

## Trust boundaries

```
[ Client LLM ] ⇄ [ MCP transport (stdio/HTTP) ] ⇄ [ MQ-Sentinel server ] ⇄ [ Queue Manager ]
                      ↑ untrusted                      ↑ trusted                  ↑ untrusted output
```

## STRIDE

| Category | Threat | Mitigation |
|---|---|---|
| **S**poofing | Unauthenticated caller issuing tool calls | OIDC JWT verification on every request; `disable_auth_for_local_dev` forbidden in `prod`. |
| **T**ampering | Attacker edits audit log to hide activity | Hash-chained JSONL; `verify-audit` detects any retroactive change. |
| **R**epudiation | User denies issuing a command | Audit record includes OIDC subject, tenant, tool, params hash, target QM, outcome. |
| **I**nformation disclosure | Credentials leaked via logs or errors | `MQCredential.__repr__` redacts; never printed; never in inventory; secrets mounted read-only with 0400. |
| **I**D | MQ message bodies exfiltrated | DLQ returns headers + reason codes only — never bodies. Bodies are hashed + length-reported. |
| **D**oS | Flooding the MCP exhausts a QM | Token-bucket rate limiter per principal; response size cap; MQSC row cap; query timeouts. |
| **E**oP | Destructive MQSC smuggled as payload | Three-layer allowlist (tool, connector, MQ-side `setmqaut`). Multi-statement, case-obfuscated, comment-hidden verbs all rejected by allowlist fuzz suite. |
| **E**oP | Prompt injection via queue/channel names or log lines steers the client LLM | Sanitizer strips control/zero-width/tag/ANSI, redacts jailbreak markers, drops non-IBM URLs, wraps output in quarantine envelope. |
| **E**oP | Path traversal in secrets backend | `FilesystemSecrets` rejects `..`, absolute paths, and any resolved path escaping the mount root. |
| **E**oP | SSRF from MCP to non-MQ endpoints | Runtime egress allowlist (Helm `networkPolicy.allowedEgressCIDRs`); no outbound HTTP in the server itself. |

## Attacker personas considered

- **Malicious queue name / log line** (attacker writes to MQ to seed content the MCP returns). — Sanitizer + quarantine envelope.
- **Compromised non-prod token** trying to reach prod QMs. — RBAC scope `nonprod-read` denies `read:prod`.
- **Insider abusing the MCP for destructive ops.** — Allowlist + MQ-side perms guarantee read-only even with full MCP admin.
- **Supply-chain attack via a dependency.** — `pip-audit`, Trivy, pinned hashes, SBOM, cosign signing on every release.

## Assumptions

- MQ service account granted only `+connect +inq +dsp`.
- TLS 1.3 enforced between client ⇄ MCP and MCP ⇄ QM.
- Deployment runs the distroless image with `readOnlyRootFilesystem: true`.

## Pending (future phases)

- Formal STRIDE refresh per phase.
- External pen test before GA.
- FIPS-140 build variant.
- Air-gapped KC doc bundle + offline verification.
