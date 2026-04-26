# Security Policy

MQ-Sentinel is built as a read-only, enterprise-grade diagnostic agent. Security is a **primary** design pillar, not a feature.

## Reporting a vulnerability

Please report suspected vulnerabilities privately to the maintainers. Do **not** open a public issue. Include:

- A clear description and impact assessment.
- Reproduction steps or PoC.
- The affected commit / version.

You will receive an acknowledgement within 72 hours and a remediation plan within 10 business days for High/Critical issues.

## Security guarantees enforced in code

1. **Read-only execution.** A static MQSC allowlist in `src/mq_sentinel/security/allowlist.py` permits only `DISPLAY` / `DIS` / `PING CHANNEL`. Destructive verbs (`ALTER`, `DELETE`, `START`, `STOP`, `REFRESH`, `RESET`, `CLEAR`, `SET`, `DEFINE`, `RECOVER`, `BACKUP`, `SUSPEND`, `RESUME`, `MOVE`, `END`, `ARCHIVE`, `RECORD`, `REVERIFY`, `CHANGE`) are rejected.
2. **No shell injection.** Shell commands are invoked as `argv` lists (never `shell=True`) and matched against a binary-specific argument regex.
3. **Prompt-injection firewall.** All MQ-sourced output is sanitized (`src/mq_sentinel/security/sanitizer.py`) before leaving the server: control/zero-width/tag chars stripped, jailbreak markers redacted, URLs constrained to `www.ibm.com`.
4. **Tamper-evident audit.** Every tool call produces a hash-chained record in `audit.jsonl`. `mq-sentinel verify-audit` detects any retroactive edit.
5. **Credentials never logged.** `MQCredential.__repr__` / `__str__` redact passwords. Secrets are loaded from a pluggable backend (filesystem/K8s by default; Vault / AWS Secrets Manager / CyberArk adapters planned).
6. **Defense in depth at the MQ layer.** Operators must grant the MQ-Sentinel service account only `+connect +inq +dsp` — never admin.

## Threat model

See [docs/threat-model.md](docs/threat-model.md) for the STRIDE analysis.

## Security tests

`tests/security/` contains a non-negotiable corpus. CI fails if any security test fails:

```bash
uv run pytest -q -m security
```

## Out of scope (by design)

- Safe remediation / auto-fix (not in v1).
- Executing anything other than `DISPLAY` / `DIS` / `PING CHANNEL` / the shell allowlist.
- Calling any LLM from the server. The MCP returns typed data + KC citations; the client LLM narrates.
