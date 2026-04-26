# MQ-Sentinel Demo Sandbox

Pre-recorded MQSC + shell fixtures so MQ-Sentinel can produce realistic RCS
findings without a live IBM MQ Queue Manager.

## Seeded faults (DEMO_QM, MQ 9.4.0)

| Channel | Status | Reason | Demonstrates |
|---|---|---|---|
| `APP.SVRCONN` | RETRYING | 2035 | CHLAUTH/MCAUSER authorization failure (the canonical demo) |
| `TO.PARTNER` | RETRYING | 2009 | Network/TLS connection error (AMQ9202) |
| `INDOUBT.RCVR` | INDOUBT | — | Manual resolution required (CRITICAL) |
| `HEALTHY.SVRCONN` | RUNNING | 0 | Healthy channel (negative control) |

The error log tail also seeds `AMQ9202E` and `AMQ9503E` so the matcher emits
log-level findings with KC links.

## How fixtures map to commands

`FixtureConnector` fingerprints each MQSC command into a filename:
- spaces → `_`
- `(`/`)` → `_`
- `*` → `ALL`
- `'` removed
- `/` → `_`

Example: `DISPLAY CHSTATUS(*) ALL` → `DISPLAY_CHSTATUS_ALL__ALL.json`.

Shell fixtures use `argv` joined with `_`, e.g.
`["dspmq", "-o", "standby"]` → `dspmq_-o_standby.txt`.
