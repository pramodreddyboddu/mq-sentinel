"""Filesystem secrets: K8s-style mounts work, leaky permissions are refused."""

from __future__ import annotations

from pathlib import Path

import pytest

from mq_sentinel.secrets.filesystem import FilesystemSecrets

pytestmark = pytest.mark.security


def _secret(root: Path, *, dir_mode: int, file_mode: int) -> None:
    d = root / "prod" / "qm1"
    d.mkdir(parents=True)
    (d / "username").write_text("mqs\n")
    (d / "password").write_text("pw\n")
    for f in d.iterdir():
        f.chmod(file_mode)
    d.chmod(dir_mode)


def test_k8s_secret_volume_layout_is_accepted(tmp_path: Path) -> None:
    _secret(tmp_path, dir_mode=0o755, file_mode=0o400)
    cred = FilesystemSecrets(tmp_path).resolve("prod/qm1")
    assert cred.user == "mqs"
    assert "pw" not in repr(cred)


@pytest.mark.parametrize("file_mode", [0o644, 0o604, 0o620])
def test_world_readable_or_group_writable_file_refused(tmp_path: Path, file_mode: int) -> None:
    _secret(tmp_path, dir_mode=0o700, file_mode=file_mode)
    with pytest.raises(PermissionError, match="secret file"):
        FilesystemSecrets(tmp_path).resolve("prod/qm1")


@pytest.mark.parametrize("dir_mode", [0o777, 0o775])
def test_writable_secret_dir_refused(tmp_path: Path, dir_mode: int) -> None:
    _secret(tmp_path, dir_mode=dir_mode, file_mode=0o600)
    with pytest.raises(PermissionError, match="secret dir"):
        FilesystemSecrets(tmp_path).resolve("prod/qm1")


@pytest.mark.parametrize("ref", ["../etc", "/etc/passwd", "prod/../../x"])
def test_path_traversal_refused(tmp_path: Path, ref: str) -> None:
    _secret(tmp_path, dir_mode=0o700, file_mode=0o600)
    with pytest.raises(ValueError):
        FilesystemSecrets(tmp_path).resolve(ref)
