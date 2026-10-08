# MQ-Sentinel plugin for Claude Code

Read-only IBM MQ diagnostics inside Claude Code. The plugin bundles:

- **MCP server** `mq-sentinel` (run from PyPI with `uvx`, so no clone is needed)
- **Skill** `mq-triage`, which picks the right tool for a symptom and keeps citations attached

## Install

Requires [`uv`](https://docs.astral.sh/uv/) on `PATH`.

In Claude Code:

```
/plugin marketplace add pramodreddyboddu/mq-sentinel
/plugin install mq-sentinel@mq-sentinel
```

Restart Claude Code, then run `/mcp`. You should see `mq-sentinel` connected with 9 tools.

## Try it (demo mode, no IBM MQ needed)

Out of the box the server runs in `dev` mode against bundled fixtures with one queue manager, `DEMO_QM`:

```
Run full_mq_health_check on DEMO_QM and give me a prioritized summary.
```

```
APP.SVRCONN on DEMO_QM is RETRYING with 2035. What's wrong?
```

## Configuration

The plugin reads these from your shell environment when Claude Code starts:

| Variable | Default | Meaning |
|---|---|---|
| `MQS_SERVER_ENVIRONMENT` | `dev` | `dev` / `staging` / `prod`. Used by RBAC and audit. |
| `MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV` | `true` | Local-only auth bypass. Refused when environment is `prod`. |
| `MQS_SERVER_INVENTORY_DIR` | *(empty)* | Directory of `*.yaml` inventory files. Empty in dev means the built-in `DEMO_QM`. |

The audit log is written to `~/.mq-sentinel/audit.jsonl`.

Inventory file format (`$MQS_SERVER_INVENTORY_DIR/qms.yaml`):

```yaml
qms:
  - qm_name: PROD_QM1
    host: mq-prod1.internal
    port: 1414
    channel: SYSTEM.ADMIN.SVRCONN
    environment: prod        # dev | staging | prod | nonprod
    topology_hint: native_ha # optional
    secret_ref: prod/qm1     # resolved by the secrets backend; never the secret itself
```

For team or production use, run the HTTP transport with OIDC instead. See [docs/http-transport.md](../../docs/http-transport.md) and [docs/oidc-examples.md](../../docs/oidc-examples.md).
