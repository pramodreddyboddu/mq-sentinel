# MQ-Sentinel — 5-Minute Demo Script

A walk-through that runs end-to-end against the bundled `demo-sandbox/` —
no live IBM MQ required.

## Setup (one-time, ~30s)

```bash
git clone https://github.com/pramodreddyboddu/mq-sentinel.git
cd mq-sentinel
uv sync --all-extras --dev
uv pip install -e .
```

## The pitch (30 seconds)

> "Your MQ admins burn hours chasing 2035s, DLQ storms, Native HA replica lag,
> stale CLUSQMGR entries, RDQM split-brains, z/OS page-set fills. MQ-Sentinel
> plugs into Claude or Cursor and returns **Root Cause + Exact Fix Steps + IBM
> Knowledge Center link** in seconds — read-only, audit-logged, zero
> hallucinations, every IBM MQ flavor."

## Beat 1 — server is up + tamper-evident audit (45s)

```bash
uv run mq-sentinel version
uv run mq-sentinel health
uv run mq-sentinel verify-audit
```

Talking point: *"Every tool call is hash-chained into an append-only JSONL.
Any retroactive edit breaks the chain. Compliance teams love this."*

## Beat 2 — channel diagnosis with KC citation (60s)

Connect Claude / Cursor to the MCP via stdio (the standard MCP wire-up), then:

```
diagnose_failed_channels(qm_name="DEMO_QM")
```

Surfaces (from seeded fixtures):
- **HIGH: APP.SVRCONN — MQRC 2035 NOT_AUTHORIZED** with CHLAUTH/CONNAUTH fix steps + IBM KC link.
- **HIGH: TO.PARTNER — connection error (2009)** with AMQ9202 KC link.
- **CRITICAL: INDOUBT.RCVR is in-doubt** — and notice **no `RESOLVE CHANNEL` is suggested**: read-only by design.
- **HIGH: AMQERR contains AMQ9503E** with KC link.

Talking point: *"Notice the link goes to `www.ibm.com/docs/...`. We enforce
that allowlist — every URL the MCP returns is verified-IBM. No model can
hallucinate a fake fix URL through us."*

## Beat 3 — DLQ analyzer, **headers only** (45s)

```
analyze_dlq_and_suggest_reprocessing(qm_name="DEMO_QM")
```

Demo QM has DLQ depth 1247 with mixed reasons:
- **HIGH: DLQ depth 1247** with `DISPLAY QSTATUS` follow-up.
- 2035, 2030, 2053, 2051 each grouped with KC link + per-reason fix steps.
- **HIGH: 2 messages with backout_count >= 5** — poison-message detector.
- Response carries `"bodies_read": false` — auditable.

Talking point: *"The DLQ tool reads only MQDLH headers — never message
bodies. We have a security test that reads our own source code to enforce
this: anyone who refactors and breaks the guarantee fails CI."*

## Beat 4 — composite health check, executive summary (45s)

```
full_mq_health_check(qm_name="DEMO_QM")
```

Single connection runs channels + DLQ + cluster against the fixture QM,
returns:

```json
{
  "summary": {
    "overall_status": "CRITICAL",
    "by_severity": {"CRITICAL": 3, "HIGH": 7, "MEDIUM": 2, "LOW": 0, "INFO": 0},
    "by_category": {"channels": 4, "dlq": 5, "cluster": 3},
    "top_issues": [
      {"severity": "CRITICAL", "category": "cluster",
       "issue": "Cluster PAYMENTS has no visible full repository"},
      {"severity": "CRITICAL", "category": "channels",
       "issue": "Channel INDOUBT.RCVR is in-doubt"},
      "..."
    ]
  },
  "findings": [/* sorted by severity then category */],
  "checks_run": ["channels", "dlq", "cluster"]
}
```

Talking point: *"This is the daily digest a Slack bot or PagerDuty webhook
would consume. Severity counts, top issues, full sortable list."*

## Beat 5 — every IBM MQ flavor (60s)

