# MQ-Sentinel plugin for Claude Code

Read-only IBM MQ diagnostics inside Claude Code. The plugin bundles:

- **MCP server** `mq-sentinel` (run from PyPI with `uvx`, so no clone is needed)
- **Skill** `mq-triage`, which picks the right tool for a symptom and keeps IBM citations attached
- **Commands** `/mq-health <QM>` (full check plus an incident note) and `/mq-status` (mode and available QMs)

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
/mq-health DEMO_QM
```

```
APP.SVRCONN on DEMO_QM is RETRYING with 2035. What's wrong?
```

## Connect real queue managers

1. Install the IBM MQ C client on this machine ([byom.md](../../docs/byom.md)).
2. On each QM, create a display-only user and channel ([onboard-new-qm.md](../../docs/onboard-new-qm.md)). It takes a few `setmqaut` grants and one CHLAUTH rule.
3. Write an inventory and a secrets directory, then export these before starting Claude Code:

```bash
export MQS_PACKAGE='mq-sentinel[mq]==0.4.0'        # adds pymqi (needs the MQ client)
export MQS_SERVER_INVENTORY_DIR=~/.mq-sentinel/inventory
export MQS_SERVER_SECRETS_DIR=~/.mq-sentinel/secrets
```

`~/.mq-sentinel/inventory/qms.yaml`:

```yaml
qms:
  - qm_name: PROD_QM1
    host: mq-prod1.internal
    port: 1414
    channel: MQS.SVRCONN
    environment: prod            # dev | staging | prod | nonprod
    secret_ref: prod/qm1         # -> ~/.mq-sentinel/secrets/prod/qm1/{username,password}
    cipher_spec: ANY_TLS13_OR_HIGHER
```

Run `/mq-status`. It should say **live** and list `PROD_QM1`.

Prod queue managers need the `prod-read` role. With the local-dev stub (stdio), only `dev`/`staging`/`nonprod` QMs are readable. Use the HTTP transport with OIDC for prod ([http-transport.md](../../docs/http-transport.md), [oidc-examples.md](../../docs/oidc-examples.md)).

## Configuration

All of these are read from your shell environment when Claude Code starts:

| Variable | Default | Meaning |
|---|---|---|
| `MQS_PACKAGE` | `mq-sentinel==0.4.0` | Package spec for `uvx`. Use `mq-sentinel[mq]==0.4.0` for live QMs. |
| `MQS_SERVER_CONNECTOR` | `auto` | `auto` (live if an inventory is set), `fixture`, or `pymqi`. |
| `MQS_SERVER_INVENTORY_DIR` | *(empty)* | Directory of `*.yaml` inventory files. |
| `MQS_SERVER_SECRETS_DIR` | *(empty)* | One subdirectory per `secret_ref`, holding `username` and `password`. Must not be world-readable. |
| `MQS_SERVER_ENVIRONMENT` | `dev` | `dev` / `staging` / `prod`. `prod` refuses demo fixtures and the local-dev auth bypass. |
| `MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV` | `true` | Local-only auth bypass for stdio. |

The audit log (hash-chained) is written to `~/.mq-sentinel/audit.jsonl`.

## What it will never do

Every tool sends only allowlisted `DISPLAY` commands. DLQ messages are browsed for headers only, and bodies are never read. Fixes come back as MQSC text for you to review and run.
