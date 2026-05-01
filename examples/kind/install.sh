#!/usr/bin/env bash
# examples/kind/install.sh — bring up MQ-Sentinel on Kind in <5 min.

set -Eeuo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-mq-sentinel-demo}"
NAMESPACE="${NAMESPACE:-mq-sentinel}"
JWKS_NAMESPACE="${JWKS_NAMESPACE:-demo}"

require() { command -v "$1" >/dev/null || { echo "missing: $1" >&2; exit 1; }; }
for c in docker kind kubectl helm jq python3 openssl; do require "$c"; done

cd "$(dirname "$0")/../.."  # repo root

echo "==> 1. Create Kind cluster"
kind get clusters | grep -q "^${CLUSTER_NAME}$" \
  || kind create cluster --name "${CLUSTER_NAME}" --config examples/kind/kind-config.yaml

echo "==> 2. Build + load image"
docker build -f deploy/Dockerfile -t mq-sentinel:dev .
kind load docker-image mq-sentinel:dev --name "${CLUSTER_NAME}"

echo "==> 3. Generate keypair + JWKS"
WORK=$(mktemp -d)
trap 'rm -rf "${WORK}"' EXIT
python3 - "${WORK}" <<'PY'
import json, sys, pathlib
from authlib.jose import JsonWebKey
work = pathlib.Path(sys.argv[1])
priv = JsonWebKey.generate_key("RSA", 2048, options={"kid": "demo-kid"}, is_private=True)
priv_jwk = priv.as_dict(is_private=True)
pub_jwk  = priv.as_dict(is_private=False)
pub_jwk["alg"] = "RS256"
pub_jwk["use"] = "sig"
(work / "private.jwk.json").write_text(json.dumps(priv_jwk))
(work / "jwks.json").write_text(json.dumps({"keys": [pub_jwk]}))
PY

echo "==> 4. Deploy in-cluster JWKS server"
kubectl create namespace "${JWKS_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "${JWKS_NAMESPACE}" create configmap jwks --from-file=jwks.json="${WORK}/jwks.json" \
  --dry-run=client -o yaml | kubectl apply -f -
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jwks
  namespace: ${JWKS_NAMESPACE}
spec:
  replicas: 1
  selector: { matchLabels: { app: jwks } }
  template:
    metadata: { labels: { app: jwks } }
    spec:
      containers:
        - name: nginx
          image: nginx:1.27-alpine
          ports: [{ containerPort: 80 }]
          volumeMounts:
            - name: jwks
              mountPath: /usr/share/nginx/html
      volumes:
        - name: jwks
          configMap: { name: jwks }
---
apiVersion: v1
kind: Service
metadata:
  name: jwks
  namespace: ${JWKS_NAMESPACE}
spec:
  selector: { app: jwks }
  ports: [{ port: 80, targetPort: 80 }]
EOF

echo "==> 5. Helm install MQ-Sentinel"
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install mq-sentinel deploy/helm \
  --namespace "${NAMESPACE}" \
  --values examples/kind/values.yaml \
  --wait --timeout 3m

echo "==> 6. Mint a demo JWT (prod-read role)"
TOKEN=$(python3 - "${WORK}" <<'PY'
import json, pathlib, sys, time
from authlib.jose import JsonWebToken
priv = json.loads((pathlib.Path(sys.argv[1]) / "private.jwk.json").read_text())
now = int(time.time())
claims = {
    "iss": "http://jwks.demo.svc.cluster.local",
    "aud": "mq-sentinel",
    "sub": "demo-user@kind",
    "iat": now, "nbf": now - 5, "exp": now + 3600,
    "tenant": "demo",
    "roles": ["prod-read", "nonprod-read"],
}
print(JsonWebToken(["RS256"]).encode({"alg": "RS256", "kid": "demo-kid"}, claims, priv).decode())
PY
)

echo "==> 7. Try it"
kubectl -n "${NAMESPACE}" port-forward svc/mq-sentinel 8080:8080 >/dev/null 2>&1 &
PF_PID=$!
trap 'kill ${PF_PID} 2>/dev/null || true' EXIT

# Wait for port-forward
for _ in {1..20}; do
    curl -fsS http://127.0.0.1:8080/healthz >/dev/null 2>&1 && break
    sleep 0.5
done

echo
echo "----- /healthz -----"
curl -fsS http://127.0.0.1:8080/healthz | jq .
echo
echo "----- /mcp/tools (no auth) -----"
curl -fsS http://127.0.0.1:8080/mcp/tools | jq '.tools | length as $n | "\($n) tools available"'
echo
echo "----- POST /mcp/tools/call (with JWT) -----"
curl -fsS \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"tool":"health","params":{}}' \
  http://127.0.0.1:8080/mcp/tools/call | jq .

echo
echo "✅ MQ-Sentinel is running on Kind."
echo
echo "To call diagnostic tools (the demo sandbox lives inside the image):"
echo "  TOKEN='${TOKEN}'"
echo "  curl -H \"Authorization: Bearer \$TOKEN\" -H 'Content-Type: application/json' \\"
echo "       -d '{\"tool\":\"full_mq_health_check\",\"params\":{\"qm_name\":\"DEMO_QM\"}}' \\"
echo "       http://127.0.0.1:8080/mcp/tools/call | jq ."
echo
echo "To verify audit chain:"
echo "  kubectl -n ${NAMESPACE} exec deploy/mq-sentinel -- mq-sentinel verify-audit"
echo
echo "To tear down:"
echo "  kind delete cluster --name ${CLUSTER_NAME}"
