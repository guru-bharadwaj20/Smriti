from pathlib import Path

from smriti.pack.tokens import TokenCounter
from smriti.server.service import SmritiService


def test_context_is_budgeted_with_explanations_and_cached_across_restart(tmp_path: Path) -> None:
    (tmp_path / 'app.py').write_text(
        'def normalize_request(value):\n    return value.strip()\n\ndef caller(value):\n    return normalize_request(value)\n',
        encoding='utf-8',
    )
    service = SmritiService(tmp_path)
    service.index()
    result = service.context('normalize request', 200)
    assert result.items
    assert 'Why:' in result.text
    assert result.token_count == TokenCounter().count(result.text) <= 200
    assert service.context('normalize request', 0).text == ''
    assert SmritiService(tmp_path).context('normalize request', 200).text == result.text
