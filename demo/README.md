# MQ-Sentinel demo — recordable terminal walkthrough

A self-running, screen-recording-ready demo. Show it to people in 3 ways:

1. **Run it live** — open a terminal, run `bash demo/run.sh`, hit ⌘+Shift+5 to screen-record.
2. **Record as asciinema cast** — `bash demo/record.sh` produces a shareable browser-playable cast.
3. **Embed in README / website** — convert the cast to GIF/SVG, drop the image.

The demo is **deterministic, dependency-free, and offline-runnable**. It uses
the bundled fixture sandbox — no live IBM MQ required.

## Quick run (any laptop, ~90 seconds)

```bash
bash demo/run.sh
```

Speed control:

```bash
DEMO_SPEED=slow   bash demo/run.sh   # explanation-friendly
DEMO_SPEED=normal bash demo/run.sh   # default
DEMO_SPEED=fast   bash demo/run.sh   # recording-friendly
```

Force cached output (skips live MCP, always works):

```bash
DEMO_MODE=cached bash demo/run.sh
```

## Record a screen video — the simplest path

### macOS

```bash
# 1. Open Terminal, full-screen the window, 14-16pt font, dark theme.
# 2. Hit ⌘+Shift+5 → Record Selected Portion → drag a clean rectangle around the terminal.
# 3. Click Record.
DEMO_SPEED=fast bash demo/run.sh
# 4. Hit ⌘+Shift+5 again to stop. Saves to Desktop.
# 5. Upload to YouTube as Unlisted, embed on landing page.
```

### Linux / Windows

Use **OBS Studio**, **Kap**, or **ScreenStudio**. Same flow — clean terminal,
run the script, stop recording, upload.

## Record an asciinema cast — the embeddable path

asciinema casts are tiny (≤50 KB), play in any browser, and embed in
GitHub READMEs.

```bash
brew install asciinema      # macOS
# or: pip install asciinema  (Linux/Windows)

bash demo/record.sh
# → demo/cast/mq-sentinel.cast
```

Then:

```bash
# Preview locally:
asciinema play demo/cast/mq-sentinel.cast

# Upload to asciinema.org (gets you a shareable URL like asciinema.org/a/123456):
asciinema upload demo/cast/mq-sentinel.cast

# Convert to animated GIF (for LinkedIn, Twitter):
brew install agg
agg demo/cast/mq-sentinel.cast demo/cast/mq-sentinel.gif

# Convert to animated SVG (for README, scales infinitely):
npm install -g svg-term-cli
svg-term --in demo/cast/mq-sentinel.cast --out demo/cast/mq-sentinel.svg \
         --window --no-cursor --width 100 --height 32
```

## Embed in the main README

After uploading to asciinema.org, add to README.md right under the badges:

```markdown
[![asciicast](https://asciinema.org/a/REPLACE_WITH_ID.svg)](https://asciinema.org/a/REPLACE_WITH_ID)
```

Or, after generating the SVG locally:

```markdown
![MQ-Sentinel demo](demo/cast/mq-sentinel.svg)
```

Or, with the GIF (works on platforms that don't render SVG animations, like
LinkedIn):

```markdown
![MQ-Sentinel demo](demo/cast/mq-sentinel.gif)
```

## Embed in the landing page

In `web/index.html`, replace the placeholder hero "before/after" cards with:

```html
<script src="https://asciinema.org/a/REPLACE_WITH_ID.js" id="asciicast-REPLACE_WITH_ID" async></script>
```

Or for a self-hosted version (no asciinema.org dependency), use the
asciinema-player library:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/asciinema-player@3/dist/bundle/asciinema-player.css" />
<div id="demo-player"></div>
<script src="https://cdn.jsdelivr.net/npm/asciinema-player@3/dist/bundle/asciinema-player.min.js"></script>
<script>
  AsciinemaPlayer.create('demo/cast/mq-sentinel.cast', document.getElementById('demo-player'), {
    autoPlay: true, loop: true, theme: 'monokai', cols: 100, rows: 32
  });
</script>
```

## Demo structure (7 scenes, ~90 seconds at `fast` speed)

| Scene | What it shows | Why it's there |
|---|---|---|
| 1 | 3 AM PagerDuty page + AMQERR.LOG nightmare | Empathy hook for MQ admins |
| 2 | One natural-language question in Claude Code | Shows the UX, no commands |
| 3 | Claude's response: root cause + DISPLAY steps + IBM KC link | The "wow" — 3-second answer |
| 4 | Four security guarantees | Trust signal for InfoSec viewers |
| 5 | The eight tools + flavor coverage | Breadth — every IBM MQ flavor |
| 6 | `full_mq_health_check` executive summary JSON | What ships to PagerDuty/Slack |
| 7 | Three install paths in one screen | "I could try this tomorrow" |
| 8 | Try-it-yourself CTA + GitHub URL | Conversion |

## When to re-record

Re-record whenever any of the following change:
- The headline number of tools (currently 8).
- The headline test count (currently 167).
- The list of supported flavors.
- The install commands.
- The landing-page URL.

The script keeps these as plain text near the top — search for the section
markers `SCENE 5` and `SCENE 7` to update.

## Cached output

The `cached-output/` directory holds canned RCS responses used when
`DEMO_MODE=cached` (which is automatic when the `mq-sentinel` CLI isn't on
$PATH). Keep these in sync with the real demo-sandbox fixtures by running:

```bash
# Regenerate cached output from live fixtures (requires uv pip install -e .):
DEMO_MODE=live bash demo/run.sh > /tmp/refresh.txt  # not strictly automated; refresh manually if needed
```

The cached output is intentionally check-in safe — no PII, no real
credentials, just structured RCS JSON.

## Tips for a high-conversion demo

- **Terminal background:** dark theme (people associate dark terminals with
  "real engineers"). The default macOS Terminal "Pro" theme works.
- **Font:** monospace at 14–16pt. JetBrains Mono / Fira Code / SF Mono.
  Whatever has good ligatures for `=>`, `!=`, `->`.
- **Window size:** ~100 cols × 32 rows. Matches GitHub README rendering.
- **Audio:** for a screen video, record audio narration over the
  pre-recorded run. Use the script in `marketing/screencast-script.md`
  for the voiceover (~110 seconds).
- **Don't show your hostname or username in the prompt.** Set
  `PS1='❯ '` before recording.
- **Resize the window before starting.** Mid-recording resize looks bad.
- **Test playback on a phone.** Most LinkedIn/Twitter clicks come from
  mobile — confirm text is readable.

## What this isn't

This demo doesn't connect to a real IBM MQ Queue Manager. The output is
either:
- Live RCS findings from MQ-Sentinel against the bundled fixture sandbox
  (DEMO_MODE=live, requires `uv pip install -e .`), or
- Pre-baked RCS JSON identical to what the live path produces (DEMO_MODE=cached).

Both paths surface real seeded faults — the same ones the integration
test suite verifies. Nothing in the demo is invented for marketing.
