# community.ibm.com Post — Final Draft (paste-ready)

**Where to post:** community.ibm.com → IBM MQ → "Discussions" section.

**Title:**

> A design pattern for hallucination-free AI tooling on IBM MQ: separating "what's wrong" from "here's the IBM-recommended fix"

**Tags:** `ibm-mq`, `ai`, `mcp`, `chlauth`, `connauth`, `automation`, `tooling`

---

## Post body — copy from below the line

---

Hi all,

Long-time MQ admin, first-time poster on this side of the keyboard. I want to share a design pattern from a side project I'm shipping, in case the community has feedback before I push it wider — and especially in case anyone has spotted holes in the approach.

### The problem

AI assistants (Claude, ChatGPT, Cursor, Claude Code) are increasingly used by ops teams to triage IBM MQ incidents at 3am. The pattern usually goes:

1. AMQERR.LOG fires, on-call engineer pastes the tail into an AI chat.
2. AI replies with "looks like a 2035 NOT_AUTHORIZED" and writes some plausible-looking MQSC: `ALTER CHLAUTH...`, `SET AUTHREC...`, `REFRESH SECURITY...`
3. Tired engineer copy-pastes the suggested MQSC into runmqsc on PROD.
4. Sometimes it works. Sometimes the AI hallucinated a flag that doesn't exist, or applied a fix that masks the symptom without addressing the cause, or — worst — modifies CHLAUTH in a way that opens up the channel to anyone.

The fundamental problem isn't that the AI doesn't know MQ. It's that:

- **Hallucination is undetectable to a tired SRE at 3am.** The output looks confident and plausible.
- **The AI controls both diagnosis AND execution** in a single context, so a wrong diagnosis writes itself into production.
- **No citation trail.** When the auditor asks "why did you run `ALTER CHLAUTH` on PROD_QM at 03:14?", the answer is "the AI said to."

### The design pattern I landed on

After building MQ-Sentinel — a read-only diagnostic MCP server for IBM MQ — I think the right pattern has four properties:

#### 1. Separate the AI from the QM with a read-only layer

The AI never connects to the QM directly. It calls a server (in this case, an MCP — Model Context Protocol — server) that owns the connection. That server has a static allowlist of MQSC verbs it will execute:

```python
_MQSC_ALLOWED_VERBS = frozenset({"DISPLAY", "DIS", "PING"})
```

`ALTER`, `DELETE`, `START`, `STOP`, `REFRESH`, `RESET`, `CLEAR`, `SET`, `DEFINE`, `RECOVER`, `BACKUP`, `SUSPEND`, `RESUME`, `MOVE`, `END` — all rejected by the server before they reach the QM. Multi-statement injection (`DISPLAY QMGR;ALTER QMGR`), case obfuscation, NUL injection, comment-hidden verbs — all rejected by a negative-test corpus.

Critically: this layer is enforced **even if the AI client asks the server to run something destructive**. The server says no. The AI's context window can't override the allowlist.

#### 2. Every response separates "diagnostic" from "IBM-recommended remediation"

Each finding the server returns has two distinct fields:

```json
{
  "issue": "Channel APP.SVRCONN returned MQRC 2035 (NOT_AUTHORIZED)",
  "fix_steps": [
    "DISPLAY CHLAUTH('APP.SVRCONN') MATCH(RUNCHECK) ALL",
    "DISPLAY CHSTATUS('APP.SVRCONN') ALL",
    "DISPLAY QMGR CONNAUTH"
  ],
  "remediation_steps": [
    {
      "scenario": "CHLAUTH BLOCKUSER rule incorrectly matching",
      "commands": [
        "SET CHLAUTH('APP.SVRCONN') TYPE(BLOCKUSER) USERLIST('badactor') ACTION(REPLACE)"
      ]
    },
    {
      "scenario": "MCAUSER lacks queue manager / queue permissions",
      "commands": [
        "SET AUTHREC PRINCIPAL('mcauser') OBJTYPE(QMGR) AUTHADD(CONNECT, INQ)",
        "SET AUTHREC PROFILE('PAYMENTS.IN') OBJTYPE(QUEUE) PRINCIPAL('mcauser') AUTHADD(PUT, INQ, BROWSE)"
      ]
    },
    {
      "scenario": "CONNAUTH credentials rejected",
      "commands": [
        "ALTER AUTHINFO('SYSTEM.DEFAULT.AUTHINFO.IDPWOS') AUTHTYPE(IDPWOS) ADOPTCTX(YES) CHCKCLNT(REQDADM)",
        "REFRESH SECURITY TYPE(CONNAUTH)"
      ]
    }
  ],
  "execution_policy": "Server never executes remediation_steps. These are IBM-recommended fix commands returned as TEXT only for the operator to review and run manually in a change window.",
  "doc_refs": [
    {
      "title": "2035 (07F3) MQRC_NOT_AUTHORIZED",
      "url": "https://www.ibm.com/docs/en/ibm-mq/9.4?topic=codes-2035-07f3-rc2035-mqrc-not-authorized"
    }
  ]
}
```

