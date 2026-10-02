import os
from pathlib import Path

import pytest

from smriti.memory import Anchor, MemoryStore
from smriti.memory.summaries import summarize


class Echo:
    model = 'echo-test'

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return 'Requests retries idempotent calls and times out after 30 seconds.'


def test_summary_is_a_derived_fact_that_forget_cascades_to(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / 'm.sqlite')
    store.remember('requests retries idempotent calls', fact_id='retry', confidence=0.9)
    store.remember('the default timeout is 30 seconds', fact_id='timeout')
    generator = Echo()
    summary = summarize(store, ['retry', 'timeout'], generator)
    assert summary.tool == 'local-summary:echo-test'
    assert sorted(summary.derived_from) == ['retry', 'timeout']
    assert summary.confidence == 0.9
    assert 'requests retries idempotent calls' in generator.prompts[0]
    assert sorted(store.forget('timeout')) == sorted(['timeout', summary.id])
    assert [f.id for f in store.recall()] == ['retry']
    store.close()


def test_refuses_stale_unknown_and_single_sources(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / 'm.sqlite')
    store.remember('a', fact_id='a', anchors=[Anchor('s', 'h')])
    store.remember('b', fact_id='b')
    store.refresh({'s': 'changed'})
    with pytest.raises(ValueError, match='stale'):
        summarize(store, ['a', 'b'], Echo())
    with pytest.raises(KeyError):
        summarize(store, ['b', 'missing'], Echo())
    with pytest.raises(ValueError, match='two'):
        summarize(store, ['b', 'b'], Echo())
    store.close()


MODEL = Path(
    os.environ.get('SMRITI_SUMMARY_MODEL', '.smriti/models/qwen2.5-0.5b-instruct-q4_k_m.gguf')
)


@pytest.mark.skipif(not MODEL.is_file(), reason='local GGUF model not downloaded')
def test_real_local_model_summary(tmp_path: Path) -> None:
    pytest.importorskip('llama_cpp')
    from smriti.memory.summaries import LlamaCppGenerator

    store = MemoryStore(tmp_path / 'm.sqlite')
    store.remember('The parser caches syntax trees per file path.', fact_id='cache')
    store.remember(
        'Edited files reuse their previous tree for incremental parsing.', fact_id='edit'
    )
    summary = summarize(store, ['cache', 'edit'], LlamaCppGenerator(MODEL, max_tokens=80))
    assert summary.text and summary.tool.startswith('local-summary:qwen2.5-0.5b')
    assert store.forget('cache') == sorted(['cache', summary.id]) or summary.id in store.forget(
        'edit'
    )
    store.close()
