"""Pattern matchers that turn raw MQ data into RCSFindings."""

from mq_sentinel.rcs.matchers.channels import match_channel_failures

__all__ = ["match_channel_failures"]
