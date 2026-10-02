from pathlib import Path
from tempfile import TemporaryDirectory

from smriti.identity import repository_id, symbol_id


def test_identity_survives_restart() -> None:
    with TemporaryDirectory() as temp:
        root = Path(temp)
        assert repository_id(root) == repository_id(root)
        assert symbol_id('r', 'src\\a.py', 'function', 'f') == symbol_id(
            'r', 'src/a.py', 'function', 'f'
        )
        assert symbol_id('r', 'a.py', 'function', 'f') != symbol_id('r', 'a.py', 'function', 'g')


if __name__ == '__main__':
    test_identity_survives_restart()
