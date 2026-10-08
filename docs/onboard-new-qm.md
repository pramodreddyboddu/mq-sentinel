# How to Onboard a New Queue Manager

This runbook adds a live IBM MQ queue manager to MQ-Sentinel with **display-only** access. MQ-Sentinel never sends anything but allowlisted `DISPLAY` commands. The grants below mean MQ itself would also refuse anything else, even if MQ-Sentinel were compromised.

## Prerequisites

- MQ admin access to the queue manager (to define the channel and grant authorities)
- The IBM MQ C client on the MQ-Sentinel host, with `pymqi` installed. See [byom.md](byom.md).
- The command server running on the QM (`DISPLAY QMSTATUS CMDSERV` should show `RUNNING`)
- OIDC group mapping for the right tier (`prod-read` or `nonprod-read`) if you use the HTTP transport

## 1. Create a dedicated, display-only identity

Create an OS group and user on the QM host (for example group `mqsread`, user `mqsentinel`) that is **not** in `mqm`. Then grant only what PCF display commands need:

```bash
QM=PROD_QM_EU1
G=mqsread

# Connect and inquire/display the queue manager
setmqaut -m $QM -t qmgr -g $G +connect +inq +dsp

# Send PCF commands to the command server
setmqaut -m $QM -n SYSTEM.ADMIN.COMMAND.QUEUE -t queue -g $G +put +dsp

# Temporary reply queue for PCF responses
setmqaut -m $QM -n SYSTEM.DEFAULT.MODEL.QUEUE -t queue -g $G +get +dsp

# Display (never change) every queue, channel and listener
setmqaut -m $QM -n '**' -t queue    -g $G +dsp
setmqaut -m $QM -n '**' -t channel  -g $G +dsp
setmqaut -m $QM -n '**' -t listener -g $G +dsp

# Dead-letter queue: browse headers only. No +get, so messages can't be removed.
# Use the name from DISPLAY QMGR DEADQ.
setmqaut -m $QM -n SYSTEM.DEAD.LETTER.QUEUE -t queue -g $G +browse +inq +dsp
```

The OAM uses the most specific matching profile, so each explicitly named queue above repeats `+dsp`.

## 2. Define a channel for MQ-Sentinel

```mqsc
DEFINE CHANNEL(MQS.SVRCONN) CHLTYPE(SVRCONN) TRPTYPE(TCP) +
  SSLCIPH(ANY_TLS13_OR_HIGHER) SSLCAUTH(REQUIRED) +
  MAXINST(10) MAXINSTC(5) +
  DESCR('MQ-Sentinel read-only diagnostics')

* Only the MQ-Sentinel host(s), and require a password (CONNAUTH)
SET CHLAUTH(MQS.SVRCONN) TYPE(ADDRESSMAP) ADDRESS('10.20.30.*') +
  USERSRC(CHANNEL) CHCKCLNT(REQUIRED)
```

Keep the default `BLOCKUSER('*MQADMIN')` rule in place, so this channel can never be used with an administrator ID.

## 3. Store the credentials

Credentials live in a secrets directory, never in the inventory. Each `secret_ref` is a subdirectory:

```bash
SECRETS=/etc/mq-sentinel/secrets       # or ~/.mq-sentinel/secrets on a laptop
install -d -m 700 "$SECRETS/prod/eu1"
printf '%s' mqsentinel > "$SECRETS/prod/eu1/username"
printf '%s' "$PASSWORD" > "$SECRETS/prod/eu1/password"
# TLS (optional): a client key repository and certificate label
printf '%s' /etc/mq-sentinel/tls/client > "$SECRETS/prod/eu1/keystore_path"
printf '%s' mqsentinel-client > "$SECRETS/prod/eu1/cert_label"
chmod 600 "$SECRETS"/prod/eu1/*
```

MQ-Sentinel refuses a secret directory that is world-readable or group-writable. In Kubernetes, mount a Secret with the same file names.

## 4. Add the QM to the inventory

Every `*.yaml` in `MQS_SERVER_INVENTORY_DIR` is loaded at startup. Full example: [examples/org/inventory-example.yaml](../examples/org/inventory-example.yaml).

```yaml
qms:
  - qm_name: PROD_QM_EU1
    host: mq-prod-eu1.internal
    port: 1414
    channel: MQS.SVRCONN
    environment: prod            # dev | staging | prod | nonprod
    topology_hint: native_ha     # optional; topology is also auto-detected
    secret_ref: prod/eu1
    cipher_spec: ANY_TLS13_OR_HIGHER
```

Then start MQ-Sentinel in live mode:

```bash
export MQS_SERVER_INVENTORY_DIR=/etc/mq-sentinel/inventory
export MQS_SERVER_SECRETS_DIR=/etc/mq-sentinel/secrets
# MQS_SERVER_CONNECTOR defaults to "auto": live when an inventory is set
mq-sentinel serve
```

## 5. Verify

From your AI client, call the `health` tool. It should report `"connector": "live"` and list the QM. Then run a check:

> Run full_mq_health_check on PROD_QM_EU1 and summarize the findings with IBM links.

Over HTTP:

```bash
curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  http://mq-sentinel:8080/mcp/tools/call \
  -d '{"tool": "full_mq_health_check", "params": {"qm_name": "PROD_QM_EU1"}}'
```

## What live mode can and can't see

| Check | Source | Remote QM | MQ-Sentinel on the QM host (`host: localhost`) |
|---|---|---|---|
| Channels, DLQ, clusters, Native HA, z/OS QSG | MQSC over PCF | ✓ | ✓ |
| RDQM (Pacemaker, DRBD) and multi-instance standby | `rdqmstatus`, `crm_mon`, `drbdadm`, `dspmq` | – | ✓ |
| AMQERR log excerpts | error log files | – | – |

Host commands only run when the inventory `host` is `localhost`, so a remote QM is never diagnosed from another machine's state.

## Rollback

Remove the entry from the inventory and restart MQ-Sentinel. Then remove the access with `setmqaut ... -remove`, or `DELETE CHANNEL(MQS.SVRCONN)` once nothing uses it.

## Common issues

- **`failed to connect ... (MQRC 2035)`**: not authorized. Check the CHLAUTH rule, CONNAUTH, and step 1's `+connect`.
- **`(MQRC 2059)` / `(MQRC 2538)`**: the QM or listener isn't reachable. Check the host, port, firewall and listener.
- **Tools return no rows**: the command server is stopped, or the reply model queue lacks `+get`.
- **2393 / 2397 (TLS)**: the `cipher_spec` doesn't match the channel's `SSLCIPH`, or the key repository or certificate label is wrong.
- **`live connections need credentials`**: `MQS_SERVER_SECRETS_DIR` is unset.

## Approval

Treat this as a normal change: it grants read-only access to a production resource.
