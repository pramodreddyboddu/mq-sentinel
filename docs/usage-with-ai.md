# Using MQ-Sentinel with AI Agents

This guide shows how to get the most value out of MQ-Sentinel when using it with Claude, Cursor, Grok, or other MCP-capable tools.

## Why MQ-Sentinel is different

Most approaches to "AI + IBM MQ" either:
- Give the model raw MQ access (dangerous)
- Rely on the model to hallucinate fixes from memory (unreliable)

MQ-Sentinel returns **typed, evidence-backed, citation-verified** diagnostics that the model can trust and present to you.

## Recommended Setup

### For local development / Claude Desktop / Cursor

```bash
# Easiest: run in dev mode (stdio)
uv run mq-sentinel serve
```

Then add the stdio server in your AI tool's MCP settings.

### For production / team use

Use the HTTP transport with OIDC (see `docs/http-transport.md` and `docs/oidc-examples.md`).

## Example Prompts That Work Well

### Quick health check
```
Run full_mq_health_check on PROD_QM1 and give me a prioritized summary of issues.
```

### Channel problems
```
My channel APP.SVRCONN to PROD_QM is in RETRYING state with 2035. Use diagnose_failed_channels and tell me the most likely causes + the exact MQSC I should run to investigate.
```

### DLQ storm
```
There's a big DLQ on PROD_QM. Use analyze_dlq_and_suggest_reprocessing. Group by reason code and tell me which messages look like they can be safely reprocessed.
```

### Native HA issues
```
Check Native HA on QMHA1. Tell me replica states, any quorum or lag problems, and recommended next steps with citations.
```

### Cluster health
```
Run check_cluster_health on our uniform cluster and highlight any stale or suspended members.
```

### Executive summary for on-call
```
Give me a full health picture of QMCLUSTER1 using full_mq_health_check. Format it as a short incident report I can paste into Slack/PagerDuty.
```

## Pro Tips

- Always let the model use `full_mq_health_check` first when the problem is unclear — it runs the relevant subset of checks.
- Ask for **exact MQSC commands** to run. MQ-Sentinel is designed to give you commands you can copy-paste.
- Ask for citations: "include the IBM KC link".
- For z/OS or RDQM, be explicit: "use diagnose_zos_qsg_issues" or "use diagnose_rdqm_issues".

## What the model should never do

MQ-Sentinel will refuse (by design) any request that would require:
- Writing to MQ
- Running RESET, STOP, RESOLVE, etc.
- Reading message bodies from DLQ

If the AI suggests destructive commands, it is not using MQ-Sentinel correctly or is ignoring its output.

## Debugging the connection

```bash
# Check your environment
uv run mq-sentinel doctor

# See what tools are available
uv run mq-sentinel tools
```

## Getting the best results

1. Start broad with `full_mq_health_check`.
2. Drill down with the specific tool mentioned in the summary.
3. Ask the model to translate findings into the exact next MQSC command + why.

MQ-Sentinel turns "I don't know what's wrong with my MQ" into "Here are the 3 most likely causes with the commands to confirm".

---

Built and maintained as a serious engineering project. The goal is that you (and your AI) can trust the answers.
