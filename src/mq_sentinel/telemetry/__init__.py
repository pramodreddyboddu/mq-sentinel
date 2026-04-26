"""OpenTelemetry + Prometheus setup."""

from mq_sentinel.telemetry.setup import configure_telemetry, get_logger, get_tracer

__all__ = ["configure_telemetry", "get_logger", "get_tracer"]
