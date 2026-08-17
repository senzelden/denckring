"""Start the explorer."""

from __future__ import annotations

import os
from typing import Annotated

import typer
import uvicorn

from explorer import env

env.load()

cli = typer.Typer(
    add_completion=False, help="Browse the denckring catalogue and try its procedures."
)

#: Not 8000: that is the first port anything reaches for, and this is a tool you
#: run alongside whatever else you are working on.
DEFAULT_PORT = 8412


@cli.command()
def serve(
    port: Annotated[int, typer.Option(help="Port to listen on.")] = 0,
    host: Annotated[str, typer.Option(help="Interface to bind.")] = "",
    reload: Annotated[bool, typer.Option(help="Restart when the source changes.")] = False,
) -> None:
    """Serve the explorer, by default only to this machine.

    The flags win over `.env`, which wins over the built-in defaults.
    """
    port = port or int(os.environ.get("EXPLORER_PORT", DEFAULT_PORT))
    host = host or os.environ.get("EXPLORER_HOST", "127.0.0.1")
    typer.echo(f"denckring explorer → http://{host}:{port}")
    uvicorn.run("explorer.app:app", host=host, port=port, reload=reload)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
