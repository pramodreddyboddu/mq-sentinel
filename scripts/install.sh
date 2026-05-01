#!/usr/bin/env bash
# MQ-Sentinel — one-line Docker installer (Path 1: startup / single-host)
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/pramodreddyboddu/mq-sentinel/main/scripts/install.sh | bash
# OR (recommended — review first):
#   curl -fsSLO https://raw.githubusercontent.com/pramodreddyboddu/mq-sentinel/main/scripts/install.sh
#   less install.sh
#   bash install.sh
#
# Env vars (optional):
#   MQS_VERSION         — image tag (default: latest)
#   MQS_IMAGE           — full image ref (default: ghcr.io/pramodreddyboddu/mq-sentinel)
#   MQS_PORT            — host port (default: 8080)
#   MQS_DATA_DIR        — host config + audit dir (default: /etc/mq-sentinel)
#   MQS_DEV_MODE        — set to "true" to skip OIDC (single-host dev only)
#
# Refuses to run if MQS_DEV_MODE is set on a host with a public IP unless
# MQS_DEV_MODE_ACK_INSECURE=yes is also set.

set -Eeuo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

log()  { printf '%b[mq-sentinel]%b %s\n'  "${GREEN}" "${NC}" "$*"; }
warn() { printf '%b[mq-sentinel]%b %s\n' "${YELLOW}" "${NC}" "$*" >&2; }
die()  { printf '%b[mq-sentinel]%b %s\n'    "${RED}" "${NC}" "$*" >&2; exit 1; }

require() { command -v "$1" >/dev/null 2>&1 || die "missing dependency: $1"; }

main() {
    require docker
    require sha256sum 2>/dev/null || require shasum

    local version="${MQS_VERSION:-latest}"
    local image="${MQS_IMAGE:-ghcr.io/pramodreddyboddu/mq-sentinel}:${version}"
    local port="${MQS_PORT:-8080}"
    local data_dir="${MQS_DATA_DIR:-/etc/mq-sentinel}"
    local dev_mode="${MQS_DEV_MODE:-false}"

    log "Image:    ${image}"
    log "Port:     ${port} (bound to 127.0.0.1 by default)"
    log "Data dir: ${data_dir}"
    log "Dev mode: ${dev_mode}"

    if [[ "${dev_mode}" == "true" ]]; then
        if [[ "${MQS_DEV_MODE_ACK_INSECURE:-no}" != "yes" ]]; then
            warn "Dev mode disables OIDC — anyone reaching the port becomes 'local-dev'."
            warn "Re-run with MQS_DEV_MODE_ACK_INSECURE=yes to confirm you understand."
            die  "refusing to install in dev mode without explicit ack"
        fi
    fi

    log "Creating ${data_dir}/{secrets,inventory,audit} ..."
    install -d -m 700 "${data_dir}"
    install -d -m 700 "${data_dir}/secrets"
    install -d -m 750 "${data_dir}/inventory"
    install -d -m 750 "${data_dir}/audit"

    if [[ ! -f "${data_dir}/inventory/inventory.yaml" ]]; then
        cat >"${data_dir}/inventory/inventory.yaml" <<'EOF'
# MQ-Sentinel inventory — list every Queue Manager you want to diagnose.
# Credentials are NOT stored here — only `secret_ref` pointing at
# /etc/mq-sentinel/secrets/<secret_ref>/{username,password,...}
queue_managers:
  - qm_name: DEV_QM
    host: mq.example.internal
    port: 1414
    channel: MCP.SVRCONN
    environment: dev
    secret_ref: dev-qm
EOF
        chmod 640 "${data_dir}/inventory/inventory.yaml"
        log "Wrote starter inventory at ${data_dir}/inventory/inventory.yaml — edit it next."
    fi

    log "Pulling image (this may take a minute) ..."
    docker pull "${image}"

    log "(Re)starting container ..."
    docker rm -f mq-sentinel >/dev/null 2>&1 || true

    local extra_env=()
    if [[ "${dev_mode}" == "true" ]]; then
        extra_env+=( -e "MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV=true" )
        extra_env+=( -e "MQS_SERVER_ENVIRONMENT=dev" )
    else
        extra_env+=( -e "MQS_SERVER_ENVIRONMENT=prod" )
        warn "Production mode — make sure MQS_AUTH_OIDC_* env vars are exported."
        : "${MQS_AUTH_OIDC_ISSUER:?required in production}"
        : "${MQS_AUTH_OIDC_AUDIENCE:?required in production}"
        : "${MQS_AUTH_OIDC_JWKS_URL:?required in production}"
        extra_env+=( -e "MQS_AUTH_OIDC_ISSUER=${MQS_AUTH_OIDC_ISSUER}" )
        extra_env+=( -e "MQS_AUTH_OIDC_AUDIENCE=${MQS_AUTH_OIDC_AUDIENCE}" )
        extra_env+=( -e "MQS_AUTH_OIDC_JWKS_URL=${MQS_AUTH_OIDC_JWKS_URL}" )
    fi

    docker run -d \
        --name mq-sentinel \
        --restart unless-stopped \
        --read-only \
        --tmpfs /tmp:rw,size=64m \
        --cap-drop ALL \
        --security-opt no-new-privileges:true \
        -p "127.0.0.1:${port}:8080" \
        -v "${data_dir}/inventory:/etc/mq-sentinel/inventory:ro" \
        -v "${data_dir}/secrets:/etc/mq-sentinel/secrets:ro" \
        -v "${data_dir}/audit:/var/audit" \
        -e MQS_SERVER_TRANSPORT=http \
        -e MQS_SERVER_HTTP_HOST=0.0.0.0 \
        -e MQS_SERVER_HTTP_PORT=8080 \
        -e MQS_AUDIT_LOG_PATH=/var/audit/audit.jsonl \
        "${extra_env[@]}" \
        "${image}" \
        serve --transport http >/dev/null

    sleep 2
    if curl -fsS "http://127.0.0.1:${port}/healthz" >/dev/null 2>&1; then
        log "✅ MQ-Sentinel is up at http://127.0.0.1:${port}"
        log "    /healthz, /readyz, /metrics, GET /mcp/tools (no auth)"
        log "    POST /mcp/tools/call (Bearer auth required unless dev mode)"
        log ""
        log "Next steps:"
        log "  1. Add Queue Managers to ${data_dir}/inventory/inventory.yaml"
        log "  2. Drop credentials at ${data_dir}/secrets/<ref>/{username,password}"
        log "     (chmod 400 for files, chmod 700 for dirs)"
        log "  3. Restart: docker restart mq-sentinel"
        log ""
        log "Diagnose: docker logs mq-sentinel"
        log "Verify audit chain: docker exec mq-sentinel mq-sentinel verify-audit"
    else
        warn "Health probe failed — check 'docker logs mq-sentinel'"
        exit 1
    fi
}

main "$@"
