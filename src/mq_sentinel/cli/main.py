"""MQ-Sentinel CLI — control plane commands (serve, verify-audit, version)."""

from __future__ import annotations

import sys

import orjson
import typer

from mq_sentinel import __version__
from mq_sentinel.audit.logger import verify_chain
from mq_sentinel.config import load_settings
from mq_sentinel.server import MQSentinelServer, serve_stdio

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
def doctor() -> None:
    """Run environment and configuration diagnostics (does not require MQ)."""
    import platform
    import sys as pysys
    from pathlib import Path

    from mq_sentinel.config import load_settings

    print("MQ-Sentinel Doctor")
    print("=" * 40)
    print(f"Version: {__version__}")
    print(f"Python:  {platform.python_version()} ({pysys.executable})")
    print(f"Platform: {platform.platform()}")
    print()

    # Check optional pymqi
    try:
        import pymqi  # type: ignore

        print(f"✓ pymqi available (version {getattr(pymqi, '__version__', 'unknown')})")
        print("  Real MQ connections should work if client libraries are installed.")
    except ImportError:
        print("✗ pymqi NOT installed")
        print("  Real MQ connections will not work.")
        print("  For development/demo use the built-in fixtures (make demo).")
        print("  To use against real QMs: see docs/byom.md")

    print()

    # Config & security basics
    try:
        settings = load_settings()
        print("✓ Configuration loaded successfully")
        print(f"  Environment: {settings.server.environment}")
        print(f"  Transport default: {settings.server.transport}")
        print(f"  Auth disabled for local dev: {settings.auth.disable_auth_for_local_dev}")
        print(f"  Audit log: {settings.audit.log_path}")
        print(f"  Read-only enforcement: {settings.security.enforce_readonly}")
    except Exception as exc:
        print(f"✗ Failed to load configuration: {exc}")
        pysys.exit(2)

    print()

    # Audit path check
    try:
        audit_path = Path(settings.audit.log_path)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        # Try a non-destructive touch
        if audit_path.exists():
            print("✓ Audit log path is writable (file exists)")
        else:
            audit_path.touch()
            audit_path.unlink(missing_ok=True)
            print("✓ Audit log path is writable")
    except Exception as exc:
        print(f"✗ Audit log path problem: {exc}")

    print()
    print("Doctor complete. Most issues are fixed by:")
    print("  - uv sync --all-extras --dev")
    print("  - Setting the right MQS_* environment variables")
    print("  - Running inside the official container image")


@app.command()
def serve(
    transport: str = typer.Option(
        None,
        "--transport",
        "-t",
        help="Transport: stdio | http. Defaults to settings.server.transport.",
    ),
    host: str = typer.Option(
        None,
        "--host",
        help="HTTP bind host (HTTP transport only). Default 127.0.0.1.",
    ),
    port: int = typer.Option(
        None,
        "--port",
        "-p",
        help="HTTP bind port (HTTP transport only). Default 8080.",
    ),
) -> None:
    """Start the MCP server. Defaults to stdio; pass `--transport http` for HTTP."""
    settings = load_settings()
    chosen = (transport or settings.server.transport).lower()
    if chosen == "stdio":
        typer.echo(
            f"mq-sentinel {__version__} starting on stdio (env={settings.server.environment})",
            err=True,
        )
        serve_stdio()
    elif chosen == "http":
        from mq_sentinel.http_app import serve_http

        bind_host = host or settings.server.http_host
        bind_port = port if port is not None else settings.server.http_port
        typer.echo(
            f"mq-sentinel {__version__} starting on http://{bind_host}:{bind_port} "
            f"(env={settings.server.environment})",
            err=True,
        )
        serve_http(host=bind_host, port=bind_port)
    else:
        typer.echo(f"unknown transport: {chosen!r} (expected 'stdio' or 'http')", err=True)
        raise typer.Exit(code=2)


if __name__ == "__main__":  # pragma: no cover
    app()
