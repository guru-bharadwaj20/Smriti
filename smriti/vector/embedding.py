"""Explicit local ONNX CPU encoder with attention-mask mean pooling."""

import importlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from .math import normalize


class ONNXEmbedder:
    def __init__(
        self,
        model_path: str | Path,
        tokenizer_path: str | Path,
        threads: int = 1,
        version: str | None = None,
    ) -> None:
        ort = importlib.import_module('onnxruntime')
        import hashlib

        from tokenizers import Tokenizer

        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        self.session: Any = ort.InferenceSession(
            str(model_path), sess_options=options, providers=['CPUExecutionProvider']
        )
        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.enable_truncation(max_length=256)
        self.tokenizer.enable_padding()
        self.version = (
            version or hashlib.file_digest(Path(model_path).open('rb'), 'sha256').hexdigest()
        )

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
    version: str

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

        self.connection = sqlite3.connect(str(path))
        self.encoder = encoder
        self.connection.execute(
            'CREATE TABLE IF NOT EXISTS embeddings (key TEXT PRIMARY KEY, vector TEXT NOT NULL)'
        )

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        import hashlib
        import json

        output = []
        for text in texts:
            key = hashlib.sha256((self.encoder.version + '\0' + text).encode()).hexdigest()
            row = self.connection.execute(
                'SELECT vector FROM embeddings WHERE key=?', (key,)
            ).fetchone()
            if row:
                vector = tuple(json.loads(row[0]))
            else:
                vector = self.encoder.embed([text])[0]
                self.connection.execute(
                    'INSERT OR REPLACE INTO embeddings VALUES (?,?)', (key, json.dumps(vector))
                )
                self.connection.commit()
            output.append(vector)
        return output

    def close(self) -> None:
        self.connection.close()
