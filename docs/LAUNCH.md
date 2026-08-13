# How people find MQ-Sentinel (and how you get recognition)

You already built the product. Recognition is a **distribution** problem, not more features.

## The honest picture

MQ-Sentinel is a **niche enterprise** tool (IBM MQ + AI agents). It will not go viral like a consumer app. It *can* get you:

- Recruiter / hiring-manager respect (this is the strongest card)
- A few real MQ platform teams trying the demo
- A listing next to other MCP servers (Claude, Cursor, Grok users)

That is the right goal. One clean GitHub repo + one working demo + three public posts beats another month of features.

## Do these in order

### 1. GitHub is the home page (this repo)

People judge the README in 20 seconds. It must answer: what it is, why it's safe, how to try it in 90 seconds (`make demo`).

### 2. List it where MCP users search

| Where | What you do | Time |
|---|---|---|
| [Official MCP Registry](https://registry.modelcontextprotocol.io/) | Rebuild/push image `0.3.0` with the Docker label, then `mcp-publisher login github` + `publish` | 30–60 min |
| [Smithery](https://smithery.ai) | Add Server → connect `pramodreddyboddu/mq-sentinel` (`smithery.yaml` is already here) | 10 min |
| PulseMCP / Glama | Check a day later; many ingest the official registry automatically | 5 min |

There is **no** single “submit to Claude + ChatGPT + Gemini store.”

### 3. Make the demo impossible to fail

`make demo` must work on a laptop with **no IBM MQ**. That is how strangers try it.

### 4. Tell people (one week, then stop)

Copy from `marketing/` — do not rewrite from scratch.

| Day | Where | What |
|---|---|---|
| 1 | LinkedIn | Portfolio post (`marketing/portfolio-linkedin-post.md`) |
| 1 | X | Thread (`marketing/portfolio-x-thread.md`) |
| 2 | IBM MQ community | `marketing/community-ibm-post.md` |
| 3 | r/mcp + r/IBMMQ | Short: problem → demo command → GitHub link |

One post, then reply to comments. Do not spam.

### 5. ChatGPT (only if you care)

ChatGPT cannot run local stdio. You need a **public HTTPS** demo (`docs/http-transport.md`). Skip this until 1–4 are done.

## What “success” looks like in 30 days

- GitHub README + `make demo` works for a stranger
- Listed on official MCP Registry + Smithery
- 3 public posts live
- You can send one URL in a job conversation: “I built a read-only IBM MQ diagnostic MCP”

Stars are nice. **A hiring manager opening the repo** is the real win.

## Do not do next

- More diagnostic tools
- Another rewrite of the landing page
- Waiting until it feels “ready”

Ship the listing. Then talk about it.
