"""The Agensi skill package builds and passes its submission checks."""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

_BUILD = Path(__file__).resolve().parents[2] / "packaging" / "agensi" / "build_skill.py"


def _builder():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("build_skill", _BUILD)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_skill_zip_builds_with_single_top_level_folder(tmp_path: Path) -> None:
    builder = _builder()
    archive = builder.build(tmp_path)  # runs check(): frontmatter, text-only, JSON, inventory
    names = zipfile.ZipFile(archive).namelist()
    assert {n.split("/")[0] for n in names} == {"ibm-mq-diagnostics"}
    assert "ibm-mq-diagnostics/SKILL.md" in names
    assert "ibm-mq-diagnostics/references/reason-codes.md" in names
    assert not any(n.endswith(".DS_Store") for n in names)


def test_templates_pin_the_package_version(tmp_path: Path) -> None:
    builder = _builder()
    builder.build(tmp_path)
    claude = (tmp_path / "ibm-mq-diagnostics" / "templates" / "claude-code.mcp.json").read_text()
    assert f"mq-sentinel=={builder.package_version()}" in claude
