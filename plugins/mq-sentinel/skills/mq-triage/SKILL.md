---
name: mq-triage
description: Triage IBM MQ problems with the read-only MQ-Sentinel tools. Use when the user reports an IBM MQ issue — a channel in RETRYING/STOPPED/INDOUBT, reason codes like 2035/2009/2059, AMQ9xxx errors, a growing dead-letter queue, cluster or repository problems, Native HA / RDQM / multi-instance failover, or z/OS queue-sharing groups — or asks for an MQ health check.
---

# IBM MQ triage with MQ-Sentinel

Every MQ-Sentinel tool is read-only and takes a `qm_name`. Pick the narrowest tool that fits the symptom; use `full_mq_health_check` when the symptom is vague.

| Symptom | Tool |
|---|---|
| Channel not running, 2035 / 2009 / 2059, AMQ9202 / 9208 / 9503, INDOUBT | `diagnose_failed_channels` |
| Messages piling up on the DLQ | `analyze_dlq_and_suggest_reprocessing` (headers only; `sample_size` default 50) |
| Partial repositories, stale or suspended CLUSQMGR, cluster channels | `check_cluster_health` |
| Native HA replicas, quorum, log replay lag, CRR | `diagnose_native_ha_issues` |
| RDQM: Pacemaker quorum, DRBD state, split-brain | `diagnose_rdqm_issues` |
| Multi-instance active/standby, dual-active, failover | `diagnose_multi_instance_issues` |
| z/OS QSG, CHIN, page sets, buffer pools, CF structures | `diagnose_zos_qsg_issues` |
| "Is this QM healthy?" / on-call summary | `full_mq_health_check` |

## How to answer

1. If the user didn't name a queue manager, ask for one. In demo mode the only QM is `DEMO_QM`.
2. Call the tool. Report findings by severity, highest first.
3. Keep the tool's evidence and IBM Knowledge Center citations attached to each finding. Don't invent reason codes, causes, or links that the tool didn't return.
4. Present suggested MQSC as commands for the user to run. MQ-Sentinel never changes a queue manager, and neither should you: don't propose `RESET`, `RESOLVE`, `CLEAR`, `DELETE`, or DLQ reprocessing as already done. Label any change command as something the user decides to run.
5. If a tool returns an error such as `QM 'X' not in inventory`, say so plainly and point the user to the plugin README for configuring an inventory.
