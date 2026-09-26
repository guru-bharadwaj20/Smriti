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
