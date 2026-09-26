"""Explicit local ONNX CPU encoder with attention-mask mean pooling."""

import hashlib
import importlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from .math import normalize


def encoder_identity(model_path: str | Path, tokenizer_path: str | Path) -> str:
    """Cache identity includes weights, tokenizer and preprocessing semantics."""
    digests = []
    for path in (model_path, tokenizer_path):
        with Path(path).open('rb') as stream:
            digests.append(hashlib.file_digest(stream, 'sha256').hexdigest())
    return hashlib.sha256(('\0'.join(digests) + '\0mean-mask-l2-max256-v1').encode()).hexdigest()


class ONNXEmbedder:
    def __init__(
        self,
        model_path: str | Path,
        tokenizer_path: str | Path,
        threads: int = 1,
        version: str | None = None,
    ) -> None:
        ort = importlib.import_module('onnxruntime')
        from tokenizers import Tokenizer

        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        self.session: Any = ort.InferenceSession(
            str(model_path), sess_options=options, providers=['CPUExecutionProvider']
        )
        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.enable_truncation(max_length=256)
        self.tokenizer.enable_padding()
        self.version = version or encoder_identity(model_path, tokenizer_path)

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        import numpy as np

        if not texts:
            return []
        encoded = self.tokenizer.encode_batch(list(texts))
        values = {
            'input_ids': np.asarray([x.ids for x in encoded], dtype=np.int64),
            'attention_mask': np.asarray([x.attention_mask for x in encoded], dtype=np.int64),
            'token_type_ids': np.asarray([x.type_ids for x in encoded], dtype=np.int64),
        }
        inputs = {node.name: values[node.name] for node in self.session.get_inputs()}
        tokens = self.session.run(None, inputs)[0]
        mask = values['attention_mask'][..., None]
        pooled = (tokens * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)
        return [normalize(vector) for vector in pooled]

    def __call__(self, text: str) -> tuple[float, ...]:
        return self.embed([text])[0]


class Encoder(Protocol):
    @property
    def version(self) -> str: ...

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]: ...


class BatchedEmbedder:
    def __init__(self, encoder: Encoder, batch_size: int = 32) -> None:
        if batch_size < 1:
            raise ValueError('positive batch size required')
        self.encoder = encoder
        self.batch_size = batch_size
        self.version = encoder.version

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        texts = list(texts)
        result = []
        for start in range(0, len(texts), self.batch_size):
            result.extend(self.encoder.embed(texts[start : start + self.batch_size]))
        return result


class EmbeddingCache:
    def __init__(self, path: str | Path, encoder: Encoder) -> None:
        import sqlite3
        import threading

        self.connection = sqlite3.connect(str(path), check_same_thread=False)
        self.encoder = encoder
        self.lock = threading.RLock()
        self.connection.execute(
            'CREATE TABLE IF NOT EXISTS embeddings (key TEXT PRIMARY KEY, vector TEXT NOT NULL)'
        )

    @property
    def version(self) -> str:
        return self.encoder.version

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        import hashlib
        import json

        with self.lock:
            keys = [
                hashlib.sha256((self.encoder.version + '\0' + text).encode()).hexdigest()
                for text in texts
            ]
            found: dict[str, tuple[float, ...]] = {}
            missing: dict[str, str] = {}
            for key, text in zip(keys, texts, strict=True):
                if key in found or key in missing:
                    continue
                row = self.connection.execute(
                    'SELECT vector FROM embeddings WHERE key=?', (key,)
                ).fetchone()
                if row:
                    found[key] = tuple(float(x) for x in json.loads(row[0]))
                else:
                    missing[key] = text
            if missing:
                vectors = self.encoder.embed(list(missing.values()))
                if len(vectors) != len(missing):
                    raise ValueError('encoder returned incorrect batch size')
                with self.connection:
                    for key, vector in zip(missing, vectors, strict=True):
                        found[key] = vector
                        self.connection.execute(
                            'INSERT OR REPLACE INTO embeddings VALUES (?,?)',
                            (key, json.dumps(vector)),
                        )
            return [found[key] for key in keys]

    def close(self) -> None:
        with self.lock:
            self.connection.close()
