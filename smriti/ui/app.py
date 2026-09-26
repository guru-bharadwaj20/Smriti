"""Local inspection views backed by the repository service."""

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from smriti.server.status import index_status

ASSETS = Path(__file__).parent / 'static'


def create_app(root: Path) -> FastAPI:
    root = root.resolve()
    app = FastAPI(title='Smriti', docs_url=None, redoc_url=None)
    app.mount('/static', StaticFiles(directory=ASSETS), name='static')

    @app.get('/', response_class=FileResponse)
    def home() -> FileResponse:
        return FileResponse(ASSETS / 'index.html')

    @app.get('/api/status')
    def status() -> dict[str, object]:
        return {**asdict(index_status(root)), 'repository': root.name, 'root': str(root)}

    return app
