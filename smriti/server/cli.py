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


@app.command('find-symbol')
def find_symbol(
    name: str,
    root: Annotated[Path, typer.Option('--root', exists=True, file_okay=False)] = DEFAULT_ROOT,
) -> None:
    """Find indexed source definitions by name, qualified name, or symbol ID."""
    from smriti.server.service import SmritiService

    typer.echo(json.dumps([asdict(symbol) for symbol in SmritiService(root).find_symbol(name)]))


@app.command('context')
def context(
    task: str,
    budget: Annotated[int, typer.Option('--budget', min=0, max=65536)] = 8000,
    root: Annotated[Path, typer.Option('--root', exists=True, file_okay=False)] = DEFAULT_ROOT,
) -> None:
    """Retrieve code context with explanations within a token budget."""
    from smriti.server.service import SmritiService

    typer.echo(SmritiService(root).context(task, budget).text)
