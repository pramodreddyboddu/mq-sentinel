# Setting up MQ-Sentinel

MQ-Sentinel is a free, read-only MCP server published on PyPI as [`mq-sentinel`](https://pypi.org/project/mq-sentinel/). Source and full docs: <https://github.com/pramodreddyboddu/mq-sentinel>.

The user adds it to their agent. The agent should show these steps, not perform them.

## 1. Pick a mode

| Mode | Who | Needs |
|---|---|---|
| **Demo** | Anyone trying it out | [`uv`](https://docs.astral.sh/uv/) only. Bundled fixtures, one QM: `DEMO_QM`. No IBM MQ. |
| **Local live** | One engineer, their own non-prod QMs | `uv`, the IBM MQ C client, an inventory file, a secrets directory |
| **Central (org)** | A team | One MQ-Sentinel server run by the platform team. Engineers only need its URL and an SSO login. |

## 2. Add the server to your agent

Copy the matching file from `templates/`:

| Agent | Template | Where it goes |
|---|---|---|
| Claude Code | `templates/claude-code.mcp.json` | `.mcp.json` in your project, or run `claude mcp add` (below) |
| Claude Desktop | `templates/claude-desktop.json` | merge into `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/`, Windows: `%APPDATA%\Claude\`) |
| Cursor | `templates/cursor.mcp.json` | `.cursor/mcp.json` |
| VS Code (Copilot) | `templates/vscode.mcp.json` | `.vscode/mcp.json` |
| Any agent, central org server | `templates/remote-org.mcp.json` | your agent's remote / HTTP MCP server setting |

In the Claude Desktop and Cursor templates, replace `/ABSOLUTE/PATH/TO/HOME` with your home directory. Those clients may start servers from `/`, where the default audit log location isn't writable.

Claude Code in one command (demo mode):

```bash
claude mcp add mq-sentinel \
  -e MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV=true -e MQS_SERVER_ENVIRONMENT=dev \
  -- uvx mq-sentinel=={{VERSION}} serve
```

Restart the agent, then ask: *"Run full_mq_health_check on DEMO_QM."*

## 3. Connect real queue managers (local live mode)

1. **Install the IBM MQ C client** (the free IBM MQ redistributable client), then use the `mq` extra: change `mq-sentinel=={{VERSION}}` to `mq-sentinel[mq]=={{VERSION}}` in the template.
2. **Create a display-only MQ identity on each QM.** Use a dedicated user, not in `mqm`, with only display authority. Summary (adapt the names):

   ```bash
   setmqaut -m QM1 -t qmgr -g mqsread +connect +inq +dsp
   setmqaut -m QM1 -n SYSTEM.ADMIN.COMMAND.QUEUE -t queue -g mqsread +put +dsp
   setmqaut -m QM1 -n SYSTEM.DEFAULT.MODEL.QUEUE -t queue -g mqsread +get +dsp
   setmqaut -m QM1 -n '**' -t queue -g mqsread +dsp
   setmqaut -m QM1 -n '**' -t channel -g mqsread +dsp
   setmqaut -m QM1 -n SYSTEM.DEAD.LETTER.QUEUE -t queue -g mqsread +browse +inq +dsp
   ```

   Then add a dedicated TLS `SVRCONN` channel with a CHLAUTH rule that admits only the MQ-Sentinel host. The full runbook is `docs/onboard-new-qm.md` in the repository.
3. **Write an inventory.** Copy `templates/inventory.yaml` into a directory (for example `~/.mq-sentinel/inventory/`) and set `MQS_SERVER_INVENTORY_DIR` to that directory.
4. **Store credentials outside the agent.** Under `MQS_SERVER_SECRETS_DIR`, create one directory per `secret_ref` containing two files, `username` and `password`. Make them readable only by you (`chmod 700` on the directory, `chmod 600` on the files). MQ-Sentinel refuses world-readable secrets. Never put credentials in the inventory, the agent config, or the chat.
5. Restart the agent and call `health`. It should say `"connector": "live"` and list your queue managers.

Local live mode reads only `dev`, `staging` and `nonprod` queue managers. Prod queue managers need the central mode, with SSO roles.

## 4. Central server for a team

The platform team runs MQ-Sentinel once (Helm chart, container image or RPM/DEB) with the HTTP transport, OIDC single sign-on, the inventory and the credentials. Each engineer then:

1. Gets the server URL, for example `https://mq-sentinel.internal.example.com/mcp`.
2. Adds it as a remote MCP server (`templates/remote-org.mcp.json`, or `claude mcp add --transport http mq-sentinel <url>` in Claude Code).
3. Signs in through the company SSO when the agent asks.

Access to prod queue managers follows the engineer's SSO groups (`prod-read` / `nonprod-read`), and every call is audited under their identity. The platform guide is `docs/http-transport.md` in the repository.

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `MQS_SERVER_ENVIRONMENT` | `dev` | `dev` / `staging` / `prod` |
| `MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV` | `false` | `true` for single-user local use. Refused in `prod`. |
| `MQS_SERVER_INVENTORY_DIR` | unset | Directory of inventory `*.yaml`. Setting it switches to live connections. |
| `MQS_SERVER_SECRETS_DIR` | unset | Credentials root, one directory per `secret_ref` |
| `MQS_AUDIT_LOG_PATH` | `./audit.jsonl` | Hash-chained audit log of every call |
