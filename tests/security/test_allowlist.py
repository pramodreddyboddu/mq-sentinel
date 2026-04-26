"""Negative-test corpus for the MQSC/shell command allowlist.

EVERY destructive or obfuscated command below MUST be rejected.
A single passing destructive command is a P0 security bug.
"""

from __future__ import annotations

import pytest

from mq_sentinel.security.allowlist import (
    CommandNotAllowedError,
    assert_mqsc_allowed,
    assert_shell_allowed,
)

pytestmark = pytest.mark.security


ALLOWED_MQSC = [
    "DISPLAY QMSTATUS",
    "DIS QMGR",
    "DISPLAY CHSTATUS(*)",
    "DISPLAY QUEUE(*) CURDEPTH MAXDEPTH",
    "DISPLAY CLUSQMGR(*)",
    "PING CHANNEL(APP.SVRCONN)",
]


DENIED_MQSC = [
    "",
    "   ",
    "ALTER QMGR",
    "DELETE QUEUE(Q1)",
    "START CHANNEL(FOO)",
    "STOP CHANNEL(FOO)",
    "DEFINE QLOCAL(Q1)",
    "REFRESH CLUSTER",
    "RESET QMGR",
    "CLEAR QLOCAL(Q1)",
    "SET AUTHREC",
    "DISPLAY QMGR;ALTER QMGR",  # multi-statement via semicolon
    "DISPLAY QMGR\nALTER QMGR",  # multi-statement via newline
    "DISPLAY QMGR\r\nDELETE QUEUE(Q)",  # CRLF
    "DISPLAY QMGR\x00ALTER QMGR",  # NUL injection
    "* fake comment\nALTER QMGR",  # comment strip should still leave ALTER
    "alter qmgr",  # case obfuscation
    "Alter Qmgr",
    "PING QMGR",  # PING only allowed as PING CHANNEL
    "FOO BAR",  # unknown verb
]


@pytest.mark.parametrize("cmd", ALLOWED_MQSC)
def test_mqsc_allowlist_accepts_readonly(cmd: str) -> None:
    assert_mqsc_allowed(cmd)


@pytest.mark.parametrize("cmd", DENIED_MQSC)
def test_mqsc_allowlist_rejects_destructive_or_malformed(cmd: str) -> None:
    with pytest.raises(CommandNotAllowedError):
        assert_mqsc_allowed(cmd)


def test_shell_allowlist_accepts_dspmq() -> None:
    assert_shell_allowed(["dspmq"])
    assert_shell_allowed(["dspmq", "-m", "-o", "status"])


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["rm", "-rf", "/"],
        ["bash", "-c", "id"],
        ["dspmq", "; rm -rf /"],
        ["dspmq", "|", "cat"],
        ["dspmq", "&&", "echo", "pwn"],
        ["dspmq", "$(id)"],
        ["crm_mon", "--unsafe-arg"],
    ],
)
def test_shell_allowlist_rejects_dangerous(argv: list[str]) -> None:
    with pytest.raises(CommandNotAllowedError):
        assert_shell_allowed(argv)
