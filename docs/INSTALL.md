# Installation Guide

Three deployment paths, picked by your environment. **All three give you
the same MQ-Sentinel** — same security guarantees, same eight tools, same
audit chain. Only the operational wrapper differs.

| Path | For | Time | Onboarding |
|------|-----|------|------------|
| **1. One-line installer** | Solo / startup, single host, ≤ 5 QMs | 5 min | `curl … \| bash` |
| **2. Kubernetes / Helm** | Mid-org, K8s estate, IdP in place | 30 min | `helm install` (worked example: `examples/kind/`) |
| **3. RPM / DEB package** | Regulated / air-gapped (banks, gov, healthcare) | 1 evening | `dnf install` / `apt install` |

If you have IBM MQ client libraries on the host already → see
[Bring Your Own MQ](byom.md) for how to wire them in.

---

## Path 1 — One-line installer (Docker)

**Audience:** small teams, single bastion host, no K8s yet.

### Dev mode (no auth — for laptop POCs)

```bash
curl -fsSL https://raw.githubusercontent.com/pramodreddyboddu/mq-sentinel/main/scripts/install.sh \
  | MQS_DEV_MODE=true MQS_DEV_MODE_ACK_INSECURE=yes bash
```

Server runs at `http://127.0.0.1:8080`. The bind is `127.0.0.1` only — never
exposed to the network. Refuses to install in dev mode without the explicit
`MQS_DEV_MODE_ACK_INSECURE=yes` env, so you can't paste this into a public
host by accident.

### Production mode (OIDC required)

```bash
export MQS_AUTH_OIDC_ISSUER=https://login.example.com/realms/mq-sentinel
export MQS_AUTH_OIDC_AUDIENCE=mq-sentinel
export MQS_AUTH_OIDC_JWKS_URL=https://login.example.com/.well-known/jwks.json

curl -fsSL https://raw.githubusercontent.com/pramodreddyboddu/mq-sentinel/main/scripts/install.sh | bash
```

The script:
- Pulls the signed image from `ghcr.io/pramodreddyboddu/mq-sentinel`.
- Creates `/etc/mq-sentinel/{secrets,inventory,audit}` with locked-down perms.
- Drops a starter `inventory.yaml`.
- Runs the container with `--read-only`, `--cap-drop ALL`, `no-new-privileges`.
- Verifies `/healthz` before declaring success.

### Add Queue Managers

```bash
# Credentials
sudo install -d -m 700 /etc/mq-sentinel/secrets/prod-qm
echo -n 'mq-sentinel-svc'  | sudo tee /etc/mq-sentinel/secrets/prod-qm/username
echo -n 'redacted-password' | sudo tee /etc/mq-sentinel/secrets/prod-qm/password
sudo chmod 400 /etc/mq-sentinel/secrets/prod-qm/*

# Inventory
sudo $EDITOR /etc/mq-sentinel/inventory/inventory.yaml

# Reload
docker restart mq-sentinel
```

### Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/pramodreddyboddu/mq-sentinel/main/scripts/uninstall.sh | bash
# To wipe data dir too:
curl -fsSL .../uninstall.sh | bash -s -- --purge
```

---

## Path 2 — Kubernetes / Helm

**Audience:** anyone with a K8s cluster + an IdP (Okta, Keycloak, AAD, Ping, Auth0).

### Quickstart

```bash
helm install mq-sentinel oci://ghcr.io/pramodreddyboddu/charts/mq-sentinel \
  --namespace mq-sentinel --create-namespace \
  --set oidc.issuer=https://login.example.com/realms/mq-sentinel \
  --set oidc.audience=mq-sentinel \
  --set oidc.jwksUrl=https://login.example.com/.well-known/jwks.json
```

Or with a values file:

```yaml
# my-values.yaml
oidc:
  issuer: https://login.example.com/realms/mq-sentinel
  audience: mq-sentinel
  jwksUrl: https://login.example.com/.well-known/jwks.json
replicaCount: 3
podDisruptionBudget:
  minAvailable: 2
networkPolicy:
  enabled: true
  allowedEgressCIDRs:
    - 10.42.0.0/16   # MQ subnet
    - 10.99.5.0/24   # IdP
```

### Try it locally first

The fully worked example in [`examples/kind/`](../examples/kind/) brings
up MQ-Sentinel + an in-cluster JWKS issuer + a JWT-signed `curl` call
in **under five minutes**. No live MQ required.

```bash
cd examples/kind
./install.sh
```

### Wire credentials via Vault Agent Injector

The `FilesystemSecrets` backend just reads files at a configured path.
Vault Agent Injector renders Vault secrets *to* that path — zero code
change in MQ-Sentinel:

```yaml
podAnnotations:
  vault.hashicorp.com/agent-inject: "true"
  vault.hashicorp.com/role: "mq-sentinel-read"
  vault.hashicorp.com/agent-inject-secret-prod-qm: "secret/data/mq-sentinel/prod-qm"
  vault.hashicorp.com/agent-inject-template-prod-qm: |
    {{- with secret "secret/data/mq-sentinel/prod-qm" -}}
    {{ .Data.data.username }}{{ end }}
```

### Wire Prometheus + Grafana

`/metrics` is exposed without auth (intended for cluster scrape).
Prometheus annotation pattern:

```yaml
podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8080"
  prometheus.io/path: "/metrics"
