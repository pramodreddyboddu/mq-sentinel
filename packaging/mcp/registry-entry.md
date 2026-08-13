# How to list MQ-Sentinel so MCP clients can find it

The old “open a PR on `modelcontextprotocol/servers`” README table is no longer the official path. Publish metadata once; marketplaces consume it.

## 1. Official MCP Registry (do this first)

Canonical store: https://registry.modelcontextprotocol.io/

Namespace with GitHub login: `io.github.pramodreddyboddu/mq-sentinel`  
Manifest: repo-root [`server.json`](../../server.json)

### Prerequisites

1. Rebuild and push the image **with** the MCP ownership label (already in `deploy/Dockerfile`):

   ```
   LABEL io.modelcontextprotocol.server.name="io.github.pramodreddyboddu/mq-sentinel"
   ```

   Tag must match `server.json` (`ghcr.io/pramodreddyboddu/mq-sentinel:0.3.0`). The registry will reject a missing image or a missing label.

2. Install the publisher:

   ```bash
   brew install mcp-publisher
   # or: https://github.com/modelcontextprotocol/registry/releases
   mcp-publisher --help
   ```

3. Publish (interactive GitHub device login):

   ```bash
   cd /path/to/mq-sentinel
   mcp-publisher validate          # dry check of server.json
   mcp-publisher login github
   mcp-publisher publish
   ```

4. Confirm:

   ```bash
   curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.pramodreddyboddu/mq-sentinel"
   ```

Optional later: add a PyPI package (`registryType: pypi`) so clients can `uvx mq-sentinel serve`. README already contains `<!-- mcp-name: io.github.pramodreddyboddu/mq-sentinel -->`.

## 2. Smithery

`smithery.yaml` is already at the repo root.

1. Open https://smithery.ai → Add Server
2. Connect GitHub repo `pramodreddyboddu/mq-sentinel`
3. Smithery reads `smithery.yaml` and lists the server

## 3. Other directories

After the official registry listing exists, check (many auto-ingest):

- https://www.pulsemcp.com
- https://glama.ai/mcp
- https://mcp.so

Manual submit only if they have not picked it up in a day or two.

## 4. Client-specific “stores”

There is no one plugin that installs into Claude + ChatGPT + Gemini + Grok at once.

- **Grok / Claude Desktop / Claude Code / Cursor / Gemini CLI** — stdio (local) or HTTP. Copy-paste configs: [`docs/mcp-clients.md`](../../docs/mcp-clients.md)
- **ChatGPT** — public HTTPS MCP URL only (Developer Mode custom connector). Needs hosted HTTP + OIDC.

## 5. Community (buyers, not just developers)

Use the drafts in `marketing/`:

- IBM MQ / middleware Slack & LinkedIn groups
- r/IBMMQ, r/mcp
- Platform-engineering communities (banks, insurers already run MQ)

## Legacy README-table entry

If a community list still wants a markdown row:

> **[MQ-Sentinel](https://github.com/pramodreddyboddu/mq-sentinel)** — Read-only IBM MQ diagnostic MCP server. Root Cause + Fix Steps + verified IBM KC citations across 10 MQ flavors. Eight tools, prompt-injection firewall, hash-chained audit, OIDC HTTP transport.

```bash
docker run -i --rm \
  -e MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV=true \
  ghcr.io/pramodreddyboddu/mq-sentinel:0.3.0 \
  serve --transport stdio
```
