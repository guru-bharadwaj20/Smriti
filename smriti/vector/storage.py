"""Portable read-only memory-mapped dense float64 vector storage."""

import json
import mmap
import struct
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


class VectorStorage:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        meta: dict[str, Any] = json.loads(self.path.with_suffix('.json').read_text())
        self.ids: list[str] = meta['ids']
        self.dimension: int = meta['dimension']
        self.file = self.path.open('rb')
        self.mapping = (
            mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ) if self.ids else None
        )

    def get(self, id: str) -> tuple[float, ...]:
        i = self.ids.index(id)
        if self.mapping is None:
            raise KeyError(id)
        return struct.unpack_from('<' + 'd' * self.dimension, self.mapping, i * self.dimension * 8)

    def close(self) -> None:
        if self.mapping:
            self.mapping.close()
        self.file.close()

    @staticmethod
    def write(path: str | Path, vectors: Mapping[str, Sequence[float]]) -> None:
        path = Path(path)
        ids = sorted(vectors)
        dimension = len(vectors[ids[0]]) if ids else 0
        with path.open('wb') as file:
            for id in ids:
                if len(vectors[id]) != dimension:
                    raise ValueError('dimension mismatch')
                file.write(struct.pack('<' + 'd' * dimension, *vectors[id]))
        path.with_suffix('.json').write_text(json.dumps({'ids': ids, 'dimension': dimension}))
