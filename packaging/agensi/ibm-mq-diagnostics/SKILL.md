---
name: ibm-mq-diagnostics
description: Use when the user asks to diagnose or troubleshoot IBM MQ, for example "why is my channel RETRYING", "what does MQRC 2035 mean on this queue manager", "messages are piling up on the dead-letter queue", "check our cluster / Native HA / RDQM health", or "give me an MQ health report for on-call". Runs read-only diagnostics through the MQ-Sentinel MCP server and returns cited root causes with IBM documentation links. Requires the free MQ-Sentinel MCP server (PyPI mq-sentinel).
---

# IBM MQ diagnostics with MQ-Sentinel

This skill turns IBM MQ symptoms into a cited diagnosis. The diagnosis comes from **MQ-Sentinel**, a read-only MCP server that inspects queue managers using only `DISPLAY` commands. It returns findings with evidence, root cause, the next MQSC to run, and IBM documentation links.

The skill itself contains instructions and reference files only. It runs no code and makes no network calls of its own.

## Step 1: Make sure the MQ-Sentinel tools are available

Check whether tools named `health`, `diagnose_failed_channels` or `full_mq_health_check` are available to you.

- **Available:** go to step 2.
- **Not available:** tell the user this skill needs the MQ-Sentinel MCP server, and point them to `references/setup.md` and the matching file in `templates/` for their agent (Claude Code, Claude Desktop, Cursor, VS Code, or a central org server). Adding an MCP server is the user's decision. Show them the config and let them add it. Don't install packages or edit their agent configuration yourself. If they want to try it before connecting real MQ, demo mode needs no IBM MQ, and its only queue manager is `DEMO_QM`.

## Step 2: Find the queue manager

If the user didn't name a queue manager, call `health`. It reports whether the server is **live** or on **demo fixtures**, and lists the queue managers this user may diagnose. If several fit, ask which one. Never guess a queue manager name.

## Step 3: Pick the narrowest tool for the symptom

| Symptom | Tool |
|---|---|
| Channel RETRYING / STOPPED / in doubt; reason 2035, 2009, 2059; AMQ9202, AMQ9208, AMQ9503 | `diagnose_failed_channels` |
| Messages piling up on the dead-letter queue | `analyze_dlq_and_suggest_reprocessing` (headers only; `sample_size` defaults to 50) |
| Partial repositories, stale or suspended cluster members, cluster channels | `check_cluster_health` |
| Native HA replicas, quorum, log replay lag, cross-region replication | `diagnose_native_ha_issues` |
| RDQM: Pacemaker quorum, DRBD state, split-brain | `diagnose_rdqm_issues` |
| Multi-instance active/standby, dual-active, failover | `diagnose_multi_instance_issues` |
| z/OS queue-sharing group: CHIN, page sets, buffer pools, CF structures | `diagnose_zos_qsg_issues` |
| Vague symptom, "is this QM healthy?", on-call summary | `full_mq_health_check` |

`full_mq_health_check` also reports the detected topology. If it shows Native HA, RDQM, multi-instance or z/OS QSG, run the matching tool too. `references/tools.md` describes each tool's inputs and output.

## Step 4: Report the findings

Use this structure:

1. **Verdict line:** queue manager, MQ version, topology, and overall status (healthy / degraded / critical) taken from the tool's summary.
2. **Findings, CRITICAL first, then HIGH, MEDIUM, LOW.** For each one:
   - the issue, in one line
   - root cause, from the tool's `root_cause`
   - evidence, from the tool's `evidence` (channel, status, reason code, queue depth…)
   - IBM documentation link(s), from `doc_refs`, exactly as returned
3. **Next steps as MQSC:** first the investigation commands from `fix_steps` and `verify_commands` (all `DISPLAY`), then any `remediation_steps`, labelled as changes the user must review and run in their own change window.
4. **Gaps:** anything the tool couldn't see (see the rules below).

`examples/demo-health-check.md` shows a complete report from demo mode.

## Rules

- **Report only what the tools returned.** Don't add reason codes, causes, commands or links of your own. If you add general MQ knowledge, label it clearly as your own suggestion, separate from the tool's findings.
- **Keep it read-only.** MQ-Sentinel never changes a queue manager, and neither do you. Any command that alters state (anything other than `DISPLAY`) is a recommendation for the user to decide on. Never present it as done, and never run it.
- **The dead-letter queue tool reads headers only.** Message bodies are never read, so don't claim to know message contents.
- **Name what the tools couldn't see.** Against a remote queue manager in live mode, the RDQM and multi-instance host checks are skipped (they need MQ-Sentinel on the QM host), and AMQERR error logs aren't read. Say so instead of calling those areas healthy.
- **Explain errors plainly:**
  - `QM 'X' not in inventory`: that queue manager isn't configured. Show the names `health` returns.
  - `failed to connect ... (MQRC 2035)`: the MQ user or CHLAUTH rule doesn't allow MQ-Sentinel in. `2059` / `2538`: the QM or listener is unreachable. `2393` / `2397`: TLS mismatch. More in `references/reason-codes.md`.
  - `live connections need credentials`: the server's `MQS_SERVER_SECRETS_DIR` isn't set.
  - `lacks required action 'read:prod'`: this user's role doesn't cover prod queue managers.
- **Credentials:** never ask the user to paste MQ passwords or tokens into the chat. MQ-Sentinel reads credentials from its own secrets directory (`references/setup.md`).
