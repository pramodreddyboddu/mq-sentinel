# Agensi listing: copy-paste text

Upload: `dist/agensi/ibm-mq-diagnostics-<version>.zip` (build with `make agensi`)

**Price:** Free

**Title:** IBM MQ Diagnostics (MQ-Sentinel)

**Category:** DevOps / Infrastructure (or the closest: Monitoring, Middleware)

**Tags:** ibm-mq, middleware, mqsc, troubleshooting, observability, mcp, devops, sre, read-only

**Short description (one line):**
Diagnose IBM MQ channels, dead-letter queues, clusters, Native HA, RDQM and z/OS QSG with cited root causes and IBM doc links. Read-only.

**Long description:**

Ask your agent why a channel is RETRYING, what MQRC 2035 means on your queue manager, why the dead-letter queue is growing, or whether your cluster or Native HA setup is healthy. You get a cited diagnosis: the evidence, the root cause, the `DISPLAY` commands to confirm it, links to the matching IBM Documentation pages, and possible fixes for you to review.

The skill drives MQ-Sentinel, a free, read-only MCP server for IBM MQ:

- 9 tools: channels, dead-letter queue (headers only, bodies never read), cluster, Native HA, RDQM, multi-instance, z/OS queue-sharing groups, and a full health check with an executive summary
- Read-only by design: only allowlisted `DISPLAY` commands reach your queue managers, and suggested changes come back as text for you to run
- Every IBM documentation link it cites is checked daily
- Try it in demo mode with no IBM MQ, then connect your own queue managers, or a central team server with SSO

Includes ready-to-copy configs for Claude Code, Claude Desktop, Cursor and VS Code, a least-privilege MQ setup guide (`setmqaut`, CHLAUTH), and a reason-code reference.

**Requirements:** the free MQ-Sentinel MCP server (`uv` for demo mode; the IBM MQ client for live queue managers).

**Links:**
- PyPI: https://pypi.org/project/mq-sentinel/
- GitHub: https://github.com/pramodreddyboddu/mq-sentinel
- MCP Registry: io.github.pramodreddyboddu/mq-sentinel

**Supported agents:** any MCP-capable agent. Configs included for Claude Code, Claude Desktop, Cursor and VS Code (Copilot).
