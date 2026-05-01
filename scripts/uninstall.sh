#!/usr/bin/env bash
# MQ-Sentinel uninstaller. Stops + removes the container; preserves data dir
# unless --purge is passed.

set -Eeuo pipefail

PURGE=false
DATA_DIR="${MQS_DATA_DIR:-/etc/mq-sentinel}"

for arg in "$@"; do
    case "$arg" in
        --purge) PURGE=true ;;
        --data-dir=*) DATA_DIR="${arg#--data-dir=}" ;;
        -h|--help)
            cat <<EOF
Usage: uninstall.sh [--purge] [--data-dir=PATH]
  --purge       Remove ${DATA_DIR} (audit log + inventory + secrets) too.
  --data-dir    Override default data directory.
EOF
            exit 0 ;;
        *) echo "unknown arg: $arg" >&2; exit 1 ;;
    esac
done

echo "[mq-sentinel] Stopping + removing container ..."
docker rm -f mq-sentinel >/dev/null 2>&1 || true

if [[ "${PURGE}" == "true" ]]; then
    echo "[mq-sentinel] Purging data dir ${DATA_DIR} ..."
    rm -rf "${DATA_DIR}"
else
    echo "[mq-sentinel] Data dir preserved at ${DATA_DIR} (use --purge to remove)."
fi

echo "[mq-sentinel] Done."
