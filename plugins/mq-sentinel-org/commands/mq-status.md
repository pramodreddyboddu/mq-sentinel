---
description: Show MQ-Sentinel's mode (demo or live) and the queue managers you can diagnose
---

Call the MQ-Sentinel `health` tool and report:

- Version, environment, and whether it's using **live** connections or **demo fixtures**.
- A table of the queue managers it lists: name, environment, topology hint.

If it's in demo mode, say that the only queue manager is `DEMO_QM`, and that live queue managers are configured on the server with `MQS_SERVER_INVENTORY_DIR` and `MQS_SERVER_SECRETS_DIR` (see the plugin README). If the list is empty in live mode, either the server's inventory has no queue managers, or none of them are readable by this user. On a shared org server, that usually means the user's SSO groups don't map to `nonprod-read` or `prod-read`.
