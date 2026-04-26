"""Connector protocol. All MQSC execution goes through assert_mqsc_allowed()."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from mq_sentinel.inventory.models import QMEntry
from mq_sentinel.secrets.backend import MQCredential


class MQConnectionError(RuntimeError):
    """Raised on MQ connection failures. Never leak credentials in the message."""


@dataclass(frozen=True, slots=True)
class MQSCResult:
    command: str
    rows: list[dict[str, str]] = field(default_factory=list)
    raw: str = ""
    reason_code: int | None = None
    completion_code: int | None = None


class MQConnector(Protocol):
    """Pluggable connector. Implementations: pymqi (real), fixture (tests/demo)."""

    def connect(self, entry: QMEntry, credential: MQCredential) -> None: ...
    def disconnect(self) -> None: ...
    def execute_mqsc(self, command: str) -> MQSCResult: ...
    def execute_shell(self, argv: Sequence[str]) -> str: ...
