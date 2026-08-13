LinkedIn Post Draft (ready to post — "ready to use" version):

---

I built MQ-Sentinel — a production-grade, read-only IBM MQ diagnostic MCP server that Claude, Cursor, Grok and other AI agents can safely use.

If you work with IBM MQ, you know the pain: 2035 storms, exploding DLQs, Native HA lag, cluster mysteries. Traditional tools are slow. Giving an LLM direct MQ access is a non-starter for security teams.

MQ-Sentinel solves this properly:

• 8 diagnostic tools covering all 10 IBM MQ flavors
• Strictly read-only (enforced in 3 layers)
• Prompt-injection firewall + output sanitizer
• Every answer includes verified IBM Knowledge Center citations (CI validates the links daily)
• OIDC + RBAC, hash-chained audit, hardened containers

The best part: it's actually pleasant to use.

New commands make it easy to get started:
- `mq-sentinel doctor` — checks your environment
- `mq-sentinel tools` — see everything it can do
- `mq-sentinel info` — quick overview

There's also a full guide with copy-paste prompts that work well with AI agents.

Try it in 60 seconds (no real MQ needed):

```bash
git clone https://github.com/pramodreddyboddu/mq-sentinel.git
cd mq-sentinel
make demo
```

Or just:
```bash
uv run mq-sentinel doctor
```

Repo + demo + usage guide + all docs:
https://github.com/pramodreddyboddu/mq-sentinel

Built with high engineering standards (271+ tests, strict typing, full threat model). I used Grok Build as my main coding partner while keeping full ownership of the architecture and quality.

If you deal with IBM MQ + AI tooling, or platform engineering in regulated environments, I'd love to hear what you think.

(Attach a short screen recording of `make demo` or `mq-sentinel info`)

#IBMMQ #MCP #AI #PlatformEngineering #Security

---