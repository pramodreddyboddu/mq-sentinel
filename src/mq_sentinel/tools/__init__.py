"""MCP tool implementations.

Phase 1:
- diagnose_failed_channels — channel health + RCS findings.
"""

from mq_sentinel.tools.channels import TOOL_NAME as CHANNELS_TOOL_NAME
from mq_sentinel.tools.channels import diagnose_failed_channels
from mq_sentinel.tools.cluster import TOOL_NAME as CLUSTER_TOOL_NAME
from mq_sentinel.tools.cluster import check_cluster_health
from mq_sentinel.tools.dlq import TOOL_NAME as DLQ_TOOL_NAME
from mq_sentinel.tools.dlq import analyze_dlq
from mq_sentinel.tools.health_check import TOOL_NAME as HEALTH_CHECK_TOOL_NAME
from mq_sentinel.tools.health_check import full_mq_health_check

__all__ = [
    "CHANNELS_TOOL_NAME",
    "CLUSTER_TOOL_NAME",
    "DLQ_TOOL_NAME",
    "HEALTH_CHECK_TOOL_NAME",
    "analyze_dlq",
    "check_cluster_health",
    "diagnose_failed_channels",
    "full_mq_health_check",
]
