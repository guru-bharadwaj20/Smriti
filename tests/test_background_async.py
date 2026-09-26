import asyncio
from pathlib import Path

from smriti.server.jobs import BackgroundIndexer


def test_event_loop_remains_responsive_while_indexing(tmp_path: Path) -> None:
    for index in range(100):
        (tmp_path / f'app_{index}.py').write_text(
            f'class App{index}:\n    pass\n', encoding='utf-8'
        )

    async def exercise() -> None:
        worker = BackgroundIndexer()
        try:
            job = asyncio.create_task(worker.index_async(tmp_path))
            ticks = 0
            async with asyncio.timeout(60):
                while not job.done():
                    ticks += 1
                    await asyncio.sleep(0.001)
                result = await job
            assert ticks > 1
            assert result.files == 100
        finally:
            worker.close()

    asyncio.run(exercise())
