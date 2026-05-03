# Hosted public demo — `demo.mq-sentinel.io`

A read-only, sandboxed MQ-Sentinel anyone can hit without installing
anything. Same code path as production, but the underlying QM is the
bundled `demo-sandbox/fixtures` — no real IBM MQ exists behind it.

The only purpose: **let prospects evaluate the product in 30 seconds**
before deciding whether to install it for their own QMs.

## Architecture (free tier — $0/month)

```
            INTERNET                   INSIDE YOUR CLOUD/HOME
                                       ┌──────────────────────────┐
   demo.mq-sentinel.io  ──── HTTPS ────│  Cloudflare Tunnel       │
   (managed by CF)                     │  (cloudflared container) │
                                       │            ↓             │
                                       │  mq-sentinel container   │
                                       │  (fixture-only, no MQ)   │
                                       └──────────────────────────┘
```

- **DNS + TLS:** Cloudflare manages it (free).
- **Tunnel:** Cloudflare Tunnel (free, no port-forwarding, no public IP).
- **Compute:** any always-on machine that can run two containers — a $5
  Hetzner VPS, an old Mac mini, even a Raspberry Pi.
- **Auth:** stub OIDC (`MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV=true`) +
  Cloudflare Access policy that adds Bearer-token rate-limiting at the
  edge.

## One-time setup

```bash
# 1. Create the tunnel + DNS record (one-time)
cloudflared tunnel login
cloudflared tunnel create mq-sentinel-demo
cloudflared tunnel route dns mq-sentinel-demo demo.mq-sentinel.io

# 2. Deploy with docker-compose
cd deploy/hosted-demo
cp cloudflared.yml.example cloudflared.yml
# edit cloudflared.yml — set tunnel ID + credentials path
docker compose up -d

# 3. Verify
curl -fsS https://demo.mq-sentinel.io/healthz
```

## What visitors can do

```bash
# Public token, baked into the demo image — read-only by construction.
TOKEN="demo-readonly"

# List tools
curl -s https://demo.mq-sentinel.io/mcp/tools | jq .

# Invoke the headline composite tool against the seeded fixture QM
curl -s -H "Authorization: Bearer $TOKEN" \
       -H "Content-Type: application/json" \
       -d '{"tool":"full_mq_health_check","params":{"qm_name":"DEMO_QM"}}' \
       https://demo.mq-sentinel.io/mcp/tools/call \
| jq .summary
```

## Cost protection

Cloudflare Access policy at the edge:
- Max 30 requests/min per IP.
- Block any request that is not `GET /healthz`, `GET /readyz`,
  `GET /metrics`, `GET /mcp/tools`, or `POST /mcp/tools/call`.
- Block requests larger than 8 KiB.

Even under HN front-page load, this stays well under Cloudflare free-tier
limits. The mq-sentinel container itself has the rate limiter
(`MQS_SECURITY_RATE_LIMIT_PER_MINUTE=20`) as a backup.

## When to take it down

Never. The demo doesn't connect to any live MQ — there's nothing to
expose. The image is exactly what's on `ghcr.io/pramodreddyboddu/mq-sentinel`,
running with the bundled fixtures. Worst case, an attacker exhausts the
container; restart it.
