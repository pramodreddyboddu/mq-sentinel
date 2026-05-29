"""Structural-validity tests for the KC registry (offline — runs in normal CI).

These assert the *shape* of every URL without hitting the network. The live
dead-link check lives in scripts/verify_kc_links.py + a scheduled workflow.
Together: this test catches malformed URLs on every PR; the scheduled job
catches IBM doc reorganizations daily.
"""

from __future__ import annotations

import re

import pytest

from mq_sentinel.rcs.kc_registry import KCRegistry

_registry = KCRegistry()
_ALL = _registry.all_refs()

# IBM doc URLs all look like:
#   https://www.ibm.com/docs/en/ibm-mq/<version>?topic=<slug>
_URL_SHAPE = re.compile(r"^https://www\.ibm\.com/docs/en/ibm-mq/\d+\.\d+\?topic=[a-z0-9-]+$")
# Reason-code slugs are deterministic: codes-<dec>-<hex4>-rc<dec>-mqrc-<name>
_REASON_SLUG = re.compile(r"topic=codes-(\d+)-[0-9a-f]{4}-rc(\d+)-mqrc-[a-z0-9-]+$")
# AMQ message slugs: messages-amq<nnnn><letter>
_AMQ_SLUG = re.compile(r"topic=messages-amq\d{4}[a-z]$")


def test_registry_is_not_empty() -> None:
    assert len(_ALL) >= 30, "registry shrank unexpectedly"


@pytest.mark.parametrize("ref", _ALL, ids=lambda r: r.url)
def test_every_url_is_https_ibm(ref) -> None:
    assert ref.url.startswith("https://www.ibm.com/docs/en/ibm-mq/"), ref.url
    assert _URL_SHAPE.match(ref.url), f"malformed IBM doc URL: {ref.url}"


@pytest.mark.parametrize("ref", _ALL, ids=lambda r: r.url)
def test_every_ref_has_title_and_versions(ref) -> None:
    assert ref.title.strip(), f"empty title for {ref.url}"
    assert ref.mq_versions, f"no mq_versions for {ref.url}"
    for v in ref.mq_versions:
        assert re.match(r"^\d+\.\d+$", v), f"bad version {v!r} for {ref.url}"


def test_reason_code_slugs_match_the_canonical_pattern() -> None:
    """Every reason-code URL's slug must encode the same code it's keyed under.

    This catches copy-paste errors like keying 2059 to the 2058 slug.
    """
    for code in _registry.reason_codes():
        for ref in _registry.lookup_reason(code):
            m = _REASON_SLUG.search(ref.url)
            assert m, f"reason {code} URL not in canonical form: {ref.url}"
            slug_dec, slug_rc = int(m.group(1)), int(m.group(2))
            assert slug_dec == code, f"reason {code} URL encodes {slug_dec}: {ref.url}"
            assert slug_rc == code, f"reason {code} URL rc encodes {slug_rc}: {ref.url}"


def test_amq_slugs_match_the_code() -> None:
    for code in _registry.amq_codes():
        for ref in _registry.lookup_amq(code):
            assert _AMQ_SLUG.search(ref.url), f"AMQ {code} URL not canonical: {ref.url}"
            # The 4-digit number in the slug must match the code's digits.
            digits = re.sub(r"\D", "", code)
            assert digits in ref.url, f"AMQ {code} digits not in URL: {ref.url}"


def test_no_duplicate_urls_across_buckets() -> None:
    urls = [r.url for r in _ALL]
    assert len(urls) == len(set(urls)), "duplicate URLs in registry"


def test_coverage_floor() -> None:
    """Lock in the breadth we've built so a regression that drops codes fails CI."""
    assert len(_registry.reason_codes()) >= 20, _registry.reason_codes()
    assert len(_registry.amq_codes()) >= 7, _registry.amq_codes()
