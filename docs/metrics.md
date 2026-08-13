# MQ-Sentinel Metrics Reference

MQ-Sentinel exposes Prometheus metrics at `/metrics` when running the HTTP transport.

## Key Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `mq_sentinel_requests_total` | Counter | Total tool invocations | tool, principal, qm_tier, status |
| `mq_sentinel_errors_total` | Counter | Failed tool calls | tool, error_type |
| `mq_sentinel_request_duration_seconds` | Histogram | Tool execution time | tool |
| `mq_sentinel_audit_writes_total` | Counter | Successful audit entries |  |
| `mq_sentinel_audit_errors_total` | Counter | Audit write failures |  |
| `mq_sentinel_health_status` | Gauge | 1 = healthy |  |
| `mq_sentinel_active_connections` | Gauge | Current MQ connections |  |

## Recommended Grafana Panels

- Request rate by tool
- Error rate (should be near zero)
- p95 / p99 latency per tool
- Audit write success rate
- Health status over time

See `observability/grafana-dashboard.json` for a ready-to-import dashboard.

## SLO Examples

- Error rate < 0.1% over 30 days
- p95 latency < 3s for health checks
- 100% audit writes successful

Use the alerts in `observability/prometheus-alerts.yaml` as a starting point.