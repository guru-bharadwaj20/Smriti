"""Local inspection views backed by the repository service."""

import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from ipaddress import ip_address
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import RequestResponseEndpoint

from smriti.memory import MemoryStore, MergeConflict
from smriti.server.schemas import ContextRequest, MergeRequest
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

    @app.middleware('http')
    async def local_boundary(request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            host = urlsplit('//' + request.headers.get('host', '')).hostname or ''
            trusted = host == 'localhost' or ip_address(host).is_loopback
        except ValueError:
            trusted = False
        if not trusted:
            return Response('Local host required', status_code=400)
        if request.method not in {'GET', 'HEAD', 'OPTIONS'} and request.headers.get('origin'):
            try:
                origin = urlsplit(request.headers['origin'])
                same_origin = (
                    origin.scheme == request.url.scheme
                    and origin.hostname == request.url.hostname
                    and (origin.port or (443 if origin.scheme == 'https' else 80))
                    == (request.url.port or (443 if request.url.scheme == 'https' else 80))
                )
            except ValueError:
                same_origin = False
            if not same_origin:
                return Response('Same origin required', status_code=403)
        response = await call_next(request)
        response.headers.update(
            {
                'Cache-Control': 'no-store',
                'X-Content-Type-Options': 'nosniff',
                'Referrer-Policy': 'no-referrer',
                'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            }
        )
        return response

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

    @app.get('/api/branches')
    def branches() -> dict[str, Any]:
        with memory_store(root, service.config.data_dir) as store:
            return {'current': store.current_branch, 'heads': store.branches()}

    @app.get('/api/merge-preview')
    def merge_preview(source: str = Query(min_length=1, max_length=200)) -> dict[str, Any]:
        with memory_store(root, service.config.data_dir) as store:
            try:
                preview = store.merge_preview(source)
                return {
                    'current': store.current_branch,
                    'source': source,
                    'base': preview['base'],
                    'source_head': preview['source_head'],
                    'conflicts': jsonable_encoder(preview['conflicts']),
                }
            except KeyError as error:
                raise HTTPException(404, 'Memory branch not found') from error

    @app.post('/api/merge')
    def merge(request: MergeRequest) -> dict[str, str]:
        with memory_store(root, service.config.data_dir) as store:
            try:
                operation = store.merge(
                    request.source,
                    resolutions={key: str(value) for key, value in request.resolutions.items()},
                )
                return {'operation_id': operation, 'branch': store.current_branch}
            except MergeConflict as error:
                raise HTTPException(
                    409,
                    {
                        'message': 'Choose a resolution for every conflict',
                        'conflicts': jsonable_encoder(error.conflicts),
                    },
                ) from error
            except KeyError as error:
                raise HTTPException(404, 'Memory branch not found') from error
            except ValueError as error:
                raise HTTPException(400, str(error)) from error

    return app
