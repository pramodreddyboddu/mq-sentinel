"""Inventory data models. Credentials live elsewhere (secrets backend)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Topology(StrEnum):
    STANDALONE = "standalone"
    MULTI_INSTANCE = "multi_instance"
    RDQM = "rdqm"
    NATIVE_HA = "native_ha"
    NATIVE_HA_CRR = "native_ha_crr"
    UNIFORM_CLUSTER = "uniform_cluster"
    TRADITIONAL_CLUSTER = "traditional_cluster"
    ZOS_QSG = "zos_qsg"
    APPLIANCE = "appliance"
    CONTAINERIZED = "containerized"
    UNKNOWN = "unknown"


class QMEntry(BaseModel):
    """A Queue Manager inventory entry. NEVER contains credentials."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    qm_name: str = Field(min_length=1, max_length=48, pattern=r"^[A-Z0-9._%/]+$")
    host: str = Field(min_length=1, max_length=253)
    port: int = Field(ge=1, le=65535)
    channel: str = Field(min_length=1, max_length=20, pattern=r"^[A-Z0-9._/%]+$")
    environment: str = Field(pattern=r"^(dev|staging|prod|nonprod)$")
    topology_hint: Topology = Topology.UNKNOWN
    mq_version_hint: str | None = Field(default=None, max_length=16)
    tenant: str = Field(default="default", max_length=64)
    secret_ref: str = Field(min_length=1, max_length=256)
    """Opaque reference resolved by the secrets backend (never the secret itself)."""

    @field_validator("host")
    @classmethod
    def _valid_host(cls, v: str) -> str:
        if any(c in v for c in ("/", "\\", " ", "\n")):
            raise ValueError("invalid host")
        return v
