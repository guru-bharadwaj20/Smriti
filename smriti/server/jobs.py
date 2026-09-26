"""Background repository indexing in a separate worker process."""

import asyncio
from concurrent.futures import Future, ProcessPoolExecutor
from pathlib import Path

from smriti.server.service import IndexResult


def _index_repository(root: str) -> IndexResult:
    from smriti.server.service import SmritiService

    return SmritiService(Path(root)).index()


class BackgroundIndexer:
    def __init__(self) -> None:
        self._pool = ProcessPoolExecutor(max_workers=1)

    def submit(self, root: Path) -> Future[IndexResult]:
        return self._pool.submit(_index_repository, str(root.resolve()))

    async def index_async(self, root: Path) -> IndexResult:
        """Await worker output without blocking the agent server's event loop."""
        return await asyncio.wrap_future(self.submit(root))

    def close(self) -> None:
        self._pool.shutdown(wait=True, cancel_futures=True)
