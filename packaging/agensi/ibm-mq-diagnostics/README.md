# IBM MQ Diagnostics (MQ-Sentinel)

An agent skill for diagnosing IBM MQ. Ask your agent about a RETRYING channel, a reason code, a growing dead-letter queue, or cluster, Native HA, RDQM, multi-instance or z/OS QSG health. You get a cited diagnosis: evidence, root cause, the `DISPLAY` commands to confirm it, IBM documentation links, and possible fixes for you to review.

The diagnosis comes from **MQ-Sentinel**, a free, read-only MCP server ([PyPI](https://pypi.org/project/mq-sentinel/), [GitHub](https://github.com/pramodreddyboddu/mq-sentinel)). This skill tells your agent when and how to use it, and how to report what it finds.

## What's inside

| Path | Purpose |
|---|---|
| `SKILL.md` | Instructions the agent follows: tool choice, report format, safety rules |
| `references/tools.md` | The 9 MQ-Sentinel tools: inputs, what each checks, output shape |
| `references/setup.md` | Installing MQ-Sentinel in demo, local live or central org mode, with least-privilege MQ setup |
| `references/reason-codes.md` | MQ reason codes, AMQ messages and topics MQ-Sentinel cites, with IBM doc links |
| `templates/` | Ready-to-copy MCP configs for Claude Code, Claude Desktop, Cursor, VS Code, a central org server, plus an inventory template |
| `examples/demo-health-check.md` | A complete report from demo mode |

## Quick start

1. Add MQ-Sentinel to your agent using the template for it (`references/setup.md`). Demo mode needs only [`uv`](https://docs.astral.sh/uv/), no IBM MQ.
2. Ask: *"Run a health check on DEMO_QM."*
3. To use your own queue managers, follow section 3 of `references/setup.md`.

## Safety

- Read-only: only allowlisted `DISPLAY` commands reach your queue managers. Dead-letter queue messages are browsed for headers only.
- No credentials in the skill, the config or the chat. MQ-Sentinel reads them from its own secrets directory.
- The skill runs no code and makes no network calls. MQ-Sentinel connects only to the queue managers you list in its inventory.
