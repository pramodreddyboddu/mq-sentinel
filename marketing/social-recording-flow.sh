#!/usr/bin/env bash
# Troubleshooting flow for MQ-Sentinel
# Produces clean terminal output suitable for screen recording.

set -euo pipefail

# Colors for realistic terminal look
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

pause() {
  sleep "${1:-0.8}"
}

type_slow() {
  local text="$1"
  for ((i=0; i<${#text}; i++)); do
    printf '%s' "${text:$i:1}"
    sleep 0.03
  done
  echo
}

clear

# Start directly with realistic troubleshooting session
echo
pause 0.3

# === 1. mq-sentinel info ===
echo -e "${GREEN}${BOLD}❯${NC} ${BOLD}mq-sentinel info${NC}"
pause 0.4

cat << 'INFO'
MQ-Sentinel
========================================
Version: 0.3.0
Tools:   8 diagnostic tools (all read-only)
Flavors: Standalone, Multi-Instance, RDQM, Native HA (+CRR), Uniform/Traditional Cluster, z/OS QSG, Appliance, Containerized

Security highlights:
  • 3-layer read-only enforcement
  • Prompt-injection firewall + output sanitizer
  • Verified IBM Knowledge Center citations (CI-checked daily)
  • OIDC + RBAC with prod/nonprod scoping
  • Hash-chained tamper-evident audit
  • Distroless + signed images + SBOM

Try:
  mq-sentinel tools
  mq-sentinel doctor
  mq-sentinel serve

Docs: https://github.com/pramodreddyboddu/mq-sentinel
INFO

pause 1.5

# === 2. mq-sentinel doctor ===
echo -e "${GREEN}${BOLD}❯${NC} ${BOLD}mq-sentinel doctor${NC}"
pause 0.4

cat << 'DOCTOR'
MQ-Sentinel Doctor
========================================
Version: 0.3.0
Python:  3.12.13 (/Users/.../python3)
Platform: macOS-...

✗ pymqi NOT installed
  Real MQ connections will not work.
  For development/demo use the built-in fixtures (make demo).
  To use against real QMs: see docs/byom.md

✓ Configuration loaded successfully
  Environment: dev
  Transport default: stdio
  Auth disabled for local dev: False
  Audit log: audit.jsonl
  Read-only enforcement: True

✓ Audit log path is writable

Doctor complete. Most issues are fixed by:
  - uv sync --all-extras --dev
  - Setting the right MQS_* environment variables
  - Running inside the official container image
DOCTOR

pause 1.5

# === 3. mq-sentinel tools ===
echo -e "${GREEN}${BOLD}❯${NC} ${BOLD}mq-sentinel tools${NC}"
pause 0.4

cat << 'TOOLS'
MQ-Sentinel Diagnostic Tools
========================================
• diagnose_failed_channels
  Channel state + AMQERR analysis (2035, 2009, 2059, INDOUBT, AMQ9202/9208/9503)

• analyze_dlq_and_suggest_reprocessing
  Dead-letter queue inspection (HEADERS ONLY — bodies never read)

• check_cluster_health
  Partial repos, stale CLUSQMGR, suspended members, unhealthy cluster channels

• diagnose_native_ha_issues
  Replica state, quorum, log replay lag, split-brain, CRR lag

• diagnose_rdqm_issues
  Pacemaker quorum, offline nodes, DRBD state, split-brain

• diagnose_zos_qsg_issues
  QSG members, CHIN, page sets, buffer pools, CF structures

• diagnose_multi_instance_issues
  Active/standby state, dual-active split, standby permission, failover

• full_mq_health_check
  Composite: channels + DLQ + cluster against one QM. Executive summary + ranked findings

All tools are strictly read-only.
Use via any MCP client (Claude Desktop, Cursor, etc.) or the HTTP API.
Tip: mq-sentinel tools --json
TOOLS

pause 1.8

# Real troubleshooting flow (no meta text in output)
echo -e "${GREEN}${BOLD}❯${NC} ${BOLD}mq-sentinel doctor${NC}"
pause 0.4
echo -e "${GRAY}Checking environment and basic config...${NC}"
pause 0.6

cat << 'DOCTOR2'
✓ Configuration loaded
✓ Audit path writable
  (pymqi not installed — using fixture mode for this check)
DOCTOR2

pause 0.8

echo
echo -e "${GREEN}${BOLD}❯${NC} ${BOLD}mq-sentinel info${NC}"
pause 0.4

cat << 'INFO2'
MQ-Sentinel v0.3.0 — 8 read-only tools
Covers all 10 IBM MQ topologies.
Security: read-only enforcement + sanitizer + verified KC citations.
INFO2

pause 0.8

echo
echo -e "${GREEN}${BOLD}❯${NC} ${BOLD}Why is PROD_QM erroring?${NC}"
pause 0.5

echo -e "${GRAY}→ Running diagnose_failed_channels on PROD_QM${NC}"
pause 0.6

echo
echo -e "${MAGENTA}${BOLD}Result:${NC} HIGH: Channel APP.SVRCONN → 2035 NOT_AUTHORIZED"
echo
echo -e "${BOLD}Likely causes:${NC}"
echo "  - CHLAUTH rule blocking the user"
echo "  - MCAUSER missing +connect/+inq"
echo "  - CONNAUTH credential issue"
pause 0.6

echo
echo -e "${BOLD}Recommended next commands (read-only):${NC}"
echo -e "  ${CYAN}DISPLAY CHLAUTH('APP.SVRCONN') MATCH(RUNCHECK) ALL${NC}"
echo -e "  ${CYAN}DISPLAY CHSTATUS('APP.SVRCONN') ALL${NC}"
echo -e "  ${CYAN}DISPLAY QMGR CONNAUTH${NC}"
pause 0.6

echo
echo -e "${BOLD}IBM Knowledge Center reference:${NC}"
echo -e "  ${BLUE}https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2035-07f3-rc2035-mqrc-not-authorized${NC}"
pause 1.0

echo
echo -e "${BOLD}Security notes (why this is safe to use with AI):${NC}"
echo -e "${GREEN}✓${NC} 3-layer read-only (tool + connector + MQ permissions)"
echo -e "${GREEN}✓${NC} Prompt-injection firewall + sanitizer on all MQ output"
echo -e "${GREEN}✓${NC} DLQ tool reads headers only — bodies never touched"
echo -e "${GREEN}✓${NC} Hash-chained audit log"
pause 1.0

echo
echo -e "${BOLD}Full tool list (for reference):${NC}"
echo "  diagnose_failed_channels, analyze_dlq_and_suggest_reprocessing,"
echo "  check_cluster_health, diagnose_native_ha_issues, diagnose_rdqm_issues,"
echo "  diagnose_zos_qsg_issues, diagnose_multi_instance_issues, full_mq_health_check"
pause 0.8

echo
echo -e "${BOLD}Project:${NC} https://github.com/pramodreddyboddu/mq-sentinel"
echo -e "${GRAY}271+ tests · strict typing · production security model${NC}"

# End
echo
echo -e "${GRAY}────────────────────────────────────────────────────────────${NC}"
echo -e "${BOLD}Done.${NC}"