"""Local inspection views backed by the repository service."""

import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from smriti.memory import MemoryStore
from smriti.server.schemas import ContextRequest
from smriti.server.service import SmritiService
from smriti.server.status import index_status

ASSETS = Path(__file__).parent / 'static'


@contextmanager
def memory_store(root: Path, data_dir: Path) -> Iterator[MemoryStore]:
    store = MemoryStore(data_dir / 'memory.sqlite')
    try:
        inside_git = subprocess.run(
            ['git', '-C', str(root), 'rev-parse', '--is-inside-work-tree'],
            text=True,
            capture_output=True,
            check=False,
        )
        if inside_git.returncode == 0:
            store.sync_git(root)
        yield store
    finally:
        store.close()


def create_app(root: Path) -> FastAPI:
    root = root.resolve()
    service = SmritiService(root)
    app = FastAPI(title='Smriti', docs_url=None, redoc_url=None)
    app.mount('/static', StaticFiles(directory=ASSETS), name='static')

    @app.get('/', response_class=FileResponse)
    def home() -> FileResponse:
        return FileResponse(ASSETS / 'index.html')

    @app.get('/api/status')
    def status() -> dict[str, object]:
        return {**asdict(index_status(root)), 'repository': root.name, 'root': str(root)}

    @app.get('/api/symbols')
    def symbols(
        q: str = Query(default='', max_length=10000), limit: int = Query(default=100, ge=1, le=1000)
    ) -> list[dict[str, Any]]:
        return [asdict(symbol) for symbol in service.find_symbol(q)[:limit]]

    @app.get('/api/graph/{symbol_id}')
    def graph(symbol_id: str) -> dict[str, Any]:
        snapshot = service.snapshot()
        by_id = {symbol.id: symbol for symbol in snapshot.symbols}
        if symbol_id not in by_id:
            raise HTTPException(404, 'Symbol not found in the current index')
        edges = [edge for edge in snapshot.edges if symbol_id in (edge.source, edge.target)]
        neighbors = {key for edge in edges for key in (edge.source, edge.target)} - {symbol_id}
        return {
            'symbol': asdict(by_id[symbol_id]),
            'edges': [
                asdict(edge)
                for edge in sorted(edges, key=lambda edge: (edge.kind, edge.source, edge.target))
            ],
            'neighbors': [asdict(by_id[key]) for key in sorted(neighbors) if key in by_id],
            'index_version': snapshot.version,
        }

    @app.post('/api/context')
    def context(request: ContextRequest) -> dict[str, Any]:
        return asdict(service.context(request.task, request.budget))

    @app.get('/api/memory')
    def memory(q: str = Query(default='', max_length=10000)) -> dict[str, Any]:
        with memory_store(root, service.config.data_dir) as store:
            return {
                'branch': store.current_branch,
                'head': store.head,
                'facts': [fact.to_dict() for fact in store.recall(q)],
            }

    @app.get('/api/history')
    def history(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
        with memory_store(root, service.config.data_dir) as store:
            return {
                'branch': store.current_branch,
                'head': store.head,
                'operations': store.log(limit=limit),
            }

    @app.get('/api/diff')
    def memory_diff(left: str | None = None, right: str | None = None) -> dict[str, Any]:
        with memory_store(root, service.config.data_dir) as store:
            try:
                return store.diff(left or None, right or None)
            except (KeyError, ValueError) as error:
                raise HTTPException(404, 'Memory history ID not found') from error

    return app
