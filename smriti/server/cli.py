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


@app.command('serve')
def serve(
    root: Annotated[Path, typer.Option('--root', exists=True, file_okay=False)] = DEFAULT_ROOT,
) -> None:
    """Serve agent tools through the official MCP stdio transport."""
    from smriti.server.mcp import create_server

    create_server(root.resolve()).run(transport='stdio')


@app.command('callers')
def callers(
    name: str,
    root: Annotated[Path, typer.Option('--root', exists=True, file_okay=False)] = DEFAULT_ROOT,
) -> None:
    """Show call edges targeting matching definitions."""
    from smriti.server.service import SmritiService

    typer.echo(
        json.dumps([asdict(edge) for edge in SmritiService(root).calls(name, incoming=True)])
    )


@app.command('callees')
def callees(
    name: str,
    root: Annotated[Path, typer.Option('--root', exists=True, file_okay=False)] = DEFAULT_ROOT,
) -> None:
    """Show call edges originating in matching definitions."""
    from smriti.server.service import SmritiService

    typer.echo(
        json.dumps([asdict(edge) for edge in SmritiService(root).calls(name, incoming=False)])
    )


RootOption = Annotated[Path, typer.Option('--root', exists=True, file_okay=False)]


def _memory(root: Path):  # type: ignore[no-untyped-def]
    from smriti.server.service import MemoryService

    return MemoryService(root)


def _emit(value: object) -> None:
    typer.echo(json.dumps(value, sort_keys=True))


@app.command('remember')
def remember(
    fact: str,
    anchor: Annotated[
        list[str] | None, typer.Option('--anchor', help='SYMBOL_ID=SHA256 content hash')
    ] = None,
    confidence: Annotated[float, typer.Option('--confidence', min=0, max=1)] = 1.0,
    source: Annotated[str | None, typer.Option('--source')] = None,
    session: Annotated[str | None, typer.Option('--session')] = None,
    root: RootOption = DEFAULT_ROOT,
) -> None:
    """Record a project or symbol-anchored fact."""
    anchors = []
    for item in anchor or []:
        symbol_id, separator, content_hash = item.rpartition('=')
        if not separator:
            raise typer.BadParameter('Anchors use SYMBOL_ID=CONTENT_HASH', param_hint='--anchor')
        anchors.append({'symbol_id': symbol_id, 'content_hash': content_hash})
    service = _memory(root)
    try:
        _emit(
            service.remember(
                fact, anchors=anchors, confidence=confidence, source=source, session=session
            )
        )
    finally:
        service.close()


@app.command('recall')
def recall(
    query: Annotated[str, typer.Argument()] = '',
    fresh_only: Annotated[bool, typer.Option('--fresh-only')] = False,
    root: RootOption = DEFAULT_ROOT,
) -> None:
    """Recall current facts ranked against an optional query."""
    service = _memory(root)
    try:
        _emit(service.recall(query, include_stale=not fresh_only))
    finally:
        service.close()


@app.command('forget')
def forget(
    fact_id: Annotated[str | None, typer.Argument()] = None,
    source: Annotated[str | None, typer.Option('--source')] = None,
    session: Annotated[str | None, typer.Option('--session')] = None,
    root: RootOption = DEFAULT_ROOT,
) -> None:
    """Purge a fact, source, or session and every derived fact."""
    service = _memory(root)
    try:
        _emit({'forgotten': service.forget(fact_id=fact_id, source=source, session=session)})
    finally:
        service.close()


memory_app = typer.Typer(help='Inspect and version memory history.', no_args_is_help=True)
app.add_typer(memory_app, name='memory')


@memory_app.command('log')
def memory_log(
    limit: Annotated[int | None, typer.Option('--limit', min=1)] = None,
    root: RootOption = DEFAULT_ROOT,
) -> None:
    """List operations on the active branch, newest first."""
    service = _memory(root)
    try:
        _emit(service.log(limit))
    finally:
        service.close()


@memory_app.command('diff')
def memory_diff(
    left: Annotated[str | None, typer.Argument()] = None,
    right: Annotated[str | None, typer.Argument()] = None,
    root: RootOption = DEFAULT_ROOT,
) -> None:
    """Compare memory state between two operations (default: empty vs head)."""
    service = _memory(root)
    try:
        _emit(service.diff(left, right))
    finally:
        service.close()


@memory_app.command('revert')
def memory_revert(operation_id: str, root: RootOption = DEFAULT_ROOT) -> None:
    """Append an inverse operation for an earlier operation."""
    service = _memory(root)
    try:
        _emit({'operation': service.revert(operation_id)})
    finally:
        service.close()


@memory_app.command('branch')
def memory_branch(
    name: str,
    switch: Annotated[bool, typer.Option('--switch')] = False,
    root: RootOption = DEFAULT_ROOT,
) -> None:
    """Create a memory branch at the current head."""
    service = _memory(root)
    try:
        _emit(service.branch(name, switch))
    finally:
        service.close()


@memory_app.command('switch')
def memory_switch(name: str, root: RootOption = DEFAULT_ROOT) -> None:
    """Switch the active memory branch."""
    service = _memory(root)
    try:
        _emit(service.switch(name))
    finally:
        service.close()


@memory_app.command('merge')
def memory_merge(
    source: str,
    resolve: Annotated[
        list[str] | None, typer.Option('--resolve', help='FACT_ID=ours|theirs|base|delete')
    ] = None,
    root: RootOption = DEFAULT_ROOT,
) -> None:
    """Merge a branch; conflicts are reported unless explicitly resolved."""
    resolutions = dict(item.split('=', 1) for item in resolve or [] if '=' in item)
    service = _memory(root)
    try:
        result = service.merge(source, resolutions)
        _emit(result)
        if not result['merged']:
            raise typer.Exit(1)
    finally:
        service.close()
