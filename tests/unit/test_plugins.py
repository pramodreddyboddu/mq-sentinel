"""Claude Code plugin manifests stay valid, in sync, and on the package version."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PLUGINS = _ROOT / "plugins"
_VERSION = tomllib.loads((_ROOT / "pyproject.toml").read_text())["project"]["version"]


def _json(path: Path) -> dict:  # type: ignore[type-arg]
    data: dict = json.loads(path.read_text())  # type: ignore[type-arg]
    return data


def test_marketplace_lists_every_plugin_at_package_version() -> None:
    market = _json(_ROOT / ".claude-plugin" / "marketplace.json")
    listed = {p["name"]: p for p in market["plugins"]}
    on_disk = {d.name for d in _PLUGINS.iterdir() if d.is_dir()}
    assert set(listed) == on_disk
    for name, entry in listed.items():
        assert (_ROOT / entry["source"]).resolve() == (_PLUGINS / name).resolve()
        assert entry["version"] == _VERSION
        manifest = _json(_PLUGINS / name / ".claude-plugin" / "plugin.json")
        assert manifest["name"] == name
        assert manifest["version"] == _VERSION


def test_local_plugin_pins_the_package_version() -> None:
    server = _json(_PLUGINS / "mq-sentinel" / ".mcp.json")["mcpServers"]["mq-sentinel"]
    assert f"mq-sentinel=={_VERSION}" in " ".join(server["args"])


def test_org_plugin_connects_over_http() -> None:
    server = _json(_PLUGINS / "mq-sentinel-org" / ".mcp.json")["mcpServers"]["mq-sentinel"]
    assert server == {"type": "http", "url": "${MQS_SENTINEL_URL}"}


@pytest.mark.parametrize(
    "rel",
    ["skills/mq-triage/SKILL.md", "commands/mq-health.md", "commands/mq-status.md"],
)
def test_org_plugin_shares_skill_and_commands(rel: str) -> None:
    local = (_PLUGINS / "mq-sentinel" / rel).read_text()
    org = (_PLUGINS / "mq-sentinel-org" / rel).read_text()
    assert org == local, f"plugins/mq-sentinel-org/{rel} drifted; copy it from plugins/mq-sentinel"
