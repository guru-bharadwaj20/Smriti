"""Smriti command line interface."""

import typer
from pathlib import Path
from dataclasses import asdict
import json

from smriti import __version__

app = typer.Typer(help='Local code context and versioned memory.', no_args_is_help=True)


@app.callback()
def main() -> None:
    """Access local repository context and memory."""


@app.command()
def version() -> None:
    """Print the installed engine version."""
    typer.echo(__version__)


@app.command('index')
def index_repository(root: Path = typer.Option(Path('.'), '--root')) -> None:
    """Index supported source files and atomically publish a query snapshot."""
    from smriti.server.service import SmritiService

    result = SmritiService(root).index()
    typer.echo(json.dumps(asdict(result)))
