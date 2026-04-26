"""Topology auto-detection.

Strategy:
1. DISPLAY QMGR + DISPLAY QMSTATUS — gives version, platform, HA flags.
2. dspmq -o installation -o standby — multi-instance + install info.
3. DISPLAY CLUSQMGR(*) — cluster membership / uniform cluster heuristics.
4. Best-effort signals; never fails the request — falls back to UNKNOWN.

All commands routed through the security allowlist via the connector.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mq_sentinel.connectors.base import MQConnector
from mq_sentinel.inventory.models import Topology
from mq_sentinel.telemetry import get_logger

_log = get_logger("mq_sentinel.topology")


@dataclass(frozen=True, slots=True)
class TopologyFingerprint:
    topology: Topology
    mq_version: str | None
    platform: str | None
    is_zos: bool = False
    is_clustered: bool = False
    is_uniform_cluster: bool = False
    has_standby: bool = False
    is_native_ha: bool = False
    is_rdqm: bool = False
    evidence: dict[str, str] = field(default_factory=dict)


class TopologyDetector:
    def __init__(self, connector: MQConnector) -> None:
        self._connector = connector

    def detect(self) -> TopologyFingerprint:
        version = self._safe_attr("DISPLAY QMGR VERSION", "VERSION")
        platform = self._safe_attr("DISPLAY QMGR PLATFORM", "PLATFORM")
        qmstatus_raw = self._safe_raw("DISPLAY QMSTATUS")

        is_zos = (platform or "").upper().startswith("MVS") or "ZOS" in (platform or "").upper()
        is_native_ha = "NATIVEHA" in qmstatus_raw.upper() or "INSYNC" in qmstatus_raw.upper()
        is_rdqm = self._shell_indicates_rdqm()
        has_standby = self._dspmq_indicates_standby()

        clusqmgr_raw = self._safe_raw("DISPLAY CLUSQMGR(*) CLUSTER")
        is_clustered = bool(clusqmgr_raw.strip())
        is_uniform_cluster = "UNIFORM" in clusqmgr_raw.upper()

        topology = self._classify(
            is_zos=is_zos,
            is_native_ha=is_native_ha,
            is_rdqm=is_rdqm,
            has_standby=has_standby,
            is_clustered=is_clustered,
            is_uniform_cluster=is_uniform_cluster,
        )

        evidence = {
            "version_query": version or "",
            "platform_query": platform or "",
            "qmstatus_present": str(bool(qmstatus_raw)),
            "clusqmgr_present": str(is_clustered),
        }

        return TopologyFingerprint(
            topology=topology,
            mq_version=version,
            platform=platform,
            is_zos=is_zos,
            is_clustered=is_clustered,
            is_uniform_cluster=is_uniform_cluster,
            has_standby=has_standby,
            is_native_ha=is_native_ha,
            is_rdqm=is_rdqm,
            evidence=evidence,
        )

    # --- helpers ----------------------------------------------------------

    def _safe_attr(self, command: str, attr: str) -> str | None:
        try:
            result = self._connector.execute_mqsc(command)
        except Exception as exc:  # noqa: BLE001 — best-effort
            _log.debug("topology_query_failed", command=command, error=str(exc))
            return None
        for row in result.rows:
            if attr in row:
                return row[attr]
        return None

    def _safe_raw(self, command: str) -> str:
        try:
            return self._connector.execute_mqsc(command).raw
        except Exception:  # noqa: BLE001 — best-effort
            return ""

    def _shell_indicates_rdqm(self) -> bool:
        try:
            out = self._connector.execute_shell(["rdqmstatus"])
        except Exception:  # noqa: BLE001
            return False
        return "Node:" in out or "DRBD" in out.upper()

    def _dspmq_indicates_standby(self) -> bool:
        try:
            out = self._connector.execute_shell(["dspmq", "-o", "standby"])
        except Exception:  # noqa: BLE001
            return False
        return "PERMITTED" in out.upper() or "STANDBY" in out.upper()

    @staticmethod
    def _classify(
        *,
        is_zos: bool,
        is_native_ha: bool,
        is_rdqm: bool,
        has_standby: bool,
        is_clustered: bool,
        is_uniform_cluster: bool,
    ) -> Topology:
        if is_zos:
            return Topology.ZOS_QSG
        if is_native_ha:
            return Topology.NATIVE_HA
        if is_rdqm:
            return Topology.RDQM
        if has_standby:
            return Topology.MULTI_INSTANCE
        if is_uniform_cluster:
            return Topology.UNIFORM_CLUSTER
        if is_clustered:
            return Topology.TRADITIONAL_CLUSTER
        return Topology.STANDALONE
