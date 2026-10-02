"""Background repository indexing in a separate worker process."""

import asyncio
from concurrent.futures import Future, ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

from smriti.server.service import IndexResult


class IndexingError(RuntimeError):
    """Indexing failed in the worker; the last published snapshot remains served."""


def _index_repository(root: str) -> IndexResult:
    from smriti.server.service import SmritiService

    return SmritiService(Path(root)).index()


class BackgroundIndexer:
    def __init__(self) -> None:
        self._pool = ProcessPoolExecutor(max_workers=1)

    def submit(self, root: Path) -> Future[IndexResult]:
        return self._pool.submit(_index_repository, str(root.resolve()))

    async def index_async(self, root: Path) -> IndexResult:
        """Await worker output without blocking the agent server's event loop.

        Cancelling the awaiting task cancels a job that has not started. Worker
        exceptions and crashes surface as ``IndexingError``; a crashed pool is
        replaced so later jobs keep working.
        """
        return await self._await(self.submit(root))

    async def _await(self, future: Future[IndexResult]) -> IndexResult:
        try:
            return await asyncio.wrap_future(future)
        except asyncio.CancelledError:
            future.cancel()
            raise
        except BrokenProcessPool as error:
            self._pool.shutdown(wait=False, cancel_futures=True)
            self._pool = ProcessPoolExecutor(max_workers=1)
            raise IndexingError('Indexing worker exited unexpectedly') from error
        except Exception as error:
            raise IndexingError(f'Indexing failed: {error}') from error

    def close(self) -> None:
        self._pool.shutdown(wait=True, cancel_futures=True)