Quickly fan through the topology-specific tools — same fixture QM, different
diagnostic surfaces:

```
diagnose_native_ha_issues(qm_name="DEMO_QM")
# → DEMO_QM-2 DISCONNECTED (HIGH), 60% replay (HIGH), CRR lag 420s (CRITICAL)

diagnose_rdqm_issues(qm_name="DEMO_QM")
# → rdqm-3 OFFLINE (HIGH), DEMO_QM-monitor failed (HIGH),
#   DRBD WFConnection (HIGH), DEMO_QM_LOGS Inconsistent (HIGH)

diagnose_zos_qsg_issues(qm_name="DEMO_QM")
# → MQA3 INACTIVE, CHIN STOPPED (CRITICAL), PSID 2 at 97% (CRITICAL),
#   BUFFPOOL 1 at 5% free, CF APPLICATION2 FAILED (CRITICAL)

diagnose_multi_instance_issues(qm_name="DEMO_QM")
# → CRITICAL: 2 ACTIVE instances (split-brain) on host1, host2

check_cluster_health(qm_name="DEMO_QM")
# → CRITICAL: Cluster PAYMENTS has no visible full repository,
#   stale CLUSQMGR, suspended member, RETRYING channel
```

Talking point: *"Every flavor IBM ships, in 167 lines of test fixtures
and one process."*

## Beat 6 — production deployment in three commands (30s)

```bash
helm install mq-sentinel deploy/helm \
  --set oidc.issuer=https://login.example.com/realms/mq-sentinel \
  --set oidc.audience=mq-sentinel \
  --set oidc.jwksUrl=https://login.example.com/.well-known/jwks.json
```

Then:

```bash
curl -H 'Authorization: Bearer eyJ...' \
     -H 'Content-Type: application/json' \
     -d '{"tool":"full_mq_health_check","params":{"qm_name":"PROD_QM"}}' \
     https://mq-sentinel.example.com/mcp/tools/call | jq .summary
```

Talking point: *"Distroless image, non-root, read-only filesystem, dropped
caps, OIDC bearer auth, hash-chained audit, Prometheus metrics, JWKS cached
10 minutes with stale-on-error fallback. Not a prototype — this is the
deployment posture from day one."*

## Closing (30s)

> "Eight tools, ten IBM MQ flavors, every recommendation backed by an IBM
> Knowledge Center link. Read-only by construction — the MCP cannot
> execute a destructive command even if you wanted it to. Plugs into your
> existing Claude / Cursor / Claude Code workflow today.
> Want to run it against your QMs? Let's set up a 30-day pilot."

---

## Fault catalog (for re-recording)

Every demo finding maps to a fixture in `demo-sandbox/fixtures/`:

| Topology | Fixture file | Seeded fault |
|---|---|---|
| Distributed | `mqsc/DISPLAY_CHSTATUS_ALL__ALL.json` | 2035, 2009, INDOUBT, AMQ9503E |
| DLQ | `dlq/SYSTEM.DEAD.LETTER.QUEUE.json` | depth 1247, mixed reasons, backout=7 |
| Cluster | `mqsc/DISPLAY_CLUSQMGR_ALL__ALL.json` | RETRYING, STOPPED, SUSPEND(YES), stale |
| Native HA | `mqsc/DISPLAY_NATIVEHASTATUS.json` | DISCONNECTED, 60% replay |
| Native HA CRR | `mqsc/DISPLAY_QMSTATUS_RECOVERYGROUP.json` | REPLICATIONLAG=420 |
| RDQM | `shell/rdqmstatus.txt`, `shell/crm_mon_-1.txt`, `shell/drbdadm_status.txt` | OFFLINE node, failed resource, WFConnection, Inconsistent |
| z/OS | `mqsc/DISPLAY_GROUP.json` + CHINIT/PSID/BUFFPOOL/CFSTATUS | MQA3 INACTIVE, CHIN STOPPED, PSID 97%, CF FAILED |
| MIQM | `shell/dspmq_-x.txt` | dual-active on host1 + host2 |