`fix_steps` are the read-only commands the server already ran (or will run) to confirm the diagnosis. Every string in this array passes through the same allowlist as everything else — the server enforces its own contract here.

`remediation_steps` are the IBM-recommended commands to actually resolve the issue. These are returned as **text only**. The server cannot execute them. They're scenario-grouped (one block per root cause hypothesis) so the operator picks the recipe that matches what they confirmed via `fix_steps`.

#### 3. Make the citation a structural part of the response

Every recommendation has a `doc_refs` array linking to IBM Knowledge Center. The server enforces an allowlist on URLs:

```python
_ALLOWED_DOC_HOSTS = ("www.ibm.com",)
```

If any code path tries to return a URL pointing to a non-IBM host, it gets redacted to `[REDACTED:url]` before leaving the server. The AI client literally cannot show your admin a fake StackOverflow link, because the link never leaves the server intact.

This matters because LLMs are great at generating plausible-looking URLs. Enforcing the allowlist in the response sanitizer (not the AI prompt) gives a real guarantee.

#### 4. Make the safety guarantee machine-readable

Every response includes a top-level `execution_policy` field stating: *"Server never executes remediation_steps. These are IBM-recommended fix commands returned as TEXT only for the operator to review and run manually in a change window."*

This is meant to be auditable. The compliance team can grep the audit log and confirm:

- Every tool call was logged with hash-chained tamper detection.
- Every response carried the `execution_policy` field.
- No connector path in the source ever passed a `remediation_steps` command to `execute_mqsc()` — verified by a source-grep test in CI.

That last point is enforced by a test that scans every Python file in the project for the string `.remediation_steps` and asserts it only appears in the model layer (the dataclass definition, the JSON serializer, the matchers that construct findings) — never in the tool-dispatch layer that talks to the QM. A refactor that violates this invariant fails CI.

### What the operator workflow looks like

On-call SRE gets paged for 2035 on PROD_QM. Opens Cursor / Claude Code, types:

> "Why is PROD_QM erroring?"

3 seconds later, the AI client (which talked to the MCP server, which talked to MQ via read-only DISPLAYs) responds:

- **Diagnosis:** Channel APP.SVRCONN returned MQRC 2035 (NOT_AUTHORIZED), root cause likely one of three scenarios.
- **What I checked:** DISPLAY CHLAUTH(...) MATCH(RUNCHECK), DISPLAY CHSTATUS(...), DISPLAY QMGR CONNAUTH.
- **What IBM recommends you run, based on which scenario applies:**
  - Scenario A → SET CHLAUTH(...) TYPE(BLOCKUSER) ...
  - Scenario B → SET AUTHREC ... AUTHADD(CONNECT, INQ); SET AUTHREC ... PROFILE(...) ...
  - Scenario C → ALTER AUTHINFO ... ; REFRESH SECURITY TYPE(CONNAUTH)
- **Full procedure:** [IBM Knowledge Center link]
- **Safety guarantee:** MCP did not execute any of the SET/ALTER/REFRESH commands. Run them yourself in your change window.

The SRE confirms which scenario applies via the diagnostic DISPLAYs (read-only, safe to run from anywhere), drafts a ServiceNow change with the IBM-recommended commands in the description, executes during their next change window. MTTR drops from 90 minutes to roughly 10 — and the change ticket is bulletproof because every recommendation is sourced from IBM.

