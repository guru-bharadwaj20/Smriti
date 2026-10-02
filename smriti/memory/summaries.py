"""Optional local-model summaries stored as derived, provenance-carrying facts.

A summary never replaces its sources. It is recorded with ``derived_from`` set to
every source fact, so forgetting any source cascades to the summary, and with
``tool='local-summary:<model>'`` so it is always distinguishable from facts a
person or agent stated. Only fresh source facts are summarized: summarizing a
stale claim would launder it into a newly fresh one.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Protocol

from . import Fact, MemoryStore

PROMPT = (
    'Summarize the following project facts in at most {words} words. '
    'Use only information stated in the facts. Do not add advice or new claims.\n\n{facts}\n\nSummary:'
)


class Generator(Protocol):
    model: str

    def __call__(self, prompt: str) -> str: ...


class LlamaCppGenerator:
    """Deterministic CPU generation with a local GGUF model (needs llama-cpp-python)."""

    def __init__(self, model_path: Path, max_tokens: int = 160, threads: int | None = None):
        try:
            from llama_cpp import Llama  # type: ignore[import-not-found, unused-ignore]
        except ImportError as error:  # pragma: no cover - depends on optional extra
            raise RuntimeError('Install llama-cpp-python to use local summaries') from error
        if not model_path.is_file():
            raise FileNotFoundError(model_path)
        with model_path.open('rb') as stream:
            self.model = (
                f'{model_path.name}@{hashlib.file_digest(stream, "sha256").hexdigest()[:12]}'
            )
        self.max_tokens = max_tokens
        self._llm = Llama(
            model_path=str(model_path), n_ctx=4096, seed=0, n_threads=threads, verbose=False
        )

    def __call__(self, prompt: str) -> str:
        result: Any = self._llm.create_chat_completion(
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.0,
            max_tokens=self.max_tokens,
        )
        return str(result['choices'][0]['message']['content']).strip()


def summarize(
    store: MemoryStore,
    fact_ids: Sequence[str],
    generate: Generator | Callable[[str], str],
    *,
    words: int = 60,
    fact_id: str | None = None,
) -> Fact:
    if len(set(fact_ids)) < 2:
        raise ValueError('A summary needs at least two distinct source facts')
    current = {fact.id: fact for fact in store.recall()}
    missing = [identity for identity in fact_ids if identity not in current]
    if missing:
        raise KeyError(f'Unknown or forgotten facts: {missing}')
    sources = [current[identity] for identity in dict.fromkeys(fact_ids)]
    stale = [fact.id for fact in sources if fact.freshness != 'fresh']
    if stale:
        raise ValueError(f'Refusing to summarize stale or orphaned facts: {stale}')
    listing = '\n'.join(f'- {fact.text}' for fact in sources)
    text = generate(PROMPT.format(words=words, facts=listing)).strip()
    if not text:
        raise ValueError('Generator returned an empty summary')
    model = getattr(generate, 'model', 'unknown')
    return store.remember(
        text,
        fact_id=fact_id,
        tool=f'local-summary:{model}',
        source='summary',
        confidence=min(fact.confidence for fact in sources),
        derived_from=[fact.id for fact in sources],
    )
