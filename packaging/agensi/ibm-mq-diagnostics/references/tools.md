# MQ-Sentinel tools

Every tool is read-only: it sends only allowlisted MQSC `DISPLAY` commands (plus, on the QM's own host, `dspmq`, `rdqmstatus`, `crm_mon` or `drbdadm status`). Every tool except `health` takes a required `qm_name`.

| Tool | Inputs | What it checks |
|---|---|---|
| `health` | none | Server status, version, environment, connector (`live` or `demo-fixtures`), and the queue managers this caller may read |
| `diagnose_failed_channels` | `qm_name` | `DISPLAY CHSTATUS(*) ALL`: channels RETRYING, STOPPED, PAUSED or in doubt; reason codes 2035, 2009, 2059; AMQ9202, AMQ9208 and AMQ9503 in available log text |
| `analyze_dlq_and_suggest_reprocessing` | `qm_name`, `sample_size` (default 50, max 500) | Browses dead-letter queue **headers** (`MQDLH`; bodies are never read), groups by reason code, flags backout loops |
| `check_cluster_health` | `qm_name` | `DISPLAY CLUSQMGR`: missing full repositories, stale or suspended members, unhealthy cluster channels |
| `diagnose_native_ha_issues` | `qm_name` | `DISPLAY NATIVEHASTATUS`: replica roles, in-sync state, quorum, log replay backlog, cross-region replication |
| `diagnose_rdqm_issues` | `qm_name` | `rdqmstatus`, `crm_mon -1`, `drbdadm status` (QM host only): Pacemaker quorum, offline nodes, DRBD connection and disk state, split-brain |
| `diagnose_multi_instance_issues` | `qm_name` | `dspmq -x` / `dspmq -o standby` (QM host only): active/standby state, dual-active, standby permission |
| `diagnose_zos_qsg_issues` | `qm_name` | `DISPLAY GROUP`, `QMSTATUS`, `USAGE`, `CFSTATUS`: QSG members, channel initiator, page sets, buffer pools, CF structures |
| `full_mq_health_check` | `qm_name`, `dlq_sample_size` (default 50) | Channels, DLQ and cluster in one connection, with topology detection and an executive summary |

## Output shape

Each diagnostic tool returns:

```json
{
  "tool": "full_mq_health_check",
  "qm_name": "PROD_QM1",
  "topology": {"topology": "native_ha", "mq_version": "9.4.0.0", "platform": "UNIX", "...": "..."},
  "summary": {"overall_status": "CRITICAL", "by_severity": {"CRITICAL": 1, "HIGH": 2}, "top_issues": ["..."]},
  "findings": [
    {
      "issue": "Channel APP.SVRCONN returned MQRC 2035 (NOT_AUTHORIZED)",
      "severity": "HIGH",
      "reason_code": 2035,
      "root_cause": "The connecting principal failed authorization...",
      "evidence": {"channel": "APP.SVRCONN", "status": "RETRYING"},
      "fix_steps": ["DISPLAY CHLAUTH('APP.SVRCONN') MATCH(RUNCHECK) ALL", "..."],
      "verify_commands": ["DISPLAY CHSTATUS('APP.SVRCONN') CURRENT"],
      "doc_refs": [{"title": "2035 (07F3) MQRC_NOT_AUTHORIZED", "url": "https://www.ibm.com/docs/..."}],
      "remediation_steps": [{"scenario": "...", "commands": ["..."], "notes": "..."}],
      "confidence": "High"
    }
  ],
  "raw_evidence": {"...": "counts of what was examined"}
}
```

`summary` appears only on `full_mq_health_check`. `fix_steps` and `verify_commands` are always `DISPLAY` commands. `remediation_steps` may change state: present them for the user to review, never as done.

## Severity

- **CRITICAL:** an outage or data-integrity risk now (in-doubt channels, no full repository, lost quorum, split-brain)
- **HIGH:** a service is failing (authorization or connection errors, DLQ growth with a clear cause)
- **MEDIUM:** degraded, or worth fixing soon (replication lag, stale cluster entries)
- **LOW / INFO:** hygiene
