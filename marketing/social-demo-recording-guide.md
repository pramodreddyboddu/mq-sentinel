# Demo Recording Guide (for LinkedIn + X)

Clean troubleshooting demo piece for your posts.

Goal: Record a short, authentic-looking terminal session showing the tool in use. The output looks like real troubleshooting (no "demo" or "recording" labels in the terminal).

---

## 1. How to Attach the Recording

### LinkedIn (Best platform for this)
- Write your post first.
- **Drag the video file directly** into the post composer (native upload).
- Do **NOT** upload to YouTube first and paste a link — LinkedIn heavily buries external video.
- Recommended: Post the text, then reply to your own post with the video + "Here's the 60-second demo:".

### X / Twitter
- Post the first tweet of the thread.
- Attach the video file directly to that first tweet.
- Keep the video under 140 seconds (X limit is generous now).

---

## 2. Quickest Way to Create a Good Recording (macOS)

### Step 0: Prep (2 minutes)
```bash
cd ~/Documents/Projects/mqmcp

# Make sure everything is up to date
git pull

# Test the demo once
make demo-fast
```

### Step 1: Make your terminal look professional
```bash
# Set a clean prompt (hides your username)
export PS1='❯ '

# Recommended font size for phone readability
# Open Terminal → Settings → Profiles → "Pro" → Text → 18pt or 20pt
```

Full-screen your terminal (green button).

### Step 2: Start recording
1. Press `⌘ + Shift + 5`
2. Choose **"Record Selected Portion"**
3. Drag a clean box around your terminal (leave a small margin)
4. Click **Record**

### Step 3: Run a short, social-friendly demo

Run this command (optimized for recording):

```bash
DEMO_SPEED=fast bash demo/run.sh
```

Or even better for social — run these commands manually while recording (more natural):

```bash
# 1. Show the new easy commands first
mq-sentinel doctor

# 2. Show what it can do
mq-sentinel tools

# 3. Quick overview
mq-sentinel info

# 4. The actual demo (the impressive part)
make demo-fast
```

Stop recording when the demo finishes + 2 seconds of the final "Try it yourself" screen.

### Use the clean flow script (easiest)

```bash
cd ~/Documents/Projects/mqmcp
bash marketing/social-recording-flow.sh
```

The script runs a realistic sequence:
- `mq-sentinel info`
- `mq-sentinel doctor`
- `mq-sentinel tools`
- Diagnosis example (2035 case + commands + security notes)
- Project link

**To record:**
- Prep terminal: `export PS1='❯ '`
- Full screen, 18pt+ font
- Start screen recording (⌘+Shift+5)
- Run the script
- Stop after the final "Done."

The printed output is pure troubleshooting — no "recording" or "social demo" text.

See `marketing/social-demo-transcript.md` for reference.

### Step 4: Quick edit (optional but recommended)
- Trim the beginning (remove any setup).
- Speed up boring parts by 1.2x if needed.
- Add a simple text overlay at the end: "Try it: github.com/pramodreddyboddu/mq-sentinel"

---

## 3. Recommended 60-Second Social Demo Flow

Record something like this order (very high conversion):

1. **0-8s**: Clean terminal → run `mq-sentinel info`
2. **8-18s**: Run `mq-sentinel doctor`
3. **18-28s**: Run `mq-sentinel tools`
4. **28-55s**: `make demo-fast` (the actual diagnosis magic)
5. **55-65s**: Final screen with GitHub URL visible

This shows:
- Modern CLI (new commands)
- Zero friction
- Real value in seconds

---

## 4. Alternative: Asciinema (lightweight, no video editing)

If you want something embeddable:

```bash
# Install
brew install asciinema

# Record
bash demo/record.sh

# The file will be at: demo/cast/mq-sentinel.cast

# Convert to GIF (great for LinkedIn)
brew install agg
agg demo/cast/mq-sentinel.cast demo/cast/mq-sentinel.gif
```

Then attach the `.gif` directly.

---

## 5. Pro Tips for Social Posts

- **Phone test**: Watch the recording on your phone before posting. Text must be readable.
- **No audio needed** for the first post — the terminal speaks for itself.
- **File size**: Keep under 50MB for easy uploads.
- **Thumbnail**: LinkedIn will use the first frame. Make sure the terminal looks clean when recording starts.

---

You're ready. Run the commands above and you'll have a strong demo piece in < 15 minutes.

Once you have the file, drop it into the posts we prepared earlier.