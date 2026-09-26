from fastapi.testclient import TestClient

from smriti.server.service import SmritiService
from smriti.ui.app import create_app


def test_ui_status_reflects_published_index(tmp_path):
    (tmp_path / 'worker.py').write_text('def work():\n    return 1\n')
    app = create_app(tmp_path)
    with TestClient(app) as client:
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
    with TestClient(create_app(tmp_path)) as client:
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