```

Useful series:
- `mq_sentinel_http_requests_total{path,status}` — alert on `5xx` surges.
- `mq_sentinel_tool_calls_total{tool,outcome}` — alert on `outcome="forbidden"` (auth violation rate).
- `mq_sentinel_http_request_duration_seconds` — SLO histogram.

### Upgrade

```bash
helm upgrade mq-sentinel oci://ghcr.io/pramodreddyboddu/charts/mq-sentinel \
  --namespace mq-sentinel \
  --reuse-values \
  --set image.tag=0.2.0
```

Rolling, zero MQ downtime — no QM connection is held open between calls.

---

## Path 3 — RPM / DEB (regulated, air-gapped)

**Audience:** banks, healthcare, government, regulated SaaS. Deploy via
Satellite / Aptly / SUSE Manager / Anaconda kickstart.

### RHEL 9 / Rocky 9 / Oracle Linux 9 / Amazon Linux 2023

```bash
sudo dnf install -y https://github.com/pramodreddyboddu/mq-sentinel/releases/latest/download/mq-sentinel-0.1.0-1.x86_64.rpm

# Edit OIDC + inventory
sudo $EDITOR /etc/mq-sentinel/mq-sentinel.env
sudo $EDITOR /etc/mq-sentinel/inventory/inventory.yaml

# Drop credentials
sudo install -d -m 700 -o mq-sentinel -g mq-sentinel /etc/mq-sentinel/secrets/prod-qm
echo -n 'mq-sentinel-svc' | sudo -u mq-sentinel tee /etc/mq-sentinel/secrets/prod-qm/username
echo -n 'redacted'        | sudo -u mq-sentinel tee /etc/mq-sentinel/secrets/prod-qm/password
sudo chmod 400 /etc/mq-sentinel/secrets/prod-qm/*

# Start
sudo systemctl enable --now mq-sentinel
sudo journalctl -u mq-sentinel -f
```

### Debian 12 / Ubuntu 22.04+

```bash
sudo apt install -y https://github.com/pramodreddyboddu/mq-sentinel/releases/latest/download/mq-sentinel_0.1.0_amd64.deb
sudo systemctl start mq-sentinel
```

### What the package gives you

- `/opt/mq-sentinel/` — bundled venv (no pip-on-host pollution, no internet at install time).
- `/usr/bin/mq-sentinel` — CLI symlink.
- `/usr/lib/systemd/system/mq-sentinel.service` — hardened unit (read-only FS, dropped caps, seccomp, no-new-privs, MemoryDenyWriteExecute).
- `/etc/mq-sentinel/mq-sentinel.env` — config file (preserved across upgrades).
- `/etc/mq-sentinel/{inventory,secrets}` — config + credentials directories with correct ownership.
- `/var/log/mq-sentinel/` — audit log + journald.
- `mq-sentinel:mq-sentinel` system user/group, `nologin` shell.

### Air-gapped install

1. Mirror the RPM/DEB into your internal repo (Satellite / Foreman / Aptly).
2. Mirror the IBM MQ Redist Client tarball internally (see [BYOMQ](byom.md)).
3. Disable internet egress from the MQ-Sentinel host.
4. KC document URLs are pre-populated in `KCRegistry` at build time — no network needed to *return* them. **Customers reaching the URLs is on the customer's intranet mirror** (planned for v0.2.0 — see CHANGELOG).

### Build packages yourself

```bash
git clone https://github.com/pramodreddyboddu/mq-sentinel.git
cd mq-sentinel
make rpm        # → dist/pkg/mq-sentinel-0.1.0-1.x86_64.rpm
make deb        # → dist/pkg/mq-sentinel_0.1.0_amd64.deb
make pkg        # both
```

Requires `fpm` (`gem install fpm`) and Python 3.12.

### Sign the package (gold standard)

After building, sign with your org's GPG key:

```bash
rpmsign --addsign dist/pkg/mq-sentinel-0.1.0-1.x86_64.rpm
dpkg-sig --sign builder dist/pkg/mq-sentinel_0.1.0_amd64.deb
```

Then publish to your internal repo. End-user install becomes:

```bash
sudo dnf install mq-sentinel    # repo metadata enforces signature
```

---

## After install — same for all three paths

### Verify the install

```bash
# Health
curl -fsS http://127.0.0.1:8080/healthz | jq .

# List tools (no auth needed)
curl -fsS http://127.0.0.1:8080/mcp/tools | jq .

# Try a tool against the bundled demo sandbox (works without live MQ)
TOKEN="..."   # mint via your OIDC flow, or omit in dev mode
curl -fsS \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"tool":"full_mq_health_check","params":{"qm_name":"DEMO_QM"}}' \
  http://127.0.0.1:8080/mcp/tools/call | jq .summary
```

### Verify the audit chain

```bash
# Path 1
docker exec mq-sentinel mq-sentinel verify-audit

# Path 2
kubectl -n mq-sentinel exec deploy/mq-sentinel -- mq-sentinel verify-audit

# Path 3
sudo -u mq-sentinel mq-sentinel verify-audit
```

### Wire your AI agent

**Claude Desktop / Cursor / Claude Code:** add the MCP server to your client config.
For HTTP transport, see [docs/http-transport.md](http-transport.md).

For stdio (laptop / dev), MQ-Sentinel runs as a subprocess of the agent — no
network involved.

---

## Choosing between the paths

```
                         ┌── Single host? ──→ Path 1
                         │
          Have K8s? ─────┤
                         │
                         └── Path 2 (Helm) — has IdP? Yes? Done.
                                                   No? Add Keycloak first.

   No K8s, regulated? ────────────────────→ Path 3 (RPM/DEB)
```

If you're not sure, start at **Path 1 dev mode** for 30 minutes to see
whether MQ-Sentinel is what you need. Then graduate to Path 2 or 3.
