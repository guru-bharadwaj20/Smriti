from fastapi.testclient import TestClient

from smriti.server.service import SmritiService
from smriti.ui.app import create_app


def test_ui_status_reflects_published_index(tmp_path):
    (tmp_path / 'worker.py').write_text('def work():\n    return 1\n')
    app = create_app(tmp_path)
    with TestClient(app, base_url='http://127.0.0.1') as client:
        assert client.get('/api/status').json()['indexed'] is False
        assert client.get('/').status_code == 200
        assert 'Your repository' in client.get('/').text
        assert client.get('/static/app.js').status_code == 200
        result = SmritiService(tmp_path).index()
        status = client.get('/api/status').json()
        assert status['indexed'] is True
        assert status['version'] == result.version
        assert status['files'] == 1
        assert status['symbols'] == 2


def test_ui_symbol_graph_uses_real_call_edges(tmp_path):
    (tmp_path / 'worker.py').write_text(
        'def work():\n    return 1\ndef caller():\n    return work()\n'
    )
    SmritiService(tmp_path).index()
    with TestClient(create_app(tmp_path), base_url='http://127.0.0.1') as client:
        symbols = client.get('/api/symbols', params={'q': 'work'}).json()
        work = next(symbol for symbol in symbols if symbol['name'] == 'work')
        graph = client.get('/api/graph/' + work['id']).json()
        assert graph['symbol']['body'].startswith('def work')
        assert any(
            edge['kind'] == 'calls' and edge['target'] == work['id'] for edge in graph['edges']
        )
        assert any(symbol['name'] == 'caller' for symbol in graph['neighbors'])
        assert client.get('/api/graph/unknown').status_code == 404
        assert client.get('/api/symbols', params={'limit': 0}).status_code == 422


def test_ui_context_explains_real_selections_within_budget(tmp_path):
    (tmp_path / 'worker.py').write_text('def work():\n    "Do useful work."\n    return 1\n')
    SmritiService(tmp_path).index()
    with TestClient(create_app(tmp_path), base_url='http://127.0.0.1') as client:
        response = client.post('/api/context', json={'task': 'work', 'budget': 128})
        assert response.status_code == 200
        context = response.json()
        assert 0 < context['token_count'] <= 128
        assert 'work' in context['text']
        assert context['items']
        assert all(item['reason'] for item in context['items'])
        zero = client.post('/api/context', json={'task': 'work', 'budget': 0}).json()
        assert zero['token_count'] == 0 and zero['text'] == ''
        assert client.post('/api/context', json={'task': ' ', 'budget': 128}).status_code == 422


def test_ui_memory_retains_freshness_warning_after_source_edit(tmp_path):
    from smriti.memory import Anchor, MemoryStore

    source = tmp_path / 'worker.py'
    source.write_text('def work():\n    return 1\n')
    service = SmritiService(tmp_path)
    service.index()
    work = next(symbol for symbol in service.snapshot().symbols if symbol.kind == 'function')
    store = MemoryStore(service.config.data_dir / 'memory.sqlite')
    try:
        fact = store.remember(
            'Work returns one.',
            anchors=(Anchor(work.id, work.content_hash),),
            source='fixture',
            session='session-one',
        )
    finally:
        store.close()
    source.write_text('def work():\n    return 2\n')
    service.index()
    store = MemoryStore(service.config.data_dir / 'memory.sqlite')
    try:
        store.refresh(
            {symbol.id: symbol.content_hash for symbol in service.snapshot().symbols},
            commit='fixture-edit',
        )
    finally:
        store.close()
    with TestClient(create_app(tmp_path), base_url='http://127.0.0.1') as client:
        response = client.get('/api/memory', params={'q': 'Work'}).json()
        remembered = next(item for item in response['facts'] if item['id'] == fact.id)
        assert remembered['freshness'] == 'stale'
        assert remembered['requires_revalidation'] is True
        assert remembered['freshness_reason']
        assert remembered['session'] == 'session-one'


def test_ui_history_diff_contains_actual_before_and_after(tmp_path):
    from smriti.memory import MemoryStore

    service = SmritiService(tmp_path)
    store = MemoryStore(service.config.data_dir / 'memory.sqlite')
    try:
        fact = store.remember('Returns one.', source='fixture')
        before = store.head
        store.update(fact.id, 'Returns two.')
        after = store.head
    finally:
        store.close()
    with TestClient(create_app(tmp_path), base_url='http://127.0.0.1') as client:
        history = client.get('/api/history').json()
        assert history['head'] == after
        assert [item['kind'] for item in history['operations']][:2] == ['update', 'add']
        diff = client.get('/api/diff', params={'left': before, 'right': after}).json()
        assert diff['changed'][fact.id]['before']['text'] == 'Returns one.'
        assert diff['changed'][fact.id]['after']['text'] == 'Returns two.'
        assert client.get('/api/diff', params={'left': 'unknown'}).status_code == 404


def test_ui_merge_requires_and_records_explicit_conflict_resolution(tmp_path):
    from smriti.memory import MemoryStore

    service = SmritiService(tmp_path)
    store = MemoryStore(service.config.data_dir / 'memory.sqlite')
    try:
        fact = store.remember('Base version.')
        store.branch('feature')
        store.switch('feature')
        store.update(fact.id, 'Feature version.')
        store.switch('main')
        store.update(fact.id, 'Main version.')
    finally:
        store.close()
    with TestClient(create_app(tmp_path), base_url='http://127.0.0.1') as client:
        assert set(client.get('/api/branches').json()['heads']) == {'main', 'feature'}
        preview = client.get('/api/merge-preview', params={'source': 'feature'}).json()
        assert preview['conflicts'][fact.id]['ours']['text'] == 'Main version.'
        assert preview['conflicts'][fact.id]['theirs']['text'] == 'Feature version.'
        assert client.post('/api/merge', json={'source': 'feature'}).status_code == 409
        merged = client.post(
            '/api/merge', json={'source': 'feature', 'resolutions': {fact.id: 'theirs'}}
        )
        assert merged.status_code == 200
        assert merged.json()['operation_id']
        facts = client.get('/api/memory').json()['facts']
        assert next(item for item in facts if item['id'] == fact.id)['text'] == 'Feature version.'


def test_ui_rejects_foreign_hosts_and_cross_origin_mutation(tmp_path):
    with TestClient(create_app(tmp_path), base_url='http://127.0.0.1') as client:
        status = client.get('/api/status')
        assert status.status_code == 200
        assert status.headers['cache-control'] == 'no-store'
        assert "script-src 'self'" in status.headers['content-security-policy']
        assert client.get('/api/status', headers={'Host': 'evil.example'}).status_code == 400
        assert (
            client.post(
                '/api/context',
                headers={'Origin': 'https://evil.example'},
                json={'task': 'work', 'budget': 0},
            ).status_code
            == 403
        )
        assert (
            client.post(
                '/api/context',
                headers={'Origin': 'http://127.0.0.1'},
                json={'task': 'work', 'budget': 0},
            ).status_code
            == 200
        )


def test_ui_launcher_refuses_public_binding(tmp_path):
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, '-m', 'smriti.ui', str(tmp_path), '--host', '0.0.0.0'],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert 'loopback host' in result.stderr
