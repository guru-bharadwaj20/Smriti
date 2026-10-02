import importlib.util
from pathlib import Path


def test_integration_demo_runs() -> None:
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'demo_integration.py'
    spec = importlib.util.spec_from_file_location('demo_integration', path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run()
    assert result['stale_after_edit'] is True and result['forgotten'] == 1
