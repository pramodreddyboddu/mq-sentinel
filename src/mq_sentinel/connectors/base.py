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


@dataclass(frozen=True, slots=True)
class DLQHeader:
    """Safe DLQ header projection. NEVER contains the message body.

    Body length is reported, body content is not. msg_id_hash is a SHA-256
    hex digest of the original MsgId — sufficient for correlation, useless
    for impersonation.
    """

    reason_code: int
    feedback: int
    put_application_name: str
    put_application_type: str
    put_date: str  # YYYY-MM-DD
    put_time: str  # HH:MM:SS
    dest_q_name: str
    dest_q_mgr_name: str
    backout_count: int
    body_length: int
    msg_id_hash: str
    encoding: str | None = None
    coded_char_set_id: str | None = None


@dataclass(frozen=True, slots=True)
class BrowseResult:
    queue_name: str
    qm_name: str
    sample_size: int
    queue_depth: int
    headers: list[DLQHeader] = field(default_factory=list)


class MQConnector(Protocol):
    """Pluggable connector. Implementations: pymqi (real), fixture (tests/demo)."""

    def connect(self, entry: QMEntry, credential: MQCredential) -> None: ...
    def disconnect(self) -> None: ...
    def execute_mqsc(self, command: str) -> MQSCResult: ...
    def execute_shell(self, argv: Sequence[str]) -> str: ...
    def browse_dlq(self, queue_name: str, max_messages: int = 50) -> BrowseResult:
        """Read DLQ headers only (never bodies). Implementations MUST NOT
        return the message body content under any circumstance."""
