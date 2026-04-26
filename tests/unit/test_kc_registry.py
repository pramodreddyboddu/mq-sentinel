from __future__ import annotations

import pytest

from mq_sentinel.rcs.kc_registry import KCDocRef, KCRegistry


def test_lookup_reason_2035() -> None:
    refs = KCRegistry().lookup_reason(2035, mq_version="9.4.0")
    assert refs
    assert all("www.ibm.com" in r.url for r in refs)


def test_url_host_allowlist_enforced() -> None:
    with pytest.raises(ValueError):
        KCDocRef(title="evil", url="https://evil.example.com/x", mq_versions=("9.4",))


def test_lookup_amq9202() -> None:
    refs = KCRegistry().lookup_amq("AMQ9202")
    assert refs
