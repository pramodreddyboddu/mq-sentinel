# Local Kubernetes example — Kind + Helm + a fake OIDC issuer

This example brings up MQ-Sentinel end-to-end on your laptop in **under
five minutes**, with no live IBM MQ required. It mirrors the Path 2
mid-org deployment from [docs/INSTALL.md](../../docs/INSTALL.md): K8s,
ingress, Helm, OIDC, JWT-authenticated tool invocation.

## Prerequisites

- `docker`, `kind`, `kubectl`, `helm`, `jq` on your PATH.
- ~4 GB free RAM for the Kind cluster.

## One command

```bash
./install.sh
```

That script will:

1. Create a Kind cluster (`mq-sentinel-demo`).
2. Build the MQ-Sentinel image and load it into Kind.
3. Generate an RSA keypair + a JWKS file; serve the JWKS from a tiny
   in-cluster nginx (so we don't need a real Okta).
4. `helm install mq-sentinel deploy/helm` with that JWKS URL wired in.
5. Wait for the Pod to be Ready.
6. Mint a JWT signed with the matching private key.
7. Show you the curl command that hits `/mcp/tools/call` with that token
   and gets a real `full_mq_health_check` response back.

## Inspect

```bash
kubectl logs -n mq-sentinel deploy/mq-sentinel
kubectl exec -n mq-sentinel deploy/mq-sentinel -- mq-sentinel verify-audit
```

## Tear down

```bash
kind delete cluster --name mq-sentinel-demo
```

## Why this matters for buyers

Three audiences walk through this in their POC:

- **Mid-org platform engineer:** "OK so the Helm chart actually works,
  the OIDC integration is real, the metrics scrape, and the audit chain
  verifies. I trust this."
- **Security reviewer:** "Show me a tampered audit log break the chain."
  Run `kubectl exec ... bash -c "echo bogus >> /var/audit/audit.jsonl"`,
  then `verify-audit` fails loudly.
- **MQ admin:** "Show me a 2035 in Claude." Wire Claude Code to the
  Kind ingress (port-forward), call `diagnose_failed_channels`.
