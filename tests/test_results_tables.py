import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_results_doc_matches_committed_result_files() -> None:
    spec = importlib.util.spec_from_file_location(
        'results_tables', ROOT / 'scripts/results_tables.py'
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    committed = (ROOT / 'docs/results.md').read_text(encoding='utf-8').replace('\r\n', '\n')
    assert committed == module.generate(), 'docs/results.md is stale: run scripts/results_tables.py'
