# Homebrew formula for MQ-Sentinel.
#
# Lives in a separate "tap" repository: github.com/pramodreddyboddu/homebrew-tap
# (creating that tap is a one-time `gh repo create homebrew-tap --public` — see
# packaging/homebrew/README.md). After that, users install with:
#
#   brew tap pramodreddyboddu/tap
#   brew install mq-sentinel
#
# Or one-line:
#
#   brew install pramodreddyboddu/tap/mq-sentinel
#
# This formula installs the wrapper CLI and the bundled venv. It does NOT
# pull pymqi (which needs IBM MQ client libs at install time) — see
# docs/byom.md to wire those in afterwards.

class MqSentinel < Formula
  include Language::Python::Virtualenv

  desc "Read-only IBM MQ diagnostic MCP server"
  homepage "https://github.com/pramodreddyboddu/mq-sentinel"
  url "https://github.com/pramodreddyboddu/mq-sentinel/archive/refs/tags/v0.1.0.tar.gz"
  # Replace with the real sha256 of the tagged tarball:
  sha256 "REPLACE_WITH_TAG_TARBALL_SHA256"
  license :cannot_represent  # Proprietary; will switch to BSL-1.1
  head "https://github.com/pramodreddyboddu/mq-sentinel.git", branch: "main"

  depends_on "python@3.12"

  def install
    venv = virtualenv_create(libexec, "python3.12")
    venv.pip_install_and_link buildpath
  end

  def caveats
    <<~EOS
      MQ-Sentinel is installed as a CLI. To run the MCP server in dev mode:

        MQS_AUTH_DISABLE_AUTH_FOR_LOCAL_DEV=true mq-sentinel serve --transport http

      For production, set OIDC config:

        export MQS_AUTH_OIDC_ISSUER=https://login.example.com/realms/mq-sentinel
        export MQS_AUTH_OIDC_AUDIENCE=mq-sentinel
        export MQS_AUTH_OIDC_JWKS_URL=https://login.example.com/.well-known/jwks.json
        mq-sentinel serve --transport http

      To connect to live IBM MQ, install the IBM MQ Redist Client + pymqi:
        See https://github.com/pramodreddyboddu/mq-sentinel/blob/main/docs/byom.md

      For the Claude Desktop / Cursor / Claude Code wire-up:
        See https://github.com/pramodreddyboddu/mq-sentinel#install
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/mq-sentinel version")
    assert_match "audit chain", shell_output("#{bin}/mq-sentinel verify-audit 2>&1", 0)
  end
end
