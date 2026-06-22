# Contributing to MQ-Sentinel

Thank you for your interest in MQ-Sentinel. We treat this as a high-trust, security-sensitive project. Contributions are welcome, but we have high bars for correctness, security, and documentation.

## Code of Conduct

Be respectful. Security discussions in particular should stay constructive.

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (strongly recommended)
- Docker (for building images and running the full demo)
- Optional: IBM MQ client libraries + `pymqi` if you want to test against real QMs (see `docs/byom.md`)

### Quick Start

```bash
git clone https://github.com/pramodreddyboddu/mq-sentinel.git
cd mq-sentinel

# Install everything (editable + dev tools)
make install

# Run the full gauntlet
make ci
```

### Common Commands

```bash
make test          # All tests
make security      # Security-marked tests only (must stay green)
make lint type     # Ruff + mypy
make demo          # Run against cached fixtures (no MQ required)
make demo-record   # Record a new asciinema cast
```

## Project Structure (Owner Perspective)

```
src/mq_sentinel/
  security/     # The crown jewels: allowlist, sanitizer, ratelimit
  rcs/          # Root Cause Summary engine + verified KC registry
  tools/        # The 8 diagnostic tools (one file per major area)
  matchers/     # Pattern matchers inside rcs (very high scrutiny)
  connectors/   # Real (pymqi) vs fixture
  auth/         # OIDC + RBAC
  audit/        # Hash-chained audit log
  server.py     # Dispatcher + wiring (keep this boring)
cli/            # Typer CLI
```

## Adding or Modifying a Diagnostic Tool

1. Add or update a matcher in `src/mq_sentinel/rcs/matchers/`.
2. Create or update the tool in `src/mq_sentinel/tools/`.
3. Wire it in `server.py` (import + dispatch table).
4. Add unit tests + at least one e2e test in `tests/integration/`.
5. Add negative security tests if the change touches data flow.
6. Update `docs/` and README table if user-facing.
7. Run `make ci` before opening a PR.

**Golden rule**: If a matcher can be tricked into giving wrong advice on real MQ output, the change does not ship.

## Security Changes

Any change that touches:
- `security/`
- `auth/`
- `audit/`
- allowlists
- sanitization
- RBAC scoping

...requires extra scrutiny. Add or update tests in `tests/security/`. These tests are part of the release gate.

## Testing Philosophy

- Unit tests for pure logic (matchers, sanitizer, RBAC, etc.).
- Integration tests use rich fixtures (see `demo-sandbox/fixtures/`).
- Security tests are explicitly marked and run in CI.
- Hypothesis/property-based testing is encouraged for complex parsers.

We aim for high branch coverage on the security-critical paths.

## Documentation

If you change user-visible behavior:
- Update the relevant doc in `docs/`
- Consider updating `marketing/` launch materials
- Update the main README table of tools

## Commit & PR Guidelines

- Small, focused PRs are strongly preferred.
- Every PR should include:
  - Description of the problem
  - How it was tested (including security implications)
  - Link to any related org-readiness or threat-model items
- We may ask for updates to `VISION.md` or `SECURITY_POSTURE.md` for significant changes.

## License & Contributions

By contributing, you agree that your contribution will be licensed under the same terms as the project (currently proprietary with the project owner retaining all rights). We may discuss contribution agreements for larger changes.

## Questions?

Open a GitHub issue or start a discussion. For security matters, follow the process in `SECURITY.md`.

---

We are building something that security teams and MQ SREs can actually trust. High standards are a feature.
