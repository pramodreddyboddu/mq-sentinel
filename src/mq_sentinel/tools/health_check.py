"""full_mq_health_check — composite read-only health assessment.

Runs every Phase 1 diagnostic against a single connection, aggregates RCS
findings across categories, ranks by severity, and produces an executive
summary the AI client can present at a glance.

Topology-aware: cluster checks run regardless (matchers no-op on empty data),
but the response calls out which categories actually contributed findings.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from mq_sentinel.connectors.base import MQConnector
from mq_sentinel.inventory.registry import InventoryRegistry
from mq_sentinel.rcs.engine import RCSFinding, Severity
from mq_sentinel.rcs.kc_registry import KCRegistry
from mq_sentinel.secrets.backend import SecretsBackend
from mq_sentinel.security.sanitizer import sanitize_mq_output
from mq_sentinel.tools.base import open_qm
from mq_sentinel.tools.channels import run_channel_checks
from mq_sentinel.tools.cluster import run_cluster_checks
from mq_sentinel.tools.dlq import run_dlq_checks
from mq_sentinel.topology.detect import TopologyFingerprint

TOOL_NAME = "full_mq_health_check"

_SEVERITY_RANK: dict[str, int] = {
    Severity.CRITICAL.value: 0,
    Severity.HIGH.value: 1,
    Severity.MEDIUM.value: 2,
    Severity.LOW.value: 3,
    Severity.INFO.value: 4,
}

_CATEGORY_RANK: dict[str, int] = {"channels": 0, "dlq": 1, "cluster": 2}


def full_mq_health_check(
    *,
    qm_name: str,
    connector_factory: Any,
    inventory: InventoryRegistry,
    secrets: SecretsBackend,
    dlq_sample_size: int = 50,
    kc_registry: KCRegistry | None = None,
) -> dict[str, Any]:
    """Run all Phase 1 checks against a single QM connection.

    Returns a sanitized JSON envelope with:
      - executive summary (counts per severity + per category, top issues)
      - sorted findings (severity then category)
      - raw_evidence per category (so the AI can cite numbers)
      - checks_run / checks_skipped lists
    """
    registry = kc_registry or KCRegistry()
    started = datetime.now(UTC)
    checks_run: list[str] = []
    checks_skipped: list[dict[str, str]] = []

    with open_qm(
        qm_name,
        connector_factory=connector_factory,
        inventory=inventory,
        secrets=secrets,
    ) as (connector, _entry, fingerprint):
        all_findings: list[tuple[str, RCSFinding]] = []
        category_evidence: dict[str, dict[str, Any]] = {}

        # Channels
        channel_findings, channel_evidence = _safe_run(
            "channels",
            lambda: _run_channels(connector, fingerprint, registry),
            checks_run,
            checks_skipped,
        )
        if channel_evidence is not None:
            category_evidence["channels"] = channel_evidence
            all_findings.extend(("channels", f) for f in channel_findings)

        # DLQ
        dlq_findings, dlq_evidence = _safe_run(
            "dlq",
            lambda: _run_dlq(connector, fingerprint, registry, dlq_sample_size),
            checks_run,
            checks_skipped,
        )
        if dlq_evidence is not None:
            category_evidence["dlq"] = dlq_evidence
            all_findings.extend(("dlq", f) for f in dlq_findings)

        # Cluster
        cluster_findings, cluster_evidence = _safe_run(
            "cluster",
            lambda: _run_cluster(connector, fingerprint, registry, qm_name),
            checks_run,
            checks_skipped,
        )
        if cluster_evidence is not None:
            category_evidence["cluster"] = cluster_evidence
            all_findings.extend(("cluster", f) for f in cluster_findings)

    sorted_findings = sorted(all_findings, key=_finding_sort_key)
    summary = _build_summary(sorted_findings)
    duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)

    response: dict[str, Any] = {
        "tool": TOOL_NAME,
        "qm_name": qm_name,
        "topology": _topology_to_dict(fingerprint),
        "summary": summary,
        "findings": [
            {**finding.as_dict(), "category": category} for category, finding in sorted_findings
        ],
        "raw_evidence": category_evidence,
        "checks_run": checks_run,
        "checks_skipped": checks_skipped,
        "duration_ms": duration_ms,
        "generated_at": started.isoformat(),
        "trust_level": "rcs_findings",
    }
    sanitized: dict[str, Any] = sanitize_mq_output(response)
    return sanitized


# --- internal runners -------------------------------------------------------


def _run_channels(
    connector: MQConnector,
    fingerprint: TopologyFingerprint,
    registry: KCRegistry,
) -> tuple[tuple[RCSFinding, ...], dict[str, Any]]:
    result = run_channel_checks(connector, fingerprint, registry)
    return result.findings, result.raw_evidence


def _run_dlq(
    connector: MQConnector,
    fingerprint: TopologyFingerprint,
    registry: KCRegistry,
    sample_size: int,
) -> tuple[tuple[RCSFinding, ...], dict[str, Any]]:
    result = run_dlq_checks(connector, fingerprint, registry, sample_size)
    return result.findings, result.raw_evidence


def _run_cluster(
    connector: MQConnector,
    fingerprint: TopologyFingerprint,
    registry: KCRegistry,
    qm_name: str,
) -> tuple[tuple[RCSFinding, ...], dict[str, Any]]:
    result = run_cluster_checks(connector, fingerprint, registry, fallback_qm_name=qm_name)
    return result.findings, result.raw_evidence


def _safe_run(
    name: str,
    fn: Any,
    checks_run: list[str],
    checks_skipped: list[dict[str, str]],
) -> tuple[tuple[RCSFinding, ...], dict[str, Any] | None]:
    try:
        findings, evidence = fn()
    except Exception as exc:  # noqa: BLE001 — composite must not fail whole tool on one bad check
        checks_skipped.append({"category": name, "error": type(exc).__name__})
        return ((), None)
    checks_run.append(name)
    return (findings, evidence)


# --- helpers ----------------------------------------------------------------


def _finding_sort_key(item: tuple[str, RCSFinding]) -> tuple[int, int, str]:
    category, f = item
    return (
        _SEVERITY_RANK.get(f.severity.value, 99),
        _CATEGORY_RANK.get(category, 99),
        f.issue,
    )


def _build_summary(sorted_findings: list[tuple[str, RCSFinding]]) -> dict[str, Any]:
    by_severity: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    for category, f in sorted_findings:
        by_severity[f.severity.value] += 1
        by_category[category] += 1

    top: list[dict[str, str]] = []
    for category, f in sorted_findings[:5]:
        top.append(
            {
                "severity": f.severity.value,
                "category": category,
                "issue": f.issue,
            }
        )

    overall = (
        "CRITICAL"
        if by_severity.get("CRITICAL")
        else "HIGH"
        if by_severity.get("HIGH")
        else "MEDIUM"
        if by_severity.get("MEDIUM")
        else "LOW"
        if by_severity.get("LOW")
        else "OK"
    )

    return {
        "total_findings": sum(by_severity.values()),
        "overall_status": overall,
        "by_severity": {sev: by_severity.get(sev, 0) for sev in _SEVERITY_RANK},
        "by_category": {cat: by_category.get(cat, 0) for cat in _CATEGORY_RANK},
        "top_issues": top,
    }


def _topology_to_dict(t: TopologyFingerprint) -> dict[str, Any]:
    return {
        "topology": t.topology.value,
        "mq_version": t.mq_version,
        "platform": t.platform,
        "is_clustered": t.is_clustered,
        "is_native_ha": t.is_native_ha,
        "is_rdqm": t.is_rdqm,
        "has_standby": t.has_standby,
        "evidence": t.evidence,
    }
