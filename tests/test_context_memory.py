from pathlib import Path

from smriti.server.service import MemoryService, SmritiService


def test_context_includes_fresh_memory_and_drops_stale(tmp_path: Path) -> None:
    source = tmp_path / 'billing.py'
    source.write_text('def refund_invoice(invoice):\n    return invoice.total\n')
    service = SmritiService(tmp_path)
    service.index()
    symbol = service.find_symbol('refund_invoice')[0]
    memory = MemoryService(tmp_path)
    fact = memory.remember(
        'refund invoice rounds totals to cents',
        anchors=[{'symbol_id': symbol.id, 'content_hash': symbol.content_hash}],
    )
    memory.close()
    text = service.context('refund invoice', 2000).text
    assert f'# Memory {fact["id"]}' in text
    assert 'rounds totals to cents' in text
    source.write_text('def refund_invoice(invoice):\n    return -invoice.total\n')
    service.index()
    assert (
        'rounds totals to cents' not in SmritiService(tmp_path).context('refund invoice', 2000).text
    )
