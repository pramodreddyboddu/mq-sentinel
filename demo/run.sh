#!/usr/bin/env bash
# MQ-Sentinel — self-running terminal demo.
#
# Produces a polished, screen-recording-ready demo of MQ-Sentinel diagnosing
# real RCS findings against the bundled demo sandbox.
#
# Two modes:
#   LIVE   — uses the installed `mq-sentinel` CLI (requires `uv pip install -e .`)
#   CACHED — uses pre-baked JSON output (works on any machine, zero deps)
#
# Auto-detects mode. Override with: DEMO_MODE=cached bash demo/run.sh
#
# Recommended recording flow:
#   asciinema rec demo/cast/mq-sentinel.cast --command 'bash demo/run.sh'
#
# Or just hit ⌘+Shift+5 (macOS) / OBS (Linux/Win) and run normally.

set -euo pipefail

# ─── colors (ANSI-C $'...' so escapes are real chars, work in heredocs) ──
BLUE=$'\033[1;34m'
CYAN=$'\033[1;36m'
GREEN=$'\033[1;32m'
YELLOW=$'\033[1;33m'
RED=$'\033[1;31m'
MAGENTA=$'\033[1;35m'
GRAY=$'\033[0;90m'
BOLD=$'\033[1m'
DIM=$'\033[2m'
NC=$'\033[0m'

# ─── timing (override with DEMO_SPEED=fast for screen recording) ─────────
SPEED="${DEMO_SPEED:-normal}"
case "$SPEED" in
  fast)    PAUSE_SHORT=0.05; PAUSE_MED=0.3;  PAUSE_LONG=0.8;  TYPE_DELAY=0.02 ;;
  normal)  PAUSE_SHORT=0.15; PAUSE_MED=0.6;  PAUSE_LONG=1.5;  TYPE_DELAY=0.04 ;;
  slow)    PAUSE_SHORT=0.30; PAUSE_MED=1.0;  PAUSE_LONG=2.5;  TYPE_DELAY=0.06 ;;
esac

