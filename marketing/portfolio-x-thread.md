X / Twitter Thread Draft (ready to post — "ready to use" version):

---

1/ I built MQ-Sentinel, a read-only IBM MQ diagnostic MCP server that AI agents can actually use safely.

No hallucinations. No risk of destructive commands. Verified IBM docs for every finding.

It's ready for you to try today.

Thread →

2/ The pain is real:

MQ teams waste hours on 2035s, DLQ explosions, Native HA issues, and cluster ghosts.

Handing raw MQ access to Claude/Cursor/Grok? Security teams say no.

3/ So I built a proper MCP server:

• 8 tools covering all 10 MQ flavors
• Read-only enforced in 3 layers
• Prompt-injection firewall + sanitizer
• Every answer has live CI-verified IBM Knowledge Center links
• OIDC + RBAC, hash-chained audit, hardened distroless images

4/ Recent improvements make it genuinely nice to use:

`mq-sentinel doctor` — checks your setup
`mq-sentinel tools` — see what it can do
`mq-sentinel info` — quick overview + security highlights

Plus a guide with real prompts that work well.

5/ Try it in under a minute (no MQ required):

```bash
git clone https://github.com/pramodreddyboddu/mq-sentinel.git
cd mq-sentinel
make demo
```

Or just install and run `mq-sentinel doctor`.

6/ Repo + live demo + usage guide:
https://github.com/pramodreddyboddu/mq-sentinel

Built with Grok Build as my main partner while maintaining strict standards (271+ tests).

7/ If you work with IBM MQ and AI tools, or do platform engineering, I'd love to hear what you think.

(Attach a quick demo video or screenshot of the CLI)

#IBMMQ #MCP #AI

---

Post the first one, then reply with the rest as a thread.