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
from mq_sentinel.tools.miqm import TOOL_NAME as MIQM_TOOL_NAME
from mq_sentinel.tools.miqm import diagnose_multi_instance_issues
from mq_sentinel.tools.native_ha import TOOL_NAME as NATIVE_HA_TOOL_NAME
from mq_sentinel.tools.native_ha import diagnose_native_ha_issues
from mq_sentinel.tools.rdqm import TOOL_NAME as RDQM_TOOL_NAME
from mq_sentinel.tools.rdqm import diagnose_rdqm_issues
from mq_sentinel.tools.zos import TOOL_NAME as ZOS_TOOL_NAME
from mq_sentinel.tools.zos import diagnose_zos_qsg_issues

__all__ = [
    "CHANNELS_TOOL_NAME",
    "CLUSTER_TOOL_NAME",
    "DLQ_TOOL_NAME",
    "HEALTH_CHECK_TOOL_NAME",
    "MIQM_TOOL_NAME",
    "NATIVE_HA_TOOL_NAME",
    "RDQM_TOOL_NAME",
    "ZOS_TOOL_NAME",
    "analyze_dlq",
    "check_cluster_health",
    "diagnose_failed_channels",
    "diagnose_multi_instance_issues",
    "diagnose_native_ha_issues",
    "diagnose_rdqm_issues",
    "diagnose_zos_qsg_issues",
    "full_mq_health_check",
]
