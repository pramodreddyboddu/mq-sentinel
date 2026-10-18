# Example: health check in demo mode

Demo mode uses MQ-Sentinel's bundled fixtures, so anyone can reproduce this without IBM MQ. The findings below are what `full_mq_health_check` returns for `DEMO_QM`. The report is how this skill tells the agent to present them.

## User

> Our on-call got paged for DEMO_QM. Give me a health report.

## Agent: tool calls

1. `health` returns `"connector": "demo-fixtures"`, with queue managers `["DEMO_QM"]`.
2. `full_mq_health_check(qm_name="DEMO_QM")` returns `overall_status: CRITICAL`: 18 findings (3 CRITICAL, 9 HIGH, 6 MEDIUM) and topology `native_ha`.
3. Because the topology is Native HA, the agent also calls `diagnose_native_ha_issues(qm_name="DEMO_QM")`.

## Agent: report

**DEMO_QM: CRITICAL.** MQ 9.4.0.0, Native HA, clustered. 18 findings: 3 critical, 9 high, 6 medium. *(Demo data from MQ-Sentinel's fixtures, not a real queue manager.)*

### Critical

1. **Channel INDOUBT.RCVR is in doubt.** Uncommitted batches can't resolve on their own.
   - Evidence: channel `INDOUBT.RCVR`, status `INDOUBT`
   - Investigate: `DISPLAY CHSTATUS('INDOUBT.RCVR') ALL CURLUWID LSTLUWID`
   - Possible fix, **your decision after checking the remote QM's batch state**: `RESOLVE CHANNEL('INDOUBT.RCVR') ACTION(COMMIT)` or `ACTION(BACKOUT)`. Choosing wrongly duplicates or loses messages.
2. **Cluster ORDERS has no visible full repository.**
3. **Cluster PAYMENTS has no visible full repository.**

### High

4. **Channel APP.SVRCONN returned MQRC 2035 (NOT_AUTHORIZED).**
   - Root cause: the connecting principal failed authorization. A CHLAUTH BLOCKUSER rule, an MCAUSER missing `+connect`/`+inq`, or rejected CONNAUTH credentials.
   - Evidence: channel `APP.SVRCONN`, status `RETRYING`, remote QM `REMOTE_QM`
   - Investigate: `DISPLAY CHLAUTH('APP.SVRCONN') MATCH(RUNCHECK) ALL`, `DISPLAY CHSTATUS('APP.SVRCONN') ALL`, `DISPLAY QMGR CONNAUTH`
   - IBM docs: [2035 (07F3) MQRC_NOT_AUTHORIZED](https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2035-07f3-rc2035-mqrc-not-authorized)
5. **Channel TO.PARTNER connection error (reason 2009).**

*(The remaining HIGH and MEDIUM findings follow in the same format.)*

### Next steps

Run the `DISPLAY` commands above first. Every change command is a recommendation for your change window; MQ-Sentinel hasn't run anything.

### On-call note

> DEMO_QM CRITICAL: in-doubt channel INDOUBT.RCVR (needs a manual resolve decision), no full repository for clusters ORDERS and PAYMENTS, APP.SVRCONN failing with 2035 (authorization), TO.PARTNER failing with 2009 (connection). DLQ depth 1247. Read-only diagnosis via MQ-Sentinel; no changes made.
