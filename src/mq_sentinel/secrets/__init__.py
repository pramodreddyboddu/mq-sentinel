"""Pluggable secrets backend. Default: filesystem-mounted secrets (K8s Secrets)."""

from mq_sentinel.secrets.backend import MQCredential, SecretsBackend
from mq_sentinel.secrets.filesystem import FilesystemSecrets

__all__ = ["FilesystemSecrets", "MQCredential", "SecretsBackend"]
