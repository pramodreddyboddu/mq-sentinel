# Launch posts — final drafts

These are ready to publish. Copy/paste, adjust the dates and URLs after
you tag v0.1.0 + the landing page is live.

---

## 1. Hacker News (Show HN)

### Title (3 options, pick one — A/B in mind)

**A — recommended:**

> Show HN: I built an AI diagnostic agent for IBM MQ that physically can't hallucinate fixes

**B — more technical:**

> Show HN: MQ-Sentinel – read-only IBM MQ diagnostics for AI agents, with a prompt-injection firewall

**C — most modest:**

> Show HN: Diagnose IBM MQ from Claude/Cursor with verified IBM doc citations

### Submission body (in the URL field, paste landing page URL: `https://mq-sentinel.io`)

### First comment (post immediately after submission — HN convention)

> Hi HN — solo dev here. Built this because every IBM MQ shop I've seen
> burns hours chasing 2035 NOT_AUTHORIZED errors, DLQ growth, Native HA
> replica lag, etc. Each fix is in the IBM docs, but the docs are huge
> and admins triage logs first.
>
> The interesting part for HN is the security architecture, not the MQ
> domain knowledge:
>
> 1. **Read-only by construction.** The MCP server has a static allowlist
>    of DISPLAY/DIS/PING-CHANNEL only. Destructive verbs are rejected by
>    three layers (tool, connector, MQ-side `setmqaut`). Even if you
>    fully compromised the MCP, MQ itself refuses ALTER/DELETE/START.
>
> 2. **Prompt-injection firewall.** MQ output (channel names, queue
>    names, log lines, DLQ headers) is untrusted — an attacker who can
>    write to a queue could otherwise seed jailbreak text into the LLM
>    context. Every output is sanitized: control/zero-width/tag chars
>    stripped, jailbreak markers redacted, URLs constrained to
>    www.ibm.com only.
>
> 3. **DLQ bodies never read.** The DLQ tool reads only MQDLH headers.
>    The guarantee is enforced by tests that scan the project's own
>    source code: a refactor that adds a `body` field to the dataclass
>    fails CI.
>
> 4. **Hash-chained audit log.** Every tool call is appended to an
>    immutable JSONL with SHA-256 chaining. SOX-evidence ready.
>
> 5. **The MCP itself never calls an LLM.** Pattern-matched RCS only,
>    cited to IBM Knowledge Center. Eliminates a whole class of
>    injection-to-model-call attacks.
>
> Eight tools across all 10 IBM MQ flavors (Standalone, Multi-Instance,
> RDQM, Native HA + CRR, Uniform Cluster, Traditional Cluster, z/OS QSG,
> MQ Appliance, Containerized). 167 tests, mypy strict, ruff clean.
>
> Live demo: https://demo.mq-sentinel.io (no install). GitHub:
> https://github.com/pramodreddyboddu/mq-sentinel.
>
> Looking for early users — if you run IBM MQ in production and want to
> try this against a non-prod QM, I'd love feedback. Especially curious
> whether the read-only-by-three-layers design holds up to your
> InfoSec's review.

### FAQ-defense comments (paste these as replies if asked)

**Q: "Why MCP and not just a CLI?"**

> Because the user already has Claude / Cursor open and is asking
> questions in natural language. Wrapping the diagnostic as an MCP tool
> means the AI client handles the UX — I just supply structured data.
> Side benefit: every team that adopts MCP for one thing tends to adopt
> it for everything, so distribution compounds.

**Q: "Won't the LLM still hallucinate even with verified citations?"**

> The MCP returns typed JSON: `{ issue, severity, root_cause, fix_steps,
> doc_refs, confidence, evidence }`. The client LLM narrates that.
> Hallucination of *content the MCP returned* is constrained because
> the LLM is summarizing structured data, not retrieving facts from
> training. Hallucination of *additional* content is on the LLM, but
> the user has the citations to verify in 1 click. It's not zero
> hallucination — it's "verifiable in seconds," which is the only useful
> bar.

**Q: "Could a malicious queue name break the firewall?"**

> Tested. There's an explicit `tests/security/test_sanitizer.py` with a
> corpus of injection attempts (queue names containing
> `Ignore previous instructions`, zero-width chars, unicode tag chars,
> URLs to evil hosts). All redacted before reaching the LLM. New attacks
> get added to the corpus.

**Q: "How does this compare to ITRS Geneos / Tivoli / IBM MQ Console?"**

> Different surface. Those are dashboards/alerters. This is a diagnosis
> tool for *after* the alert fires — it tells the on-call SRE *why* the
> queue is full, not *that* it's full. They complement; we don't replace.

