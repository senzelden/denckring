"""Start the explorer."""

from __future__ import annotations

from typing import Annotated

import typer
import uvicorn

cli = typer.Typer(
    add_completion=False, help="Browse the denckring catalogue and try its procedures."
)

#: Not 8000: that is the first port anything reaches for, and this is a tool you
#: run alongside whatever else you are working on.
DEFAULT_PORT = 8412


@cli.command()
def serve(
    port: Annotated[int, typer.Option(help="Port to listen on.")] = DEFAULT_PORT,
    host: Annotated[str, typer.Option(help="Interface to bind.")] = "127.0.0.1",
    reload: Annotated[bool, typer.Option(help="Restart when the source changes.")] = False,
) -> None:
    """Serve the explorer, by default only to this machine."""
    typer.echo(f"denckring explorer → http://{host}:{port}")
    uvicorn.run("explorer.app:app", host=host, port=port, reload=reload)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
