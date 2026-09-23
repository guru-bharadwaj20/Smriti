"""Smriti command line interface."""

import typer

from smriti import __version__

app = typer.Typer(help='Local code context and versioned memory.', no_args_is_help=True)


@app.callback()
def main() -> None:
    """Access local repository context and memory."""


@app.command()
def version() -> None:
    """Print the installed engine version."""
    typer.echo(__version__)
