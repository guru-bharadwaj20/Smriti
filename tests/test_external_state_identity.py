from smriti.config import Config
from smriti.identity import repository_id
from smriti.server.service import SmritiService


def test_external_state_preserves_identity_without_contaminating_source(tmp_path):
    root = tmp_path / 'source'
    root.mkdir()
    state = tmp_path / 'state'
    service = SmritiService(root, Config(root, state))
    assert not (root / '.smriti').exists()
    assert service.repository == repository_id(root, state)
    assert service.repository == SmritiService(root, Config(root, state)).repository
    assert (state / 'repository-id').exists()


def test_default_repository_identity_remains_compatible(tmp_path):
    first = repository_id(tmp_path)
    assert first == repository_id(tmp_path)
    assert (tmp_path / '.smriti/repository-id').read_text() == first
