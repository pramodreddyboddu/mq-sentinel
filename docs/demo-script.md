# MQ-Sentinel — 5-Minute Demo Script (to be recorded once Phase 1 Commit 2 lands)

1. `mq-sentinel version` — prove the server runs.
2. `mq-sentinel health` — prove the security middleware pipeline (auth → rate limit → audit → sanitizer) is wired.
3. `mq-sentinel verify-audit` — show the hash-chained audit log is intact.
4. [Phase 1 Commit 2] Connect Claude Code to the MCP; call `diagnose_failed_channels()` against the fixture QM with a seeded 2035 fault. The response shows: raw MQSC evidence → detected issue → root cause → fix steps → IBM KC link.
5. [Phase 1 Commit 2] Tamper the audit log; re-run `verify-audit` and watch it fail loudly.

Fixture faults to seed (`demo-sandbox/fixtures/`):
- `CHLAUTH` deny + `MCAUSER('nobody')` → 2035.
- DLQ with reason codes 2080, 2030, 2051.
- Stale `CLUSQMGR` entry.
- Native HA replica lag > threshold.
