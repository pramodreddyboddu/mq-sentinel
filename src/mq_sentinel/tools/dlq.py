"""analyze_dlq_and_suggest_reprocessing — safe DLQ inspection.

This tool reads only DLQ HEADERS, never message bodies. The connector contract
guarantees this; the tool surface confirms it on every response.
"""

from __future__ import annotations

from typing import Any

from mq_sentinel.connectors.base import MQConnector
from mq_sentinel.inventory.registry import InventoryRegistry
from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.rcs.matchers.dlq import header_to_dict, match_dlq_findings
from mq_sentinel.secrets.backend import SecretsBackend
from mq_sentinel.tools.base import ToolResponse, open_qm

TOOL_NAME = "analyze_dlq_and_suggest_reprocessing"

_MAX_SAMPLE = 500
_DEFAULT_SAMPLE = 50


def analyze_dlq(
    *,
    qm_name: str,
    connector_factory: Any,
    inventory: InventoryRegistry,
    secrets: SecretsBackend,
    sample_size: int = _DEFAULT_SAMPLE,
    kc_registry: KCRegistry | None = None,
) -> dict[str, Any]:
    if sample_size < 1 or sample_size > _MAX_SAMPLE:
        raise ValueError(f"sample_size must be in [1, {_MAX_SAMPLE}]")
    registry = kc_registry or KCRegistry()

    with open_qm(
        qm_name,
        connector_factory=connector_factory,
        inventory=inventory,
        secrets=secrets,
    ) as (connector, _entry, fingerprint):
        dlq_name = _resolve_dlq_name(connector)
        browse = connector.browse_dlq(dlq_name, max_messages=sample_size)
        browse_dict = {
            "queue_name": browse.queue_name,
            "qm_name": browse.qm_name,
            "queue_depth": browse.queue_depth,
            "sample_size": browse.sample_size,
            "headers": [header_to_dict(h) for h in browse.headers],
        }
        findings = match_dlq_findings(browse_dict, registry, mq_version=fingerprint.mq_version)

        return ToolResponse(
            tool=TOOL_NAME,
            qm_name=qm_name,
            topology=fingerprint,
            findings=tuple(findings),
            raw_evidence={
                "dlq_name": browse.queue_name,
                "queue_depth": browse.queue_depth,
                "sample_size": browse.sample_size,
                "bodies_read": False,  # explicit: bodies are NEVER read
            },
        ).to_dict()


def _resolve_dlq_name(connector: MQConnector) -> str:
    """Resolve the DLQ name via DISPLAY QMGR DEADQ; fall back to SYSTEM default."""
    try:
        result = connector.execute_mqsc("DISPLAY QMGR DEADQ")
    except Exception:  # noqa: BLE001 — best-effort
        return "SYSTEM.DEAD.LETTER.QUEUE"
    for row in result.rows:
        if row.get("DEADQ"):
            return row["DEADQ"]
    return "SYSTEM.DEAD.LETTER.QUEUE"
