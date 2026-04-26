"""RCS engine: builds hallucination-free findings from raw MQ data + KC registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from mq_sentinel.rcs.kc_registry import KCDocRef, KCRegistry
from mq_sentinel.security.sanitizer import sanitize_mq_output


class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass(frozen=True, slots=True)
class RCSFinding:
    issue: str
    severity: Severity
    reason_code: int | None
    amq_code: str | None
    root_cause: str
    fix_steps: tuple[str, ...]
    verify_commands: tuple[str, ...]
    doc_refs: tuple[KCDocRef, ...]
    confidence: str  # "High" | "Medium"
    evidence: dict[str, Any] = field(default_factory=dict)

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
