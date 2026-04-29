"""Pattern matchers that turn raw MQ data into RCSFindings."""

from mq_sentinel.rcs.matchers.channels import match_channel_failures
from mq_sentinel.rcs.matchers.cluster import match_cluster_findings
from mq_sentinel.rcs.matchers.dlq import header_to_dict, match_dlq_findings
from mq_sentinel.rcs.matchers.native_ha import match_native_ha_findings

__all__ = [
    "header_to_dict",
    "match_channel_failures",
    "match_cluster_findings",
    "match_dlq_findings",
    "match_native_ha_findings",
]
