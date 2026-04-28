"""diagnose_failed_channels — scan channel statuses, return RCS findings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mq_sentinel.connectors.base import MQConnector
from mq_sentinel.inventory.registry import InventoryRegistry
from mq_sentinel.rcs.engine import RCSFinding
from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.rcs.matchers.channels import match_channel_failures
from mq_sentinel.secrets.backend import SecretsBackend
from mq_sentinel.tools.base import ToolResponse, open_qm
from mq_sentinel.topology.detect import TopologyFingerprint

TOOL_NAME = "diagnose_failed_channels"

_LOG_TAIL_LIMIT = 200  # lines


@dataclass(frozen=True, slots=True)
class ChannelCheckResult:
    findings: tuple[RCSFinding, ...]
    raw_evidence: dict[str, Any]


def run_channel_checks(
    connector: MQConnector,
    fingerprint: TopologyFingerprint,
    registry: KCRegistry,
) -> ChannelCheckResult:
    """Internal helper: run all channel checks against an existing connector.

    Used by the standalone tool below AND by full_mq_health_check so the
    composite tool can run on a single connection.
    """
    channels = _collect_channel_status(connector)
    log_tail = _read_error_log_tail(connector)
    raw = {"channels": channels, "error_log_tail": log_tail}
    findings = match_channel_failures(raw, registry, mq_version=fingerprint.mq_version)
    return ChannelCheckResult(
        findings=tuple(findings),
        raw_evidence={
            "channels_examined": len(channels),
            "log_tail_lines": len(log_tail.splitlines()),
        },
    )


def diagnose_failed_channels(
    *,
    qm_name: str,
    connector_factory: Any,
    inventory: InventoryRegistry,
    secrets: SecretsBackend,
    kc_registry: KCRegistry | None = None,
) -> dict[str, Any]:
    """Scan all channels for failures and return RCS findings.

    The tool itself executes only DISPLAY commands — the security allowlist
    rejects anything else. Recommended fixes are returned as text only;
    nothing is executed on behalf of the user.
    """
    registry = kc_registry or KCRegistry()

    with open_qm(
        qm_name,
        connector_factory=connector_factory,
        inventory=inventory,
        secrets=secrets,
    ) as (connector, _entry, fingerprint):
        result = run_channel_checks(connector, fingerprint, registry)
        return ToolResponse(
            tool=TOOL_NAME,
            qm_name=qm_name,
            topology=fingerprint,
            findings=result.findings,
            raw_evidence=result.raw_evidence,
        ).to_dict()


def _collect_channel_status(connector: MQConnector) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        result = connector.execute_mqsc("DISPLAY CHSTATUS(*) ALL")
    except Exception:  # noqa: BLE001 — best-effort, partial diagnostics still useful
        return rows
    rows.extend(result.rows)
    return rows


def _read_error_log_tail(connector: MQConnector) -> str:
    """Best-effort error-log read. Phase 1 sources from MQSC log helpers; the
    full log-file path-allowlist reader lands when we add the log connector.
    """
    try:
        result = connector.execute_mqsc("DISPLAY QMSTATUS")
    except Exception:  # noqa: BLE001
        return ""
    lines = (result.raw or "").splitlines()[-_LOG_TAIL_LIMIT:]
    return "\n".join(lines)
