"""Smriti command line interface."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from smriti import __version__

app = typer.Typer(help='Local code context and versioned memory.', no_args_is_help=True)
DEFAULT_ROOT = Path('.')


@app.callback()
def main() -> None:
    """Access local repository context and memory."""


@app.command()
def version() -> None:
    """Print the installed engine version."""
    typer.echo(__version__)


@app.command('index')
def index_repository(
    root: Annotated[Path, typer.Option('--root', exists=True, file_okay=False)] = DEFAULT_ROOT,
) -> None:
    """Index supported source files and atomically publish a query snapshot."""
    from smriti.server.service import SmritiService

    result = SmritiService(root).index()
    typer.echo(json.dumps(asdict(result)))


@app.command('status')
def status(
    root: Annotated[Path, typer.Option('--root', exists=True, file_okay=False)] = DEFAULT_ROOT,
) -> None:
    """Show persisted index version and source coverage."""
    from smriti.server.status import index_status

    typer.echo(json.dumps(asdict(index_status(root))))
