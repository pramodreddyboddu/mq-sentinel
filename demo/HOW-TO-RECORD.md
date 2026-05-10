# How to record the MQ-Sentinel demo for LinkedIn / Twitter / YouTube

You have **20 minutes** of work between you and a shareable 90-second video.

---

## ⏱ The 20-minute play

### Step 1 (2 min) — Pre-flight check, terminal looks good

```bash
cd ~/Documents/Projects/mqmcp
make demo
```

Watch it run. Make sure:
- Colors render correctly (red for the AMQERR snippet, green for the prompt, yellow for IBM-recommended commands, blue for the IBM doc link).
- The "Scene 3" remediation block shows.
- It ends with "Try it yourself" + GitHub URL.

If anything looks broken, tell me what and I'll fix it.

### Step 2 (3 min) — Style your terminal for recording

Open **Terminal.app** on macOS.

| Setting | Value | Why |
|---|---|---|
| Window | Full screen (green dot, top-left) | Maximum readability on mobile |
| Profile | Settings → Profiles → "Pro" (dark theme) | Real-engineer vibe |
| Font | "JetBrains Mono" or "SF Mono", **18pt** | Readable on a phone screen |
| Prompt | Run: `export PS1='❯ '` | Hides your username/hostname |
| Clear screen | Cmd+K right before recording | No leftover clutter |

### Step 3 (1 min) — Start screen recording

Press **⌘ + Shift + 5**. A toolbar appears at the bottom.

- Click **"Record Selected Portion"** (the rectangle icon)
- Drag a clean box around your terminal window (leave ~20px margin)
- Click **Record**

### Step 4 (90 sec) — Run the demo

```bash
make demo-fast
```

Don't touch anything. Watch the 90-second demo play. When you see the closing "Try it yourself" message, wait 2 seconds.

### Step 5 (10 sec) — Stop recording

Press **⌘ + Shift + 5** again, click **Stop** in the menu bar (top right).

The video saves to your **Desktop** as `Screen Recording 2026-05-04 at H.MM.SS.mov`.

### Step 6 (5 min) — Preview + decide

Double-click the `.mov` file. Watch the whole thing back.

**Re-record if any of these are true:**
- You see your username/hostname in the prompt (set `PS1='❯ '` and try again)
- Text is too small to read on a phone (increase font to 18pt, full-screen)
- Colors look weird (set TERM=xterm-256color before running)
- A scene cut off (the window was too small — make it bigger)

**Move on if:**
- It plays cleanly start to finish in ~90 seconds
- Scenes 1 through 7 are all visible

### Step 7 (5 min) — Post it

#### Tuesday's Day 1 post (already done) → drop the video into the comments

```
🎬 The 90-second demo (running locally against bundled fixtures — no live MQ required):

[drag the .mov file into LinkedIn]

Try it yourself: github.com/pramodreddyboddu/mq-sentinel
```

#### Or hold it for Day 2 post (recommended — see below)

---

## 🎬 What the video shows (scene-by-scene)

| Scene | What viewers see | Why it's there |
|---|---|---|
| 1 | Red AMQERR.LOG nightmare | Empathy hook for MQ admins |
| 2 | One natural-language Claude prompt | The UX (no commands required from user) |
| 3 | Root cause + diagnostic DISPLAYs + **IBM-recommended fix commands** + IBM doc link | The "wow" moment — 3-second answer that's complete |
| 4 | Four security guarantees | Trust signal for InfoSec viewers |
| 5 | Eight tools + 10 IBM MQ flavors covered | Breadth |
| 6 | `full_mq_health_check` executive summary JSON | What ships to PagerDuty/Slack |
| 7 | Three install paths in 3 commands | "I could try this tomorrow" |
| Close | Try-it-yourself CTA + GitHub URL | Conversion |

---

## 🚫 Common mistakes to avoid

1. **Don't speak over the recording.** The demo speaks for itself. If you want narration, record audio separately in iMovie afterward and use the [`marketing/screencast-script.md`](../marketing/screencast-script.md) voiceover script.

2. **Don't slow down the demo for the recording.** `make demo-fast` is the right speed — viewers can pause if they want detail.

3. **Don't upload to YouTube first and paste the link on LinkedIn.** LinkedIn buries external video. Upload the `.mov` directly to LinkedIn as a native video.

4. **Don't edit the video to add a "title card" intro.** Every second of intro = 30% of viewers gone. The AMQERR snippet IS the hook.

5. **Don't tag everyone you know on the post.** LinkedIn penalizes scattershot tags. Only tag 2-3 specific people (e.g., an IBM Champion whose work you reference).

---

## ✅ Verification command

Run this right before recording — confirms the demo and tool are both at v0.2.0:

```bash
make demo --version 2>/dev/null; mq-sentinel version; echo "---"; head -1 demo/cached-output/diagnose_failed_channels.json
```

Should print `0.2.0` and start of the JSON.
