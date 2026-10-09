# MQ-Sentinel (org) plugin for Claude Code

Connects Claude Code to your organization's **central MQ-Sentinel server**. You need no IBM MQ client and no MQ credentials on your laptop. The server holds the queue manager inventory and credentials, checks your SSO identity on every call, and applies `prod-read` / `nonprod-read` from your SSO groups.

It ships the same `mq-triage` skill and `/mq-health`, `/mq-status` commands as the local `mq-sentinel` plugin.

## Install

Your platform team gives you the server URL. Export it before starting Claude Code:

```bash
export MQS_SENTINEL_URL=https://mq-sentinel.internal.your-org.com/mcp
```

Then in Claude Code:

```
/plugin marketplace add pramodreddyboddu/mq-sentinel
/plugin install mq-sentinel-org@mq-sentinel
```

Restart Claude Code and run `/mcp`. Select `mq-sentinel` and choose **Authenticate**. Claude Code opens your company's SSO login page in the browser, and you're connected once you sign in. Then run `/mq-status` to see which queue managers you can diagnose.

## If SSO sign-in isn't available

Some IdPs need an OAuth client registered for Claude Code before browser sign-in works. Until then, you can connect with a token your IdP issues for MQ-Sentinel's audience, instead of installing this plugin:

```bash
claude mcp add --transport http mq-sentinel "$MQS_SENTINEL_URL" \
  --header "Authorization: Bearer $MQS_TOKEN"
```

## For the platform team

Run MQ-Sentinel centrally with the HTTP transport, OIDC, and a public URL. See [docs/http-transport.md](../../docs/http-transport.md), and the Helm chart in `deploy/helm`. Onboard each queue manager with [docs/onboard-new-qm.md](../../docs/onboard-new-qm.md).
