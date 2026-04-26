"""Common tool plumbing: response envelope + connector context manager."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from mq_sentinel.connectors.base import MQConnector
from mq_sentinel.inventory.models import QMEntry
from mq_sentinel.inventory.registry import InventoryRegistry
from mq_sentinel.rcs.engine import RCSFinding
from mq_sentinel.secrets.backend import SecretsBackend
from mq_sentinel.security.sanitizer import sanitize_mq_output
from mq_sentinel.topology.detect import TopologyDetector, TopologyFingerprint


@dataclass(frozen=True, slots=True)
class ToolResponse:
    tool: str
    qm_name: str
    topology: TopologyFingerprint
    findings: tuple[RCSFinding, ...]
    raw_evidence: dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = sanitize_mq_output(
            {
                "tool": self.tool,
                "qm_name": self.qm_name,
                "topology": {
                    "topology": self.topology.topology.value,
                    "mq_version": self.topology.mq_version,
                    "platform": self.topology.platform,
                    "is_clustered": self.topology.is_clustered,
                    "is_native_ha": self.topology.is_native_ha,
                    "is_rdqm": self.topology.is_rdqm,
                    "has_standby": self.topology.has_standby,
                    "evidence": self.topology.evidence,
                },
                "findings": [f.as_dict() for f in self.findings],
                "raw_evidence": self.raw_evidence,
                "generated_at": self.generated_at,
                "trust_level": "rcs_findings",
            }
        )
        return result


@contextmanager
def open_qm(
    qm_name: str,
    *,
    connector_factory: Any,
    inventory: InventoryRegistry,
    secrets: SecretsBackend,
) -> Iterator[tuple[MQConnector, QMEntry, TopologyFingerprint]]:
    """Connect, detect topology, yield (connector, entry, fingerprint), disconnect."""
    entry = inventory.get(qm_name)
    credential = secrets.resolve(entry.secret_ref)
    connector: MQConnector = connector_factory()
    connector.connect(entry, credential)
    try:
        fingerprint = TopologyDetector(connector).detect()
        yield connector, entry, fingerprint
    finally:
        connector.disconnect()
