# Development Guide for MQ-Sentinel

This document is written from the perspective of someone who owns and maintains this project long-term.

## Philosophy

- Trust and correctness are the product.
- The bar is high because this tool can be given to powerful AI agents that touch production messaging systems.
- Prefer explicit, boring, well-tested code over cleverness.
- Every new diagnostic must come with evidence from real MQ output + IBM documentation.

## Getting Started

```bash
# 1. Clone
git clone https://github.com/pramodreddyboddu/mq-sentinel.git
cd mq-sentinel

# 2. Install (uv is strongly preferred)
make install

# 3. Verify everything works
make ci
make demo
uv run mq-sentinel doctor
uv run mq-sentinel tools
```

## Running Without Real MQ (Recommended for Most Work)

The project has excellent fixture support:

```bash
make demo                 # full walk-through against seeded faults
make demo-fast
DEMO_MODE=cached make demo
```

This exercises the full tool chain without any IBM MQ client libraries.

## Working With Real Queue Managers

See `docs/byom.md` for how to bring your own MQ client libraries.

For local development against a real QM you control:

```bash
export MQS_SERVER_ENVIRONMENT=dev
export MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV=true
uv run mq-sentinel serve --transport http --port 8080
```

Then point your MCP client or curl at it.

**Never** run with `disable_auth_for_local_dev=true` against production QMs.

## Adding a New Diagnostic

1. **Understand the failure mode**
   - Capture real MQSC output or logs from the problem.
   - Talk to MQ admins if possible.

2. **Add a matcher** (most logic lives here)
   - `src/mq_sentinel/rcs/matchers/<area>.py`
   - Return `RCSFinding` objects with severity + evidence + KC links.

3. **Create the tool**
   - `src/mq_sentinel/tools/<area>.py`
   - Implement the public function that the MCP layer calls.

4. **Wire it up**
   - Import in `server.py`
   - Add to the dispatch logic and health check composite if appropriate.

5. **Tests are mandatory**
   - Unit tests for the matcher
   - At least one integration test using fixtures in `tests/integration/`
   - If it touches data from MQ → security test in `tests/security/`

6. **Documentation**
   - Update the table in README.md
   - Consider updating `marketing/` assets
   - Add to `packaging/mcp/mcp-manifest.json`

7. **Run the full gate**
   ```bash
   make ci
   ```

Golden rule: If the matcher can be fooled by realistic MQ output into giving incorrect advice, do not ship it.

## Running the Full CI Locally

```bash
make ci          # lint + type + test + security
make security    # only the security negative tests
```

## Packaging & Releases

- Version is the single source of truth in `src/mq_sentinel/__init__.py`
- `make pkg` builds RPM + DEB (requires `fpm`)
- Docker image is built and signed in CI on main pushes
- Helm chart lives in `deploy/helm/`

## Observability & Telemetry During Development

```bash
uv run mq-sentinel serve --transport http
# Metrics exposed on :9464 by default
# Prometheus alerts + Grafana dashboard in observability/
```

## Security Mindset

When making changes, constantly ask:

- Can untrusted data from MQ reach the LLM without going through the sanitizer?
- Does this open any path to executing non-readonly MQSC?
- Would a security reviewer be comfortable seeing this in a SOC2 audit?

If the answer is uncertain, pause and discuss.

## Useful Commands

| Command                        | Purpose                              |
|--------------------------------|--------------------------------------|
| `uv run mq-sentinel doctor`    | Environment & config self-check      |
| `uv run mq-sentinel tools`     | List all diagnostics                 |
| `uv run mq-sentinel health`    | In-process health (no QM)            |
| `uv run mq-sentinel verify-audit` | Check hash chain integrity       |
| `make demo`                    | End-to-end demo with faults          |

## Questions?

Open an issue or start a discussion. For anything touching the security model, prefer private discussion first.

---

Maintained with care. This project exists to make enterprise MQ teams trust AI agents again.
