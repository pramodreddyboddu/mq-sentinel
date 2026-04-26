"""MQ-Sentinel CLI — control plane commands (serve, verify-audit, version)."""

from __future__ import annotations

import sys

import orjson
import typer

from mq_sentinel import __version__
from mq_sentinel.audit.logger import verify_chain
from mq_sentinel.config import load_settings
from mq_sentinel.server import MQSentinelServer

app = typer.Typer(
    name="mq-sentinel",
    help="MQ-Sentinel — read-only IBM MQ diagnostic MCP server.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def version() -> None:
    """Print the MQ-Sentinel version."""
    typer.echo(__version__)


@app.command(name="verify-audit")
def verify_audit() -> None:
    """Verify the hash-chained audit log."""
    settings = load_settings()
    try:
        verify_chain(settings.audit.log_path)
        typer.echo("audit chain: OK")
    except (ValueError, FileNotFoundError) as exc:
        typer.echo(f"audit chain: FAILED — {exc}", err=True)
        sys.exit(2)


@app.command()
def health() -> None:
    """Run the in-process health check (does not connect to any QM)."""
    server = MQSentinelServer()
    result = server.dispatch(token="dev-token", tool="health", params={})  # noqa: S106
    sys.stdout.write(orjson.dumps(result, option=orjson.OPT_INDENT_2).decode())
    sys.stdout.write("\n")


@app.command()
def serve() -> None:
    """Start the MCP server (Phase 2 will wire the MCP transport here)."""
    settings = load_settings()
    typer.echo(
        f"mq-sentinel {__version__} would start on "
        f"{settings.server.transport}://{settings.server.http_host}:{settings.server.http_port}"
    )
    typer.echo("MCP transport wiring lands in the next commit.")


if __name__ == "__main__":  # pragma: no cover
    app()
