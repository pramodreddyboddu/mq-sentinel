"""Layered configuration: env > file > defaults. Secrets never come from here."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecurityConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MQS_SECURITY_", extra="forbid")

    enforce_readonly: bool = True
    """Hard-coded true in code paths; this flag cannot disable the allowlist."""

    max_response_bytes: int = 256 * 1024
    max_mqsc_rows: int = 500
    max_log_lines: int = 1000
    rate_limit_per_minute: int = 60
    tls_min_version: Literal["TLSv1.3"] = "TLSv1.3"
    allowed_doc_hosts: tuple[str, ...] = ("www.ibm.com",)


class AuthConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MQS_AUTH_", extra="forbid")

    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_scopes: str | None = None
    """Space-separated scopes MCP clients should request from the IdP, e.g.
    ``api://mq-sentinel/.default`` (Entra). Advertised in OAuth resource metadata."""
    disable_auth_for_local_dev: bool = False
    """ONLY set true on a developer laptop. CI refuses production builds with this on."""


class AuditConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MQS_AUDIT_", extra="forbid")

    log_path: Path = Path("./audit.jsonl")
    hash_chain: bool = True
    forward_syslog: bool = False
    syslog_address: str | None = None


class TelemetryConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MQS_TELEMETRY_", extra="forbid")

    otlp_endpoint: str | None = None
    service_name: str = "mq-sentinel"
    metrics_port: int = 9464


class ServerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MQS_SERVER_", extra="forbid")

    transport: Literal["stdio", "http"] = "stdio"
    http_host: str = "127.0.0.1"
    http_port: int = 8080
    environment: Literal["dev", "staging", "prod"] = "dev"

    inventory_dir: str | None = None
    """Directory of YAML files for large org fleet inventory (loaded at startup)."""

    connector: Literal["auto", "fixture", "pymqi"] = "auto"
    """auto: live pymqi when an inventory is configured, else the demo fixtures."""

    public_url: str | None = None
    """External URL of the MCP endpoint, e.g. https://mq-sentinel.example.com/mcp.
    Used as the OAuth resource identifier and as an allowed Host header."""

    secrets_dir: str | None = None
    """Filesystem secrets root (one subdirectory per secret_ref). Required for pymqi."""

    def resolved_connector(self) -> Literal["fixture", "pymqi"]:
        if self.connector == "auto":
            return "pymqi" if self.inventory_dir else "fixture"
        return self.connector


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MQS_", extra="forbid")

    server: ServerConfig = Field(default_factory=ServerConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)

    def assert_production_safe(self) -> None:
        if self.server.environment == "prod" and self.auth.disable_auth_for_local_dev:
            raise RuntimeError(
                "disable_auth_for_local_dev is not permitted in production environment"
            )
        if self.server.environment == "prod" and self.server.resolved_connector() == "fixture":
            raise RuntimeError(
                "the demo fixture connector is not permitted in production environment; "
                "set MQS_SERVER_INVENTORY_DIR (and MQS_SERVER_SECRETS_DIR) for live QMs"
            )


def load_settings() -> Settings:
    settings = Settings()
    settings.assert_production_safe()
    return settings
