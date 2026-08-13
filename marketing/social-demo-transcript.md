# Social Demo Video Transcript (60-second version)

This is the exact flow and output from running the recommended social recording script.

Use this as reference when screen recording, or as captions.

---

**[0:00]** Terminal opens (clean prompt `❯ `, dark theme, 18pt font)

```
────────────────────────────────────────────────────────────
MQ-Sentinel Social Demo Recording
60-second flow for LinkedIn / X posts
────────────────────────────────────────────────────────────
```

**[0:05]**

```
❯ mq-sentinel info
```

(Full info output appears with security highlights)

**[0:18]**

```
❯ mq-sentinel doctor
```

(Doctor runs, shows ✓ checks and pymqi note)

**[0:32]**

```
❯ mq-sentinel tools
```

(List of all 8 tools with descriptions)

**[0:45]**

```
❯ make demo-fast
```

(Starts the main diagnosis demo)

```
SCENE: 3:00 AM. PagerDuty fires.
Your AMQERR.LOG on PROD_QM:
AMQ9999E: Channel program ended abnormally.
MQRC = 2035 (NOT_AUTHORIZED)

Old way: 90 minutes of logs...
New way: ask your AI.

❯ Why is PROD_QM erroring?

→ Claude calls: diagnose_failed_channels on DEMO_QM

🤖 Claude: HIGH: Channel APP.SVRCONN returned 2035 NOT_AUTHORIZED.

Root cause: The connecting principal failed authorization.

Diagnostic commands (read-only):
  DISPLAY CHLAUTH('APP.SVRCONN') MATCH(RUNCHECK) ALL
  ...

IBM-recommended fixes:
  SET AUTHREC ...

IBM Knowledge Center:
  https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2035-07f3-rc2035-mqrc-not-authorized

Why this is safe:
✓ Read-only by construction (3 layers)
✓ Prompt-injection firewall
✓ DLQ headers only
✓ Hash-chained audit log

8 tools. All 10 IBM MQ flavors covered.
  ... full_mq_health_check ★

Try it yourself
  GitHub: https://github.com/pramodreddyboddu/mq-sentinel
  Live demo: https://mq-sentinel.io

271+ tests · mypy strict · production-grade security
```

**[1:05]** Video ends on the GitHub link.

**End screen text suggestion (add in editing):**
"Ready to use today → github.com/pramodreddyboddu/mq-sentinel"

---

### Recording Tips for This Transcript

- Use `DEMO_SPEED=fast` or the custom `social-recording-flow.sh` script.
- Record at 1080p or higher.
- Font size 18pt+ so it's readable on mobile.
- Pause slightly on the IBM link and security bullets.
- End with the URL visible for 3-4 seconds.

Run this to generate the exact output for your recording:

```bash
cd Documents/Projects/mqmcp
bash marketing/social-recording-flow.sh
```

Then screen record while it runs.