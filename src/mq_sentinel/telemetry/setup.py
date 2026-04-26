"""Structured logging + OpenTelemetry tracing. Idempotent initialization."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Tracer

from mq_sentinel.config import TelemetryConfig

_INITIALIZED = False


def configure_telemetry(cfg: TelemetryConfig) -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    resource = Resource.create({"service.name": cfg.service_name})
    provider = TracerProvider(resource=resource)
    if cfg.otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=cfg.otlp_endpoint))
        )
    trace.set_tracer_provider(provider)

    _INITIALIZED = True


def get_logger(name: str | None = None) -> Any:
    return structlog.get_logger(name)


def get_tracer(name: str) -> Tracer:
    return trace.get_tracer(name)
