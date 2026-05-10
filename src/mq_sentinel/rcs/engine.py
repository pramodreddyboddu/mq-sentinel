"""RCS engine: builds hallucination-free findings from raw MQ data + KC registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from mq_sentinel.rcs.kc_registry import KCDocRef, KCRegistry
from mq_sentinel.security.sanitizer import sanitize_mq_output

_EXECUTION_POLICY = (
    "MQ-Sentinel never executes remediation_steps. These are IBM-recommended fix "
    "commands returned as TEXT only for the operator to review and run manually "
    "in a change window. The MCP server is read-only by construction."
)


class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass(frozen=True, slots=True)
class RemediationScenario:
    """A scenario-specific fix recipe from IBM Knowledge Center.

    SAFETY INVARIANT: commands in this dataclass are NEVER passed to
    `connector.execute_mqsc()` or `connector.execute_shell()`. They are
    returned as opaque text strings for the human operator to review and
    run themselves. A grep-based source test enforces this invariant.
    """

    scenario: str
    """Human-readable condition (e.g. 'CHLAUTH BLOCKUSER rule incorrectly matching')."""

    commands: tuple[str, ...]
    """IBM-recommended commands (may include destructive verbs — text only)."""

    notes: str = ""
    """Optional prerequisites, warnings, or rollback guidance."""


@dataclass(frozen=True, slots=True)
class RCSFinding:
    issue: str
    severity: Severity
    reason_code: int | None
    amq_code: str | None
    root_cause: str
    fix_steps: tuple[str, ...]
    """Read-only DISPLAY/PING commands MQ-Sentinel already executed (or would).
    Every string here MUST pass `assert_mqsc_allowed()`."""

    verify_commands: tuple[str, ...]
    doc_refs: tuple[KCDocRef, ...]
    confidence: str  # "High" | "Medium"
    evidence: dict[str, Any] = field(default_factory=dict)
    remediation_steps: tuple[RemediationScenario, ...] = ()
    """IBM-recommended fix recipes. TEXT ONLY — never executed by the MCP."""

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = sanitize_mq_output(
            {
                "issue": self.issue,
                "severity": self.severity.value,
                "reason_code": self.reason_code,
                "amq_code": self.amq_code,
                "root_cause": self.root_cause,
                "fix_steps": list(self.fix_steps),
                "verify_commands": list(self.verify_commands),
                "doc_refs": [{"title": d.title, "url": d.url} for d in self.doc_refs],
                "confidence": self.confidence,
                "evidence": self.evidence,
                "remediation_steps": [
                    {
                        "scenario": s.scenario,
                        "commands": list(s.commands),
                        "notes": s.notes,
                    }
                    for s in self.remediation_steps
                ],
                "execution_policy": _EXECUTION_POLICY,
            }
        )
        return result


class RCSEngine:
    """Phase 1 skeleton. Real pattern matchers plug in via register_matcher()."""

    def __init__(self, registry: KCRegistry | None = None) -> None:
        self._registry = registry or KCRegistry()
        self._matchers: list[Any] = []

    def register_matcher(self, matcher: Any) -> None:
        self._matchers.append(matcher)

    def analyze(self, raw_data: dict[str, Any], mq_version: str | None = None) -> list[RCSFinding]:
        findings: list[RCSFinding] = []
        for matcher in self._matchers:
            result = matcher(raw_data, self._registry, mq_version)
            if result:
                findings.extend(result)
        return findings

    @property
    def registry(self) -> KCRegistry:
        return self._registry
