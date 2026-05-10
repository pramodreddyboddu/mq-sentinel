"""Safety invariants for the remediation_steps surface.

`remediation_steps` is the new field that returns IBM-recommended fix commands
as TEXT for the human operator. These strings ARE allowed to contain
destructive verbs (ALTER, DELETE, START, STOP, etc.) — that's the whole point.

The security invariant is: NO CODE PATH passes a `remediation_steps` string
into `connector.execute_mqsc()` or `connector.execute_shell()`.

This is enforced two ways:

1. Source-level grep: the `commands` tuple is only ever serialized to JSON
   for the client, never iterated as input to `execute_mqsc`/`execute_shell`.
2. Behavioural: the matcher modules build findings; the tool layer serializes
   them via `as_dict()`. No tool layer reads `finding.remediation_steps.commands`
   to dispatch them.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from mq_sentinel.rcs.engine import RCSFinding, RemediationScenario, Severity

pytestmark = pytest.mark.security


# Source dir to scan.
_SRC = Path(__file__).resolve().parents[2] / "src" / "mq_sentinel"


def test_rcsfinding_has_remediation_steps_field() -> None:
    f = RCSFinding(
        issue="x",
        severity=Severity.HIGH,
        reason_code=None,
        amq_code=None,
        root_cause="",
        fix_steps=(),
        verify_commands=(),
        doc_refs=(),
        confidence="High",
        remediation_steps=(
            RemediationScenario(scenario="x", commands=("ALTER QMGR DEADQ('NEW')",)),
        ),
    )
    d = f.as_dict()
    assert "remediation_steps" in d
    assert len(d["remediation_steps"]) == 1
    # The destructive verb survives — it's TEXT only.
    assert "ALTER" in d["remediation_steps"][0]["commands"][0]
    # And the execution policy is broadcast on every response.
    assert "execution_policy" in d
    assert "never executes" in d["execution_policy"].lower()


def test_no_code_path_feeds_remediation_to_execute_mqsc() -> None:
    """Grep the source: no occurrence of remediation_steps being iterated
    into execute_mqsc / execute_shell.

    A future refactor that violates this fails CI.
    """
    bad_patterns = (
        ".remediation_steps",  # any attribute access that could iterate it
    )
    # Files allowed to mention remediation_steps (model + serialization + tests).
    allowed_files = {
        "rcs/engine.py",  # defines the field
        "rcs/__init__.py",  # exports
    }
    violations: list[str] = []
    for path in _SRC.rglob("*.py"):
        rel = path.relative_to(_SRC).as_posix()
        if rel in allowed_files or rel.startswith("rcs/matchers/"):
            # matchers create RemediationScenario but never iterate them into execution.
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in bad_patterns:
            if pattern in text:
                # Confirm it's not just in a docstring/comment by checking the line.
                for line in text.splitlines():
                    if pattern in line and not line.lstrip().startswith("#"):
                        violations.append(f"{rel}: {line.strip()}")
    assert not violations, (
        "Found code that iterates remediation_steps outside the model layer:\n"
        + "\n".join(violations)
    )


def test_matchers_never_pass_remediation_to_a_connector() -> None:
    """Source-level guarantee: in every matcher module, no line that creates
    a RemediationScenario also feeds those commands into a connector method.
    """
    matchers_dir = _SRC / "rcs" / "matchers"
    for path in matchers_dir.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        # Matchers should construct findings, never call connectors.
        assert "connector.execute_mqsc" not in src
        assert "connector.execute_shell" not in src
        assert "connector.browse_dlq" not in src


def test_fixstep_invariants_unchanged_for_remediation_findings() -> None:
    """fix_steps must still pass the MQSC allowlist; remediation_steps need
    NOT. Verify the contract explicitly."""
    from mq_sentinel.security.allowlist import (
        CommandNotAllowedError,
        assert_mqsc_allowed,
    )

    f = RCSFinding(
        issue="x",
        severity=Severity.HIGH,
        reason_code=None,
        amq_code=None,
        root_cause="",
        fix_steps=("DISPLAY CHLAUTH('X') ALL",),
        verify_commands=(),
        doc_refs=(),
        confidence="High",
        remediation_steps=(
            RemediationScenario(
                scenario="example destructive command",
                commands=("ALTER QMGR DEADQ('NEW.DLQ')",),
            ),
        ),
    )
    # fix_steps must pass the allowlist
    for step in f.fix_steps:
        assert_mqsc_allowed(step)
    # remediation_steps need NOT pass — they're text only
    for scenario in f.remediation_steps:
        for cmd in scenario.commands:
            if cmd.startswith("#"):
                continue
            # Confirm it would be REJECTED — proving it's not safe to execute.
            with pytest.raises(CommandNotAllowedError):
                assert_mqsc_allowed(cmd)


def test_remediation_scenario_is_immutable() -> None:
    s = RemediationScenario(scenario="x", commands=("ALTER QMGR ...",))
    # frozen dataclass — direct mutation forbidden.
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        s.commands = ("RM -RF /",)  # type: ignore[misc]


def inspect_signal() -> str:
    """Used by future inspections; kept for traceability."""
    return inspect.getsource(RCSFinding)