### Best time to post

- **Tuesday or Wednesday, 9 AM Pacific (12 PM Eastern, 5 PM London).**
- Watch the comments for the first 90 minutes — that determines
  front-page ranking. Reply to every comment with substance.

---

## 2. LinkedIn — primary launch post

> 🚀 I'm shipping a side project that's been a year in the making.
>
> **MQ-Sentinel** — an AI diagnostic agent for IBM MQ that plugs into
> Claude / Cursor / Claude Code via the Model Context Protocol.
>
> If you've ever spent 90 minutes grepping AMQERR.LOG to find a 2035
> NOT_AUTHORIZED, this is for you.
>
> Ask Claude *"why is PROD_QM erroring"* and get back:
>   ✅ The root cause
>   ✅ The exact MQSC commands to investigate
>   ✅ A direct link to the IBM Knowledge Center page
>
> What makes this different from "ChatGPT writes some MQSC for you":
>
> 🛡️ **Read-only by construction.** The MCP server has a static allowlist
>    enforced in three layers — even a fully compromised server cannot
>    execute ALTER/DELETE/START.
>
> 🛡️ **Prompt-injection firewall.** Every output is sanitized — URLs
>    constrained to www.ibm.com, jailbreak markers redacted.
>
> 🛡️ **DLQ headers only — bodies are never read.** Enforced by tests
>    that scan the project's own source code.
>
> 🛡️ **Hash-chained audit log.** SOX-evidence ready.
>
> Coverage: every IBM MQ flavor — Standalone, Multi-Instance, RDQM,
> Native HA + CRR, Uniform Cluster, z/OS QSG, MQ Appliance,
> Containerized. Eight diagnostic tools, 167 tests passing, mypy strict.
>
> Try the live demo (no install): https://demo.mq-sentinel.io
> Source: https://github.com/pramodreddyboddu/mq-sentinel
>
> I'm looking for **the first ten teams** to deploy this against their
> real QMs. DM me — I'd love feedback, and I'll personally help you
> through onboarding.
>
> #IBMMQ #MessageQueuing #AI #MCP #ClaudeAI #SiteReliability
> #Observability #Banking #Mainframe #zOS #Kubernetes #DevOps
> #EnterpriseSoftware

### LinkedIn — IBM MQ groups variant

> Sharing this with the IBM MQ community specifically because the
> design choices may be controversial:
>
> 1. **Read-only by code, not policy.** The MCP refuses to issue
>    anything that isn't DISPLAY/DIS/PING. Even if a destructive verb
>    leaked into a recommendation string, the connector would reject
>    it before it reached MQ.
>
> 2. **Every recommendation cites IBM Knowledge Center.** No invented
>    fixes. No URLs to non-IBM sources.
>
> 3. **DLQ bodies are never returned.** Headers + reason codes only.
>
> 4. **The MCP server doesn't call an LLM** — pattern-matched RCS only.
>    The AI client (Claude/Cursor) narrates the structured response.
>
> Curious whether this design fits your prod posture.
>
> Live demo (no install): https://demo.mq-sentinel.io

---

## 3. community.ibm.com (TechXchange Community) — IBM MQ section

### Title

> Eliminating LLM hallucinations from IBM MQ diagnostics — a read-only
> MCP server pattern

### Post body

