"""Topology auto-detection. Read-only — relies on DISPLAY queries + dspmq."""

from mq_sentinel.topology.detect import TopologyDetector, TopologyFingerprint

__all__ = ["TopologyDetector", "TopologyFingerprint"]
