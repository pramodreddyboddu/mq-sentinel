"""Build the Agensi skill zip: dist/agensi/ibm-mq-diagnostics-<version>.zip.

    uv run python packaging/agensi/build_skill.py

Stages packaging/agensi/ibm-mq-diagnostics/, fills in {{VERSION}}, generates
references/reason-codes.md from the server's own (CI-verified) IBM doc
registry, checks the result against Agensi's submission rules, and zips it as
a single top-level folder.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tomllib
import zipfile
from pathlib import Path

import yaml

from mq_sentinel.inventory.models import QMEntry
from mq_sentinel.rcs.kc_registry import KCRegistry

ROOT = Path(__file__).resolve().parents[2]
SKILL = "ibm-mq-diagnostics"
SOURCE = Path(__file__).resolve().parent / SKILL

# Things Agensi's scan rejects, or that would only be leftovers here.
_FORBIDDEN_NAMES = {".DS_Store", "Thumbs.db"}
_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"),  # JWT
    re.compile(r"\b(?:AKIA|ghp_|gho_|github_pat_|sk-)[A-Za-z0-9_]{16,}"),
]


def package_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    version: str = data["project"]["version"]
    return version


def reason_codes_markdown() -> str:
    reg = KCRegistry()
    lines = [
        "# Reason codes, AMQ messages and topics MQ-Sentinel cites",
        "",
        "Generated from MQ-Sentinel's documentation registry. Every link is an IBM",
        "Documentation page, checked daily in MQ-Sentinel's CI. Findings carry these",
        "links in `doc_refs`: quote them as returned.",
        "",
        "## MQ reason codes (MQRC)",
        "",
        "| Code | IBM documentation |",
        "|---|---|",
    ]
    for code in reg.reason_codes():
        for ref in reg.lookup_reason(code):
            lines.append(f"| {code} | [{ref.title}]({ref.url}) |")
    lines += ["", "## AMQ messages", "", "| Message | IBM documentation |", "|---|---|"]
    for code in reg.amq_codes():
        for ref in reg.lookup_amq(code):
            lines.append(f"| {code} | [{ref.title}]({ref.url}) |")
    lines += ["", "## Topics", "", "| Topic | IBM documentation |", "|---|---|"]
    for topic in sorted(reg._topics):
        for ref in reg.lookup_topic(topic):
            lines.append(f"| `{topic}` | [{ref.title}]({ref.url}) |")
    lines += [
        "",
        "## Connection errors you may see from MQ-Sentinel itself",
        "",
        "| Message | Meaning |",
        "|---|---|",
        "| `failed to connect ... (MQRC 2035)` "
        "| MQ-Sentinel's MQ user or CHLAUTH rule doesn't allow it in |",
        "| `(MQRC 2059)` / `(MQRC 2538)` "
        "| Queue manager or listener unreachable (host, port, firewall, listener) |",
        "| `(MQRC 2393)` / `(MQRC 2397)` "
        "| TLS problem: CipherSpec mismatch, key repository or certificate label |",
        "",
    ]
    return "\n".join(lines)


def stage(out_dir: Path, version: str) -> Path:
    staged = out_dir / SKILL
    if staged.exists():
        shutil.rmtree(staged)
    for src in sorted(SOURCE.rglob("*")):
        if src.is_dir() or src.name in _FORBIDDEN_NAMES:
            continue
        dest = staged / src.relative_to(SOURCE)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text(encoding="utf-8").replace("{{VERSION}}", version))
    (staged / "references" / "reason-codes.md").write_text(reason_codes_markdown())
    return staged


def check(staged: Path) -> None:
    """Fail loudly on anything Agensi's review would reject."""
    skill_md = (staged / "SKILL.md").read_text()
    match = re.match(r"^---\n(.*?)\n---\n(.+)", skill_md, re.DOTALL)
    if not match:
        raise SystemExit("SKILL.md needs YAML frontmatter followed by instructions")
    front = yaml.safe_load(match.group(1))
    if front.get("name") != SKILL or not str(front.get("description", "")).startswith("Use when"):
        raise SystemExit("frontmatter needs name == folder and a 'Use when ...' description")

    for path in staged.rglob("*"):
        if path.is_symlink():
            raise SystemExit(f"symlink not allowed: {path}")
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")  # raises on binary content
        if "{{VERSION}}" in text:
            raise SystemExit(f"unfilled placeholder in {path}")
        for pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                raise SystemExit(f"possible secret in {path}")
        if path.suffix == ".json":
            json.loads(text)

    inventory = yaml.safe_load((staged / "templates" / "inventory.yaml").read_text())
    for item in inventory["qms"]:
        QMEntry(**item)  # the template must load on the real server


def build(out_dir: Path) -> Path:
    version = package_version()
    out_dir.mkdir(parents=True, exist_ok=True)
    staged = stage(out_dir, version)
    check(staged)
    archive = out_dir / f"{SKILL}-{version}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(staged.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(out_dir).as_posix())
    return archive


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "agensi"
    print(build(target))
