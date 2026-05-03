# MCP Registry submission

This is the entry to add to the community list at
[github.com/modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)
(in the "Community Servers" section of `README.md`).

## How to submit

```bash
# 1. Fork modelcontextprotocol/servers
# 2. In the README.md, append the row below to the "Community Servers" table:
```

## The entry

> ### 🔧 IBM MQ Diagnostics
>
> - **[MQ-Sentinel](https://github.com/pramodreddyboddu/mq-sentinel)** — Read-only IBM MQ diagnostic MCP server with Root Cause + Recommended Fix Steps + IBM Knowledge Center citations for every IBM MQ deployment flavor (Standalone, Multi-Instance, RDQM, Native HA + CRR, Uniform Cluster, Traditional Cluster, z/OS QSG). Eight diagnostic tools, prompt-injection firewall, hash-chained audit, OIDC-authenticated HTTP transport.

## PR description template

```markdown
## What

Adds MQ-Sentinel — a read-only IBM MQ diagnostic MCP server — to the
Community Servers list.

## Why this fits the registry

- **Real-world enterprise use case**: IBM MQ is deployed at every Fortune
  500 bank, insurer, airline, and telco. Admins burn hours chasing reason
  codes 2035, 2009, 2080 across distributed/Native HA/RDQM/z/OS topologies.

- **Demonstrates security best practices for MCP servers**:
  - Read-only static command allowlist (DISPLAY/DIS/PING CHANNEL only).
  - Output sanitizer + URL allowlist that constrains responses to
    `www.ibm.com` — protecting the downstream LLM from prompt injection
    via untrusted MQ data (queue/channel names, log lines, DLQ headers).
  - Hash-chained tamper-evident audit log.
  - DLQ-bodies-never-read invariant enforced by tests that scan the
    server's own source code.

- **Production-ready**: OIDC bearer auth, distroless container, signed
  images, Helm chart, RPM/DEB packages, 167 tests, mypy strict, ruff clean.

## Try it

```bash
docker run -i --rm \
  -e MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV=true \
  ghcr.io/pramodreddyboddu/mq-sentinel:latest \
  serve --transport stdio
```

The bundled demo sandbox produces realistic Root Cause Summaries against
seeded faults — no live IBM MQ required to evaluate.
```
