"""Security guarantee: DLQ browse never returns message bodies."""

from __future__ import annotations

import inspect

import pytest

from mq_sentinel.connectors.base import BrowseResult, DLQHeader

pytestmark = pytest.mark.security


def test_dlqheader_dataclass_has_no_body_field() -> None:
    field_names = set(DLQHeader.__dataclass_fields__)
    forbidden = {"body", "payload", "message_body", "data", "content", "raw_body"}
    assert forbidden.isdisjoint(field_names), (
        f"DLQHeader exposes body-like fields: {forbidden & field_names}"
    )


def test_browseresult_only_carries_headers() -> None:
    fields = set(BrowseResult.__dataclass_fields__)
    assert "headers" in fields
    assert "bodies" not in fields
    assert "payloads" not in fields


def test_pymqi_browse_dlq_zeroes_message_buffer() -> None:
    """Source-level guarantee: the pymqi connector deletes raw_msg before
    appending to headers. Anyone who refactors this needs to keep that
    property — the test reads source to enforce it."""
    from mq_sentinel.connectors import pymqi_connector

    src = inspect.getsource(pymqi_connector.PymqiConnector.browse_dlq)
    assert "del raw_msg" in src, (
        "browse_dlq must delete the raw message buffer before storing headers"
    )
    # And must not return raw bytes anywhere in its flow
    assert "raw_msg" not in src.split("return ")[-1], "browse_dlq must not return raw_msg"
