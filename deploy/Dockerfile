# syntax=docker/dockerfile:1.7
# MQ-Sentinel — distroless, non-root, read-only FS.

FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip build && python -m build --wheel
RUN pip install --prefix=/install ./dist/*.whl

FROM gcr.io/distroless/python3-debian12:nonroot
LABEL org.opencontainers.image.title="mq-sentinel"
LABEL org.opencontainers.image.description="Read-only IBM MQ diagnostic MCP server"
LABEL org.opencontainers.image.licenses="Proprietary"
LABEL org.opencontainers.image.source="https://github.com/pramodreddyboddu/mq-sentinel"

COPY --from=builder /install /usr/local
ENV PYTHONPATH=/usr/local/lib/python3.12/site-packages
ENV MQS_SERVER_ENVIRONMENT=prod
USER nonroot:nonroot
ENTRYPOINT ["python", "-m", "mq_sentinel.cli.main"]
CMD ["serve"]
