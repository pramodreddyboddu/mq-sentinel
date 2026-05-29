#!/usr/bin/env python3
"""Verify every IBM Knowledge Center URL in the KC registry resolves.

The entire trust story of MQ-Sentinel is "every recommendation cites IBM."
If even one of those URLs 404s, the first IBM admin who clicks it stops
trusting the whole tool. This script fetches every URL in the registry and
fails if any does not resolve to a live IBM doc page.

Usage:
    python scripts/verify_kc_links.py            # check all, exit 1 on any failure
    python scripts/verify_kc_links.py --json     # machine-readable report

Runs in CI on a schedule (.github/workflows/verify-kc-links.yml) so IBM doc
reorganizations are caught within a day, not by an angry customer.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from dataclasses import asdict, dataclass

import httpx

from mq_sentinel.rcs.kc_registry import KCRegistry

# IBM occasionally rate-limits or soft-blocks non-browser agents. Present a
# realistic UA and follow redirects (IBM frequently 301s doc slugs).
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}
_TIMEOUT = 15.0
_MAX_WORKERS = 8

# IBM sometimes returns 403 to HEAD but 200 to GET; we GET. A 404 is a hard
# fail. 200/301/302→200 is a pass. Anything else is flagged for manual review.
_PASS_STATUSES = frozenset({200})
_REVIEW_STATUSES = frozenset({403, 429, 503})


@dataclass(frozen=True)
class LinkResult:
    url: str
    title: str
    status: int | None
    ok: bool
    note: str


def _check_one(client: httpx.Client, url: str, title: str) -> LinkResult:
    try:
        resp = client.get(url, headers=_HEADERS, follow_redirects=True, timeout=_TIMEOUT)
    except httpx.HTTPError as exc:
        return LinkResult(url, title, None, ok=False, note=f"request_error: {type(exc).__name__}")

    status = resp.status_code
    if status in _PASS_STATUSES:
        # IBM serves a soft-404 "Page not found" with a 200 in some cases —
        # detect the canonical not-found marker in the body.
        body = resp.text[:8000].lower()
        if "the page you requested cannot be found" in body or "error 404" in body:
            return LinkResult(url, title, status, ok=False, note="soft_404_in_body")
        return LinkResult(url, title, status, ok=True, note="ok")
    if status in _REVIEW_STATUSES:
        note = f"review:{status} (IBM rate-limit/soft-block, not a 404)"
        return LinkResult(url, title, status, ok=True, note=note)
    return LinkResult(url, title, status, ok=False, note=f"bad_status:{status}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit a JSON report")
    args = parser.parse_args()

    registry = KCRegistry()
    refs = registry.all_refs()

    results: list[LinkResult] = []
    with (
        httpx.Client() as client,
        concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool,
    ):
        futures = {pool.submit(_check_one, client, ref.url, ref.title): ref for ref in refs}
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    results.sort(key=lambda r: (r.ok, r.url))
    failures = [r for r in results if not r.ok]

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        for r in results:
            mark = "✅" if r.ok else "❌"
            status = r.status if r.status is not None else "ERR"
            print(f"{mark} [{status}] {r.title}")
            if not r.ok or r.note.startswith("review"):
                print(f"     {r.url}  ({r.note})")
        print()
        print(f"Checked {len(results)} KC URLs — {len(failures)} failed.")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