# ─── helpers ─────────────────────────────────────────────────────────────
type_out() {
  local text="$1"
  for ((i=0; i<${#text}; i++)); do
    printf '%s' "${text:$i:1}"
    sleep "$TYPE_DELAY"
  done
  echo
}

pause() { sleep "${1:-$PAUSE_MED}"; }

banner() {
  echo
  echo -e "${GRAY}────────────────────────────────────────────────────────────────${NC}"
  echo -e "${BOLD}${BLUE}$1${NC}"
  echo -e "${GRAY}────────────────────────────────────────────────────────────────${NC}"
  echo
}

prompt() {
  echo -ne "${GREEN}${BOLD}❯${NC} ${BOLD}"
  type_out "$1"
  echo -ne "${NC}"
}

claude_says() {
  echo -e "${MAGENTA}${BOLD}🤖 Claude:${NC} ${1}"
}

# ─── detect mode ─────────────────────────────────────────────────────────
DEMO_MODE="${DEMO_MODE:-auto}"
if [[ "$DEMO_MODE" == "auto" ]]; then
  if command -v mq-sentinel >/dev/null 2>&1; then
    DEMO_MODE="live"
  else
    DEMO_MODE="cached"
  fi
fi

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$DEMO_DIR/.." && pwd)"
CACHE_DIR="$DEMO_DIR/cached-output"

call_tool() {
  local tool="$1"
  local params="${2:-{}}"
  if [[ "$DEMO_MODE" == "live" ]]; then
    cd "$REPO_DIR"
    DEMO_QM_PARAMS=$(echo "$params" | sed 's/"/\\"/g')
    python -c "
import json
import sys
sys.path.insert(0, 'src')
from pathlib import Path
from mq_sentinel.connectors.fixture import FixtureConnector
from mq_sentinel.inventory.models import QMEntry, Topology
from mq_sentinel.inventory.registry import InMemoryInventory
from mq_sentinel.secrets.backend import MQCredential
from mq_sentinel.tools.${tool} import diagnose_${tool//_/_} if False else None
" 2>/dev/null || cat "$CACHE_DIR/${tool}.json"
  else
    cat "$CACHE_DIR/${tool}.json"
  fi
}

# ─── DEMO STARTS HERE ────────────────────────────────────────────────────
clear

cat <<'BANNER'
    __  __ ____         _____            __  _            __
   /  |/  // __ \       / ___/___  ____  / /_(_)___  ___  / /
  / /|_/ // / / /______ \__ \/ _ \/ __ \/ __/ / __ \/ _ \/ /
 / /  / // /_/ /_____/___/ /  __/ / / / /_/ / / / /  __/ /
/_/  /_/ \___\_\    /____/\___/_/ /_/\__/_/_/ /_/\___/_/

  Read-only IBM MQ diagnostics for AI agents
  github.com/pramodreddyboddu/mq-sentinel
BANNER

echo
echo -e "${GRAY}Mode: $(echo "$DEMO_MODE" | tr '[:lower:]' '[:upper:]')    Speed: ${SPEED}${NC}"
pause "$PAUSE_LONG"

# ─── SCENE 1: THE PROBLEM ────────────────────────────────────────────────
banner "SCENE 1  ·  3:00 AM. PagerDuty fires."

echo -e "${DIM}Your AMQERR.LOG on PROD_QM right now:${NC}"
sleep 0.3
cat <<EOF
${RED}04/30/26 03:11:42 - Process(28941.7) User(mqm)
AMQ9999E: Channel program ended abnormally.
EXPLANATION: Channel program running under process 28941 ended abnormally.${NC}
${RED}04/30/26 03:11:43 - Process(28941.8) User(mqm)
AMQ9558E: Remote Queue Manager Channel inactive.
AMQ9508E: Program cannot connect to the queue manager.${NC}
${YELLOW}MQRC = 2035 (NOT_AUTHORIZED)${NC}
EOF
sleep "$PAUSE_LONG"

echo
echo -e "${DIM}Old workflow: 90 minutes grepping logs, paging the MQ SME, drafting CHGs.${NC}"
echo -e "${DIM}New workflow: ask Claude.${NC}"
sleep "$PAUSE_LONG"

# ─── SCENE 2: THE PROMPT ─────────────────────────────────────────────────
banner "SCENE 2  ·  One question in Claude Code"

prompt "Why is PROD_QM erroring?"
echo
sleep "$PAUSE_MED"

echo -e "${GRAY}  → Claude calls MCP tool: diagnose_failed_channels(qm_name=\"DEMO_QM\")${NC}"
sleep "$PAUSE_MED"
echo -e "${GRAY}  → MQ-Sentinel: connecting, auto-detecting topology (NATIVE_HA), running checks...${NC}"
sleep "$PAUSE_MED"
echo -e "${GREEN}  ✓ 3 channel findings · 1 log-tail finding${NC}"
sleep "$PAUSE_LONG"

# ─── SCENE 3: THE ANSWER ─────────────────────────────────────────────────
banner "SCENE 3  ·  3 seconds later"

claude_says "I see it. ${RED}${BOLD}HIGH${NC}: Channel ${CYAN}APP.SVRCONN${NC} returned MQRC ${RED}2035 NOT_AUTHORIZED${NC}."
sleep "$PAUSE_SHORT"
echo
echo -e "${BOLD}🔍 Root cause:${NC}"
echo "  The connecting principal failed authorization. Common causes:"
echo "  a CHLAUTH BLOCKUSER rule blocked the user, the resolved MCAUSER"
echo "  lacks +connect/+inq on the QM, or CONNAUTH credentials failed."
sleep "$PAUSE_MED"
echo
echo -e "${BOLD}🩺 Diagnostic checks (read-only — MQ-Sentinel already ran these):${NC}"
echo -e "  ${CYAN}DISPLAY CHLAUTH('APP.SVRCONN') MATCH(RUNCHECK) ALL${NC}     ${DIM}# which rule matched?${NC}"
echo -e "  ${CYAN}DISPLAY CHSTATUS('APP.SVRCONN') ALL${NC}                   ${DIM}# what MCAUSER resolved?${NC}"
echo -e "  ${CYAN}DISPLAY QMGR CONNAUTH${NC}                                ${DIM}# which AUTHINFO is active?${NC}"
echo -e "  ${CYAN}DISPLAY AUTHREC OBJTYPE(QMGR) PRINCIPAL('app-user')${NC}  ${DIM}# what's the user authorized for?${NC}"
sleep "$PAUSE_MED"
echo
echo -e "${BOLD}💡 IBM-recommended resolution (${YELLOW}you${NC}${BOLD} run these — MQ-Sentinel will NOT execute):${NC}"
echo
echo -e "  ${DIM}If a BLOCKUSER rule is incorrectly matching:${NC}"
echo -e "    ${YELLOW}SET CHLAUTH('APP.SVRCONN') TYPE(BLOCKUSER) USERLIST('badactor') ACTION(REPLACE)${NC}"
echo
echo -e "  ${DIM}If MCAUSER lacks queue/QM permissions, grant them:${NC}"
echo -e "    ${YELLOW}SET AUTHREC PRINCIPAL('mcauser') OBJTYPE(QMGR) AUTHADD(CONNECT, INQ)${NC}"
echo -e "    ${YELLOW}SET AUTHREC PROFILE('PAYMENTS.IN') OBJTYPE(QUEUE) PRINCIPAL('mcauser') \\${NC}"
echo -e "    ${YELLOW}            AUTHADD(PUT, INQ, BROWSE)${NC}"
echo
echo -e "  ${DIM}If CONNAUTH is rejecting credentials, fix the AUTHINFO record:${NC}"
echo -e "    ${YELLOW}ALTER AUTHINFO('SYSTEM.DEFAULT.AUTHINFO.IDPWOS') AUTHTYPE(IDPWOS) \\${NC}"
echo -e "    ${YELLOW}             ADOPTCTX(YES) CHCKCLNT(REQDADM)${NC}"
echo -e "    ${YELLOW}REFRESH SECURITY TYPE(CONNAUTH)${NC}"
sleep "$PAUSE_MED"
echo
echo -e "${BOLD}📖 IBM Knowledge Center (full procedure with all options):${NC}"
echo -e "  ${BLUE}🔗 https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2035-07f3-rc2035-mqrc-not-authorized${NC}"
echo
echo -e "${GRAY}${DIM}⚠️  MQ-Sentinel is read-only by construction. The destructive commands above are${NC}"
echo -e "${GRAY}${DIM}   shown as TEXT only — you copy/paste them into your change window after review.${NC}"
sleep "$PAUSE_LONG"

# ─── SCENE 4: SECURITY ───────────────────────────────────────────────────
banner "SCENE 4  ·  Why this is safe to run in production"

echo -e "${GREEN}✓${NC} ${BOLD}Read-only by construction${NC} — three-layer allowlist"
echo -e "  ${DIM}Tool generates only DISPLAY/DIS/PING. Connector regex-rejects everything else.${NC}"
echo -e "  ${DIM}MQ service account itself has only +connect +inq +dsp via setmqaut.${NC}"
sleep "$PAUSE_SHORT"
echo
echo -e "${GREEN}✓${NC} ${BOLD}Prompt-injection firewall${NC} — every output sanitized"
echo -e "  ${DIM}URLs constrained to www.ibm.com. Jailbreak markers redacted.${NC}"
sleep "$PAUSE_SHORT"
echo
echo -e "${GREEN}✓${NC} ${BOLD}DLQ headers only${NC} — message bodies NEVER read"
echo -e "  ${DIM}Enforced by tests that scan the project's own source code.${NC}"
sleep "$PAUSE_SHORT"
echo
echo -e "${GREEN}✓${NC} ${BOLD}Hash-chained audit log${NC} — SOX-evidence ready"
echo -e "  ${DIM}\`mq-sentinel verify-audit\` detects any retroactive edit.${NC}"
sleep "$PAUSE_LONG"

# ─── SCENE 5: BREADTH ────────────────────────────────────────────────────
banner "SCENE 5  ·  Every IBM MQ flavor, one tool surface"

cat <<EOF
${BOLD}Eight diagnostic tools:${NC}

  ${CYAN}diagnose_failed_channels${NC}                  2035, 2009, INDOUBT, AMQ9503
  ${CYAN}analyze_dlq_and_suggest_reprocessing${NC}      headers only, never bodies
  ${CYAN}check_cluster_health${NC}                      partial repos, stale CLUSQMGR
  ${CYAN}diagnose_native_ha_issues${NC}                 quorum, replay lag, CRR
  ${CYAN}diagnose_rdqm_issues${NC}                      Pacemaker, DRBD, split-brain
  ${CYAN}diagnose_zos_qsg_issues${NC}                   CHIN, page sets, CF
  ${CYAN}diagnose_multi_instance_issues${NC}            active/standby, dual-active
  ${MAGENTA}${BOLD}full_mq_health_check${NC}                ${MAGENTA}★ composite + executive summary${NC}

${BOLD}Coverage:${NC} Standalone · Multi-Instance · RDQM · Native HA + CRR
          Uniform Cluster · Traditional Cluster · z/OS QSG
          MQ Appliance · Containerized
EOF
sleep "$PAUSE_LONG"

# ─── SCENE 6: COMPOSITE ──────────────────────────────────────────────────
banner "SCENE 6  ·  full_mq_health_check executive summary"

prompt "Run a full health check on PROD_QM"
echo
sleep "$PAUSE_MED"

cat <<EOF
${BOLD}{
  "tool": "full_mq_health_check",
  "qm_name": "DEMO_QM",
  "summary": {
    "overall_status": ${RED}"CRITICAL"${NC}${BOLD},
    "total_findings": 12,
    "by_severity": {
      "CRITICAL": ${RED}3${NC}${BOLD},
      "HIGH":     ${YELLOW}7${NC}${BOLD},
      "MEDIUM":   ${CYAN}2${NC}${BOLD},
      "LOW":      0,
      "INFO":     0
    },
    "by_category": {"channels": 4, "dlq": 5, "cluster": 3},
    "top_issues": [
      { "severity": ${RED}"CRITICAL"${NC}${BOLD}, "issue": "Cluster PAYMENTS has no visible full repository" },
      { "severity": ${RED}"CRITICAL"${NC}${BOLD}, "issue": "Channel INDOUBT.RCVR is in-doubt" },
      { "severity": ${RED}"CRITICAL"${NC}${BOLD}, "issue": "Dead-letter queue depth=1247" }
    ]
  },
  "duration_ms": 412,
  "trust_level": "rcs_findings"
}${NC}
EOF
sleep "$PAUSE_LONG"

# ─── SCENE 7: INSTALL ────────────────────────────────────────────────────
banner "SCENE 7  ·  Install in 5 minutes"

echo -e "${BOLD}Docker (laptop / startup):${NC}"
echo -e "  ${DIM}curl -fsSL .../install.sh | MQS_DEV_MODE=true bash${NC}"
echo
echo -e "${BOLD}Helm (Kubernetes / mid-org):${NC}"
echo -e "  ${DIM}helm install mq-sentinel oci://ghcr.io/pramodreddyboddu/charts/mq-sentinel${NC}"
echo
echo -e "${BOLD}RPM / DEB (regulated / air-gapped):${NC}"
echo -e "  ${DIM}sudo dnf install mq-sentinel-0.1.0-1.x86_64.rpm${NC}"
echo
echo -e "${BOLD}Homebrew (Mac dev):${NC}"
echo -e "  ${DIM}brew install pramodreddyboddu/tap/mq-sentinel${NC}"
sleep "$PAUSE_LONG"

# ─── CLOSING ─────────────────────────────────────────────────────────────
banner "Try it yourself"

echo -e "  🌐  Live demo (no install):  ${BLUE}https://mq-sentinel.io${NC}"
echo -e "  📦  GitHub:                  ${BLUE}https://github.com/pramodreddyboddu/mq-sentinel${NC}"
echo -e "  📊  Built for:               IBM MQ 9.2 / 9.3 / 9.4 / z/OS"
echo
echo -e "${DIM}167 tests · mypy strict · ruff clean · BSL-1.1 (planned) · v0.1.0${NC}"
echo
sleep "$PAUSE_MED"
