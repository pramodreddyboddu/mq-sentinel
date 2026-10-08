"""Filesystem-mounted secrets backend (K8s Secrets / Docker secrets compatible).

Secret ref format: a relative directory under the mount root. Expected files:
  - username
  - password
  - keystore_path       (optional)
  - keystore_password   (optional)
  - cert_label          (optional)
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from mq_sentinel.secrets.backend import MQCredential


class FilesystemSecrets:
    def __init__(self, mount_root: Path) -> None:
        self._root = mount_root.resolve()
        if not self._root.exists():
            raise FileNotFoundError(f"secrets mount {self._root} does not exist")

    def resolve(self, secret_ref: str) -> MQCredential:
        if ".." in secret_ref.split("/") or secret_ref.startswith("/"):
            raise ValueError("invalid secret_ref (path traversal)")
        target = (self._root / secret_ref).resolve()
        if not str(target).startswith(str(self._root) + os.sep) and target != self._root:
            raise ValueError("secret_ref escapes mount root")
        if not target.is_dir():
            raise FileNotFoundError(f"secret directory {target} not found")

        self._check_permissions(target)

        user = self._read_required(target / "username")
        password = self._read_required(target / "password")
        keystore_path = self._read_optional(target / "keystore_path")
        keystore_password = self._read_optional(target / "keystore_password")
        cert_label = self._read_optional(target / "cert_label")

        return MQCredential(
            user=user,
            password=password,
            keystore_path=keystore_path,
            keystore_password=keystore_password,
            cert_label=cert_label,
        )

    @staticmethod
    def _read_required(path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(f"required secret file {path.name} missing")
        return path.read_text(encoding="utf-8").strip()

    @staticmethod
    def _read_optional(path: Path) -> str | None:
        if not path.exists():
            return None
        value = path.read_text(encoding="utf-8").strip()
        return value or None

    @staticmethod
    def _check_permissions(target: Path) -> None:
        mode = target.stat().st_mode
        if mode & (stat.S_IRWXO | stat.S_IWGRP):
            raise PermissionError(
                f"secret dir {target} has unsafe permissions: "
                f"must not be world-readable or group-writable"
            )
