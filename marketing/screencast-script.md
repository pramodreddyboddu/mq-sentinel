# 2-Minute Screencast — "MQ-Sentinel in 120 seconds"

The video is the single most-shared artifact you'll produce. Get this
right, every other channel funnels traffic to a 2-min YouTube link.

## Setup

- **Length target:** 110–130 seconds. Don't go longer; people drop off.
- **Resolution:** 1920×1080, 60fps. Record terminal at a font size that
  reads on a phone screen (≥18pt).
- **Audio:** USB mic if you have one (Blue Yeti / Samson Q2U); built-in
  laptop mic is acceptable for v1.
- **Tools:** macOS — built-in Screen Recording (Cmd-Shift-5) or
  ScreenStudio. Linux/Win — OBS.
- **Background music:** none (instantly more professional than overlay
  music).

## The 7 beats — read aloud, then record

### Beat 1 — Hook (0:00–0:08)

**On-screen:** terminal showing a real-looking AMQERR.LOG tail with red
2035 errors scrolling.

**Voiceover:**
> "Your IBM MQ admin gets paged at 3 AM. Channel 2035s on PROD_QM.
> Normally that's an hour of grepping logs. Watch what happens when
> Claude has MQ-Sentinel."

### Beat 2 — The prompt (0:08–0:18)

**On-screen:** Claude Code window. Type:
```
Why is PROD_QM erroring?
```

**Voiceover:**
> "One question. No commands. No knowledge of MQ required from the user."

### Beat 3 — The response (0:18–0:45)

**On-screen:** Claude responds (use a real recording from the demo
sandbox). Highlight the key parts as Claude writes them:
- "Channel APP.SVRCONN, reason 2035 NOT_AUTHORIZED"
- The fix steps (DISPLAY commands)
- The IBM Knowledge Center link

**Voiceover:**
> "Three seconds. Root cause. The exact MQSC commands to investigate.
> And — this part matters — every link goes to ibm.com/docs. The MCP
> physically cannot cite a fake URL. There's an allowlist."

### Beat 4 — Why this is different (0:45–1:05)

**On-screen:** Show the source file `src/mq_sentinel/security/allowlist.py`
in an editor, scrolling through `_MQSC_ALLOWED_VERBS = frozenset({"DISPLAY", "DIS", "PING"})`.

**Voiceover:**
> "Read-only is enforced by code, not policy. Three layers: the tool
> only ever issues DISPLAY. The connector rejects anything else. And the
> MQ service account itself only has DSP+INQ+CONNECT permissions. Even
> if every layer above failed, MQ would refuse the destructive command."

### Beat 5 — The breadth (1:05–1:30)

**On-screen:** quickly fan through a terminal showing each tool against
the demo sandbox:
```
diagnose_failed_channels    → 2035, INDOUBT, AMQ9503E
analyze_dlq_and_suggest...  → 1247 messages, 4 reasons grouped
diagnose_native_ha_issues   → replica disconnect, CRR lag 420s
diagnose_rdqm_issues        → split-brain, Pacemaker offline
diagnose_zos_qsg_issues     → CHIN STOPPED, page set 97%
```

**Voiceover:**
> "Eight tools. Every IBM MQ flavor — Standalone, Native HA, RDQM,
> z/OS Queue Sharing Groups, the lot. The composite tool gives you an
> executive summary you can ship straight to PagerDuty."

### Beat 6 — Install (1:30–1:50)

**On-screen:** terminal:
```bash
curl -fsSL .../install.sh | MQS_DEV_MODE=true MQS_DEV_MODE_ACK_INSECURE=yes bash
```

Cut to: `helm install mq-sentinel oci://...`

Cut to: `dnf install mq-sentinel-0.1.0-1.x86_64.rpm`

**Voiceover:**
> "Installs in five minutes. Docker for laptops. Helm for Kubernetes.
> RPM and DEB for regulated environments. Distroless image, OIDC bearer
> auth, hash-chained audit log, signed releases. SOC 2-ready out of the
> box."

### Beat 7 — Call to action (1:50–2:00)

**On-screen:** the landing page hero, then the GitHub repo URL.

**Voiceover:**
> "It's open. Try the live demo at mq-sentinel.io — no install. Or grab
> it on GitHub. I'm looking for the first ten teams to deploy this
> against their real QMs. DM me if that's you."

## After recording

1. Upload to YouTube as Unlisted first; share with one trusted MQ admin
   for feedback. Adjust if needed.
2. Switch to Public the day before HN launch.
3. Embed on the landing page (replaces the placeholder hero image).
4. Cross-post to:
   - LinkedIn (native upload, not just a YouTube link — LinkedIn buries
     external video).
   - Twitter/X (direct upload).
   - r/IBMMQ.
   - community.ibm.com.

## Things NOT to do

- Don't show the "MG" personal brand — it dates the project. Record as
  if you were a small team.
- Don't show prompts being typed slowly. Record at 1.5× then voice-over.
- Don't include music. It distracts from the technical proof.
- Don't end with "thanks for watching." End with an action ("DM me").
