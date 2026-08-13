# Connect MQ-Sentinel to any MCP client

MQ-Sentinel is one server. Any client that speaks [Model Context Protocol](https://modelcontextprotocol.io) can use it. You do **not** build a separate plugin per vendor.

| Client | Transport | How people add it |
|---|---|---|
| **Grok Build** | stdio or HTTP | `grok mcp add` or `~/.grok/config.toml` |
| **Claude Desktop** | stdio or HTTP | `claude_desktop_config.json` |
| **Claude Code** | stdio or HTTP | `claude mcp add` or `.mcp.json` |
| **Cursor** | stdio or HTTP | `.cursor/mcp.json` |
| **Gemini CLI** | stdio or HTTP | Gemini MCP settings |
| **ChatGPT** | **remote HTTPS only** | Settings → Apps → Developer Mode → custom connector |
| **VS Code Copilot** | stdio or HTTP | `.vscode/mcp.json` |

Demo mode (no live IBM MQ) uses the bundled fixture sandbox.

```bash
export MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV=true
export MQS_SERVER_ENVIRONMENT=dev
```

---

## Grok Build

From PyPI (no clone):

```bash
grok mcp add mq-sentinel \
  -e MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV=true \
  -e MQS_SERVER_ENVIRONMENT=dev \
  -- uvx mq-sentinel serve
```

From this repo (uv already installed):

```bash
grok mcp add mq-sentinel \
  -e MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV=true \
  -e MQS_SERVER_ENVIRONMENT=dev \
  -- uv run mq-sentinel serve
```

Or Docker:

```bash
grok mcp add mq-sentinel \
  -e MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV=true \
  -e MQS_SERVER_ENVIRONMENT=dev \
  -- docker run -i --rm --read-only --cap-drop ALL \
       --security-opt no-new-privileges:true \
       -e MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV \
       -e MQS_SERVER_ENVIRONMENT \
       ghcr.io/pramodreddyboddu/mq-sentinel:0.3.0 \
       serve --transport stdio
```

This repo also ships a project-scoped config at `.grok/config.toml`. Launch Grok from this directory and the server is already listed.

Check it:

```bash
grok mcp list
grok mcp doctor mq-sentinel
```

---

## Claude Desktop

Edit the config file:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mq-sentinel": {
      "command": "uv",
      "args": ["run", "--directory", "/ABS/PATH/TO/mq-sentinel", "mq-sentinel", "serve"],
      "env": {
        "MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV": "true",
        "MQS_SERVER_ENVIRONMENT": "dev"
      }
    }
  }
}
```

Docker alternative — set `command` to `docker` and `args` to the same `run -i --rm … serve --transport stdio` list as above.

Restart Claude Desktop after saving.

---

## Claude Code

```bash
claude mcp add mq-sentinel -- uv run --directory /ABS/PATH/TO/mq-sentinel mq-sentinel serve
```

Or commit a project `.mcp.json`:

```json
{
  "mcpServers": {
    "mq-sentinel": {
      "command": "uv",
      "args": ["run", "mq-sentinel", "serve"],
      "env": {
        "MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV": "true",
        "MQS_SERVER_ENVIRONMENT": "dev"
      }
    }
  }
}
```

---

## Cursor

Create `.cursor/mcp.json` in the project (or use Cursor Settings → MCP):

```json
{
  "mcpServers": {
    "mq-sentinel": {
      "command": "uv",
      "args": ["run", "mq-sentinel", "serve"],
      "env": {
        "MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV": "true",
        "MQS_SERVER_ENVIRONMENT": "dev"
      }
    }
  }
}
```

---

## Gemini CLI

Add an MCP server in Gemini settings (stdio), same command as Claude:

```
uv run --directory /ABS/PATH/TO/mq-sentinel mq-sentinel serve
```

Env: `MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV=true`, `MQS_SERVER_ENVIRONMENT=dev`.

---

## ChatGPT (and other hosted web UIs)

ChatGPT does **not** run local stdio servers. It only accepts a **public HTTPS** MCP endpoint (Developer Mode → custom connector).

Path for ChatGPT / Gemini web / hosted agents:

1. Deploy MQ-Sentinel with HTTP transport + OIDC (`docs/http-transport.md`).
2. Put it on a public URL (or a Cloudflare Tunnel for a demo).
3. In ChatGPT: **Settings → Apps → Advanced → Developer Mode → Create connector** → paste the MCP URL.

Local laptop demo ≠ ChatGPT. Teams that want ChatGPT need the hosted HTTP flavor.

---

## Where to publish so others find it

Do these in order. One listing feeds the rest.

| Priority | Place | Why | Status |
|---|---|---|---|
| 1 | [Official MCP Registry](https://registry.modelcontextprotocol.io/) | Canonical metadata. Smithery, PulseMCP, GitHub, Microsoft pull from here. | `server.json` is in the repo. Publish with `mcp-publisher`. |
| 2 | [Smithery](https://smithery.ai) | Largest install hub for Cursor / Claude Desktop. | `smithery.yaml` is ready. Connect the GitHub repo in the Smithery UI. |
| 3 | PyPI (`mq-sentinel`) | Lets clients run `uvx mq-sentinel serve` with no clone. | Not published yet. README already has the `mcp-name` marker. |
| 4 | PulseMCP / Glama / mcp.so | Extra discovery. Many ingest the official registry automatically. | After step 1. |
| 5 | IBM MQ / middleware communities | Actual buyers: MQ admins, banks, platform teams. | Drafts in `marketing/`. |

There is no single “submit to Claude / ChatGPT / Gemini store” that covers every vendor. Official registry + Smithery is the community path.

Publish checklist: [packaging/mcp/registry-entry.md](../packaging/mcp/registry-entry.md).

---

## Try a prompt after connecting

```
Run full_mq_health_check and give me a prioritized incident summary with IBM citations.
```

More prompts: [usage-with-ai.md](usage-with-ai.md).