> Hi all — long-time MQ admin, first-time forum poster on this side of
> the keyboard. Wanted to share a design pattern from a side project I'm
> shipping, in case the community has feedback on the approach.
>
> The problem: AI assistants (Claude, ChatGPT, Cursor) are great at
> reading IBM MQ output, but they sometimes invent fixes that aren't
> in the docs. For our admins, that's worse than no answer — they end
> up running ALTER QMGR commands that "the AI suggested" against
> production QMs.
>
> The pattern I landed on:
>
> **1. The diagnostic agent is its own MCP server, separate from the
>    AI client.** It runs as a service, exposes typed JSON tools, and
>    never calls an LLM itself.
>
> **2. The agent enforces read-only at three layers:**
>    - The tool layer only ever generates DISPLAY/DIS/PING-CHANNEL
>      commands.
>    - The connector layer has a static regex allowlist that rejects
>      anything else (including multi-statement / NUL-injected /
>      case-obfuscated bypasses — there's a negative-test corpus).
>    - The MQ service account itself is granted only +connect +inq
>      +dsp via setmqaut. Even if the upper layers bug out, MQ refuses.
>
> **3. Every recommendation cites IBM Knowledge Center.** A curated
>    registry maps (mq_version, reason_code) → KC URL. The output
>    sanitizer enforces a URL allowlist of www.ibm.com — any other
>    URL is redacted before reaching the AI client. The AI literally
>    cannot show your admin a fake doc link, because the link never
>    leaves the server intact.
>
> **4. DLQ inspection reads only MQDLH headers — never message bodies.**
>    Enforced in code by tests that scan the dataclass fields for
>    forbidden names like `body`, `payload`, `data`. PII / payment /
>    PHI never leaves the connector.
>
> **5. Hash-chained audit log.** Every tool call is recorded with
>    SHA-256 chaining; tampering with any past record breaks the chain.
>    Quarterly auditor evidence is `mq-sentinel verify-audit`.
>
> Tools cover the obvious cases (failed channels, DLQ analysis,
> cluster health, Native HA, RDQM, MIQM) and z/OS QSG (CHIN, page sets,
> buffer pools, CF structures). The composite full_mq_health_check
> ranks findings by severity and produces an executive summary.
>
> Live demo (no install, sandboxed fixtures, anyone can hit it):
> https://demo.mq-sentinel.io
>
> Source: https://github.com/pramodreddyboddu/mq-sentinel
>
> Two questions for the community:
>
> 1. Is the three-layer read-only design overkill, or correctly
>    paranoid? I'm genuinely curious if anyone's seen a way it could
>    fail.
>
> 2. The KC URL registry is curated by hand from MQ 9.2 / 9.3 / 9.4
>    docs. If you spot a wrong URL or a missing reason code, I'd
>    really appreciate a GitHub issue.
>
> Thanks for reading — happy to answer questions, and if anyone wants
> to point this at a non-prod QM in their estate, I'd love feedback.

---

## 4. r/IBMMQ — short form

### Title

> I built a read-only AI diagnostic agent for IBM MQ. Read-only is
> enforced by code, not policy.

### Body

> One-liner: ask Claude / Cursor *"diagnose channels on PROD_QM"* and
> get back root cause + exact MQSC fix commands + IBM KC link, in
> 3 seconds.
>
> The relevant design choices:
>
> - Static allowlist of DISPLAY/DIS/PING-CHANNEL. Destructive verbs
>   rejected at three layers.
> - DLQ tool reads MQDLH headers only — bodies never returned.
> - Output sanitizer constrains all URLs to www.ibm.com.
> - Hash-chained tamper-evident audit log.
> - Coverage: Standalone, Multi-Instance, RDQM, Native HA + CRR,
>   Uniform Cluster, z/OS QSG.
>
> Live demo (no install): https://demo.mq-sentinel.io
>
> GitHub: https://github.com/pramodreddyboddu/mq-sentinel
>
> Free / open. Looking for early users to validate against real QMs.

---

## 5. Five IBM Champions — DM template

> Hi {Name},
>
> Big admirer of your work on {specific_thing — make this real, not generic}.
> I've been building a tool that I think you'd have strong opinions on,
> and I'd love your feedback before I push wider.
>
> **MQ-Sentinel** — a read-only diagnostic MCP server for IBM MQ. The
> design choice that may interest you: the server enforces read-only at
> three layers (tool / connector / MQ-side authrec), and every
> recommendation cites IBM Knowledge Center via a curated URL registry
> (KC links for reason codes 2035, 2080, 2030, 2051, 2053, 2079;
> AMQ9202, 9208, 9456, 9484, 9503, 9508, 9764, AMQ3209; plus topic
> pages for CRR, Native HA quorum loss, RDQM split-brain, etc.).
>
> 2-min demo: {YouTube URL once recorded}
> Live sandbox you can curl: https://demo.mq-sentinel.io
> Source: https://github.com/pramodreddyboddu/mq-sentinel
>
> If you have 10 minutes to look, I'd value any feedback — particularly
> whether the curated KC registry has gaps, or whether the read-only
> claim has a hole I'm not seeing.
>
> No ask beyond that. Thanks for the work you do for the MQ community.
>
> — {Your real name}

### Targets (verify they're current MQ Champions before sending)

- Morag Hughson (MQGem) — independent voice, runs MQGem newsletter
- Marc Luescher — IBM MQ specialist, prolific Stack Overflow answerer
- Neil Casey — IBM MQ Champion, conference speaker
- Pete Broadbent — long-time MQ practitioner
- Tim Zielke — MQ specialist
- (Plus any IBM Champion in your LinkedIn 2nd-degree network — those
  warm intros convert at 10× the cold rate.)
