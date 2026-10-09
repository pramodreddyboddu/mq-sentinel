---
description: Run a full read-only health check on an IBM MQ queue manager and write an incident-ready summary
argument-hint: <QM_NAME>
---

Run a full MQ-Sentinel health check on queue manager `$ARGUMENTS`.

1. If no queue manager was given, call the `health` tool, list the queue managers it returns, and ask which one to check.
2. Call `full_mq_health_check` with `qm_name` set to the queue manager.
3. If the result shows Native HA, RDQM, multi-instance or z/OS QSG topology, also run the matching `diagnose_*` tool.
4. Reply with:
   - A one-line verdict (healthy / degraded / critical) with the queue manager, MQ version and topology.
   - Findings ordered CRITICAL → LOW. Each one gets its root cause, the evidence the tool returned, and its IBM documentation link.
   - Next steps as MQSC for the user to run. Investigation (`DISPLAY`) commands go first. Any command that changes state is clearly marked as the user's decision.
   - A short incident note (5 lines max) that can be pasted into Slack or PagerDuty.

Only report what the tools returned. Don't add reason codes, causes or links of your own.
