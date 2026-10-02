import asyncio
import os
from pathlib import Path

import pytest

from smriti.server.jobs import BackgroundIndexer, IndexingError


def test_worker_error_surfaces_as_indexing_error(tmp_path: Path) -> None:
    async def exercise() -> None:
        worker = BackgroundIndexer()
        try:
            not_a_directory = tmp_path / 'file.txt'
            not_a_directory.write_text('x')
            with pytest.raises(IndexingError):
                await worker.index_async(not_a_directory)
            (tmp_path / 'ok.py').write_text('def ok():\n    pass\n')
            assert (await worker.index_async(tmp_path)).files == 1
        finally:
            worker.close()

    asyncio.run(exercise())


def test_crashed_worker_pool_is_replaced(tmp_path: Path) -> None:
    (tmp_path / 'ok.py').write_text('def ok():\n    pass\n')

    async def exercise() -> None:
        worker = BackgroundIndexer()
        try:
            with pytest.raises(IndexingError, match='exited'):
                await worker._await(worker._pool.submit(os._exit, 9))  # type: ignore[arg-type]
            assert (await worker.index_async(tmp_path)).files == 1
        finally:
            worker.close()

    asyncio.run(exercise())


def test_cancelling_waiter_cancels_queued_job(tmp_path: Path) -> None:
    async def exercise() -> None:
        worker = BackgroundIndexer()
        try:
            running = asyncio.create_task(worker.index_async(tmp_path))
            queued = asyncio.create_task(worker.index_async(tmp_path))
            await asyncio.sleep(0)
            queued.cancel()
            with pytest.raises(asyncio.CancelledError):
                await queued
            assert (await running).version >= 0
        finally:
            worker.close()

    asyncio.run(exercise())
