from pathlib import Path
import subprocess

from bench.swebench.checkout import checkout_base


def test_checkout_uses_base_not_latest_or_patch(tmp_path: Path) -> None:
    source = tmp_path / 'source'
    source.mkdir()
    subprocess.run(['git', 'init', str(source)], check=True, capture_output=True)
    path = source / 'app.py'
    path.write_text('old = 1\n', encoding='utf-8')
    subprocess.run(['git', '-C', str(source), 'add', 'app.py'], check=True)
    subprocess.run(['git', '-C', str(source), '-c', 'user.name=fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'base'], check=True, capture_output=True)
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    path.write_text('new = 2\n', encoding='utf-8')
    isolated = checkout_base(str(source), commit, tmp_path / 'checkout')
    assert (isolated / 'app.py').read_text(encoding='utf-8') == 'old = 1\n'
    assert path.read_text(encoding='utf-8') == 'new = 2\n'