### Coverage today

Eight tools across all 10 IBM MQ flavors: Standalone, Multi-Instance, RDQM, Native HA + CRR, Uniform Cluster, Traditional Cluster, z/OS QSG, MQ Appliance, Containerized. Each tool returns the same issue/remediation contract.

KC docs are curated by hand from MQ 9.2, 9.3, 9.4. Reason codes covered include 2035, 2009, 2030, 2051, 2053, 2079, 2080, plus AMQ codes 9202, 9208, 9456, 9484, 9503, 9508, 9764, 3209. Plus topic pages for CRR, Native HA quorum loss, RDQM split-brain, cluster partial repository, page set management, buffer pool tuning, CF structure recovery.

### Where I'd like community feedback

Three honest questions:

**1. Is the three-layer read-only design overkill, or correctly paranoid?**

The server has its own allowlist. The connector has a regex check. The MQ service account itself only has `+connect +inq +dsp` granted via setmqaut. Even with all three layers, has anyone here seen a way it could be defeated?

**2. The scenario-grouping in `remediation_steps` — is it useful, or does it just shift the cognitive load?**

For 2035 I give three scenarios (BLOCKUSER, MCAUSER perms, CONNAUTH) because in practice it's hard to know which one applies without confirming via the diagnostic DISPLAYs. But maybe the right model is "run all three" or "pick the one whose evidence matches." Curious what you'd want as an on-call.

**3. The KC URL registry is hand-curated. If you spot a wrong URL or a missing reason code, please open a GitHub issue.**

The repo is public: github.com/pramodreddyboddu/mq-sentinel.

A 90-second demo runs against a bundled fixture sandbox (no live MQ required, no install — clone + `make demo`):

```bash
git clone https://github.com/pramodreddyboddu/mq-sentinel.git
cd mq-sentinel
make demo
```

If anyone wants to point this at a non-prod QM in their estate, I'd love feedback on the onboarding flow too — especially from Champions or anyone running on z/OS where I have the least real-world stress-test coverage.

Thanks for reading. Happy to answer questions in this thread.

— [Your name]

---

## Posting checklist

- [ ] Sign in to community.ibm.com (use your IBM ID or create a free account if you don't have one)
- [ ] Navigate to **IBM MQ → Discussions** (not blog — discussions get better engagement)
- [ ] Click **New Discussion**
- [ ] Paste the title above
- [ ] Paste the body (everything between the two `---` separators)
- [ ] Add tags: `ibm-mq`, `ai`, `mcp`, `chlauth`, `connauth`, `automation`, `tooling`
- [ ] Pick category: probably **General** or **Automation**
- [ ] Preview — make sure code blocks render correctly (community.ibm.com uses standard Markdown)
- [ ] Submit
- [ ] Within 30 minutes: reply to your own post with a follow-up linking to the GitHub repo and the demo command (boosts visibility in the algorithm)

## After posting

**Day 1:** Check every 4 hours and reply to comments within 1 hour during business hours. The IBM Champions community is small and tight — fast responsive replies build credibility.

**Day 2-7:** If anyone with `IBM` in their job title comments or DMs you, that's the door to internal IBM visibility. Take any 1:1 conversation they offer.

**Day 7+:** If the post gets >2K views, save the URL — it becomes social proof for your sales conversations.

## What NOT to do

- Don't pitch a paid product. Open-source/community ethos. The repo is free and that's how it stays in the post.
- Don't tag IBM employees or Champions you don't know. Same as LinkedIn — algorithm penalizes.
- Don't reply with "thanks!" — every reply must add information.
- Don't promote on multiple IBM forums simultaneously. Pick one (this one) and let it breathe.

## Cross-promote (optional, after the post is live for 24h)

- Drop the community.ibm.com URL in a follow-up LinkedIn post: *"I posted this on the IBM TechXchange community today — would love MQ admins to weigh in."*
- DM the URL to the 5 IBM Champions from `marketing/launch-posts.md` with a one-liner: *"Posted on community.ibm.com — would love your read on the design pattern."*
- Tweet the URL with the hashtag #IBMMQ and #IBMCommunity.
