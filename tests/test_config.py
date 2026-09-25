from pathlib import Path
import pytest
from smriti.config import load_config


def test_environment_overrides_file(tmp_path: Path) -> None:
    (tmp_path / 'smriti.toml').write_text('[smriti]\nbudget = 40\n'.replace('\\n', '\n'), encoding='utf-8')
    assert load_config(tmp_path, {'SMRITI_BUDGET': '80'}).budget == 80


def test_negative_budget_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        load_config(tmp_path, {'SMRITI_BUDGET': '-1'})
