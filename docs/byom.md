# Bring Your Own MQ — Wiring IBM MQ client libraries

`pymqi` is a thin wrapper over the IBM MQ C client library. Without
`libmqic_r` + `cmqc.h` available at runtime, MQ-Sentinel still **starts
fine** and serves the demo-sandbox fixtures — but it cannot connect to a
real Queue Manager.

This guide covers the three real-world ways to give MQ-Sentinel access to
the IBM MQ client at install time.

---

## Option A — IBM MQ Redist Client (free, no IBM account)

IBM publishes a redistributable C client for Linux x86_64 and other
platforms. It's free, no entitlement required, and **redistributable** —
you can mirror it inside your org without an IBM relationship.

**Get it:** [Fix Central — IBM MQ redistributable client](https://www.ibm.com/support/fixcentral/swg/selectFixes?product=ibm/WebSphere/WebSphere+MQ&fixids=&function=fixId&parent=ibm/WebSphere)

Look for releases named like:

```
9.4.0.x-IBM-MQC-Redist-LinuxX64.tar.gz
9.4.0.x-IBM-MQC-Redist-Win64.zip
```

### Install on RHEL / Rocky / Oracle Linux

```bash
sudo install -d -m 755 /opt/mqm
cd /opt/mqm
sudo tar xf /path/to/9.4.0.x-IBM-MQC-Redist-LinuxX64.tar.gz
sudo /opt/mqm/bin/setmqenv -s
```

Then point MQ-Sentinel at it via the env file:

```bash
# /etc/mq-sentinel/mq-sentinel.env
LD_LIBRARY_PATH=/opt/mqm/lib64:/opt/mqm/lib
PATH=/opt/mqm/bin:$PATH
```

### Install pymqi against the Redist Client

```bash
sudo -u mq-sentinel /opt/mq-sentinel/bin/pip install pymqi
```

`pymqi` finds the headers + libs via `LD_LIBRARY_PATH`. Verify:

```bash
sudo -u mq-sentinel /opt/mq-sentinel/bin/python -c \
  "import pymqi; print(pymqi.__version__)"
```

---

## Option B — Bake it into the container image

Best for K8s / Path 2 — every Pod ships with the right MQ client; no
node-level state, no `LD_LIBRARY_PATH` config drift.

Drop this `Dockerfile.bring-your-own-mq` next to the standard one:

```dockerfile
# syntax=docker/dockerfile:1.7
ARG MQ_REDIST_URL
ARG MQ_VERSION=9.4.0.0

FROM python:3.12-slim AS mq-redist
RUN apt-get update && apt-get install -y --no-install-recommends curl tar ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /opt/mqm \
 && curl -fsSL "${MQ_REDIST_URL}" | tar -xz -C /opt/mqm

FROM python:3.12-slim AS builder
COPY --from=mq-redist /opt/mqm /opt/mqm
ENV LD_LIBRARY_PATH=/opt/mqm/lib64:/opt/mqm/lib
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip build \
 && python -m build --wheel \
 && pip install --prefix=/install ./dist/*.whl pymqi

FROM gcr.io/distroless/python3-debian12:nonroot
COPY --from=mq-redist /opt/mqm /opt/mqm
COPY --from=builder /install /usr/local
ENV PYTHONPATH=/usr/local/lib/python3.12/site-packages
ENV LD_LIBRARY_PATH=/opt/mqm/lib64:/opt/mqm/lib
USER nonroot:nonroot
ENTRYPOINT ["python", "-m", "mq_sentinel.cli.main"]
CMD ["serve"]
```

Build:

```bash
docker build \
  -f Dockerfile.bring-your-own-mq \
  --build-arg MQ_REDIST_URL=https://artifacts.internal.example.com/ibm-mq/9.4.0.0-IBM-MQC-Redist-LinuxX64.tar.gz \
  -t mq-sentinel-with-mq:0.1.0 .
```

For air-gapped: mirror the redist tarball to internal artifact storage
(`Artifactory`, `Nexus`, `S3`) and pass the internal URL via
`MQ_REDIST_URL`.

---

## Option C — Use an existing IBM MQ install

If the host already has a full IBM MQ Server (typical when you're running
MQ-Sentinel on the same host as a QM), point at the existing `/opt/mqm`:

### Path 1 (Docker)

```bash
docker run -d --name mq-sentinel \
  -v /opt/mqm:/opt/mqm:ro \
  -e LD_LIBRARY_PATH=/opt/mqm/lib64:/opt/mqm/lib \
  ... \
  ghcr.io/pramodreddyboddu/mq-sentinel:0.1.0
```

### Path 2 (Kubernetes)

If MQ is installed on the worker nodes (rare but seen in some on-prem
clusters), use a hostPath volume:

```yaml
volumes:
  - name: mq-client
    hostPath:
      path: /opt/mqm
      type: Directory
volumeMounts:
  - name: mq-client
    mountPath: /opt/mqm
    readOnly: true
env:
  - name: LD_LIBRARY_PATH
    value: /opt/mqm/lib64:/opt/mqm/lib
```

For multi-node clusters, prefer **Option B** — bake the client into the
image so any worker can run a Pod.

### Path 3 (RPM/DEB)

If `/opt/mqm` exists when you install the RPM, the env file's default
`LD_LIBRARY_PATH=/opt/mqm/lib64:/opt/mqm/lib` already points there.
Restart `mq-sentinel.service` and `pip install pymqi` into
`/opt/mq-sentinel`.

---

## Verifying connectivity

### 1. Test from the host

```bash
sudo -u mq-sentinel /opt/mqm/samp/bin/amqsputc Q1 PROD_QM
```

If that works, MQ-Sentinel can connect too.

### 2. Test via MQ-Sentinel

```bash
TOKEN="..."
curl -fsS \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"tool":"diagnose_failed_channels","params":{"qm_name":"PROD_QM"}}' \
  http://127.0.0.1:8080/mcp/tools/call | jq .raw_evidence
```

You should see `channels_examined > 0`. If you get an empty response,
check `journalctl -u mq-sentinel` (or `docker logs mq-sentinel`) for
`MQConnectionError`.

### 3. Diagnose connection failures

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `pymqi is not installed` | pymqi not in venv | `pip install pymqi` into the right venv (see above) |
| `failed to connect to PROD_QM` | TLS / CONNAUTH / CHLAUTH issue | check QM logs, run `amqsputc` first |
| `binary not found: dspmq` | Redist client doesn't ship `dspmq` | Use a full MQ install or skip the topology shell probes (MQ-Sentinel works without them) |
| `MQRC 2538` | TLS handshake failure | check `SSLCIPH` matches between client + server |

---

## Why MQ-Sentinel decoupled itself from `pymqi`

The whole project imports `pymqi` **lazily** inside `PymqiConnector` —
the module compiles, tests pass, and the demo sandbox runs *without* IBM
client libraries on the box. This means:

- ✅ CI builds in a clean container that has never heard of MQ.
- ✅ Security tests run on every PR with no IBM dependency.
- ✅ Customers can evaluate the MCP and run the demo before talking to IBM.
- ✅ Air-gapped customers can stage the install in two steps: install
  MQ-Sentinel from RPM, then later overlay `pymqi` against their own
  Redist tarball.

When `pymqi` is missing, MQ-Sentinel raises `MQConnectionError` with a
helpful message pointing at this document — no cryptic `ImportError`
stack trace from the bowels of the connector.
