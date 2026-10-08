---
description: Show MQ-Sentinel's mode (demo or live) and the queue managers you can diagnose
---

Call the MQ-Sentinel `health` tool and report:

- Version, environment, and whether it's using **live** connections or **demo fixtures**.
- A table of the queue managers it lists: name, environment, topology hint.

If it's in demo mode, say that the only queue manager is `DEMO_QM`, and that live queue managers need `MQS_SERVER_INVENTORY_DIR` and `MQS_SERVER_SECRETS_DIR` (see the plugin README). If the list is empty in live mode, say the inventory directory has no `*.yaml` files or none of its QMs are readable by this principal.
