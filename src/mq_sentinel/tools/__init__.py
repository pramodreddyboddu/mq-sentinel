"""MCP tool implementations.

Phase 1:
- diagnose_failed_channels — channel health + RCS findings.
"""

from mq_sentinel.tools.channels import TOOL_NAME as CHANNELS_TOOL_NAME
from mq_sentinel.tools.channels import diagnose_failed_channels

__all__ = ["CHANNELS_TOOL_NAME", "diagnose_failed_channels"]
