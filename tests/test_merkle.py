from hashlib import sha256

from smriti.merkle import hash_content, hash_file


def test_file_hash_is_content_only(tmp_path):
    a = tmp_path / 'a.py'
    b = tmp_path / 'b.py'
    a.write_bytes(b'hello\r\n')
    b.write_bytes(a.read_bytes())
    assert hash_file(a) == hash_file(b) == sha256(a.read_bytes()).hexdigest()
    assert hash_content(b'hello\n') != hash_file(a)
    assert hash_content(b'') == sha256(b'').hexdigest()


def test_directory_child_order():
    from smriti.merkle import ordered_children

    assert ordered_children({'z': '1', 'a': '2'}) == [('a', '2'), ('z', '1')]


def test_directory_hash_composition():
    from smriti.merkle import hash_directory

    a, b = hash_content(b'a'), hash_content(b'b')
    assert hash_directory({'x': a, 'y': b}) == hash_directory({'y': b, 'x': a})
    assert hash_directory({'x': a}) != hash_directory({'y': a})
    assert hash_directory({}) != hash_content(b'')


def test_snapshot_persistence(tmp_path):
    from smriti.merkle import MerkleSnapshot

    snapshot = MerkleSnapshot({'a.py': hash_content(b'a')}, {'': hash_content(b'root')})
    path = tmp_path / 'snapshot.json'
    snapshot.save(path)
    assert MerkleSnapshot.load(path) == snapshot
    assert not path.with_suffix('.json.tmp').exists()


def test_initial_repository_scan(tmp_path):
    from smriti.merkle import RepositoryScanner

    (tmp_path / 'pkg').mkdir()
    (tmp_path / 'pkg' / 'a.py').write_bytes(b'a')
    snapshot = RepositoryScanner().scan(tmp_path)
    assert snapshot.files == {'pkg/a.py': hash_content(b'a')}
    assert set(snapshot.directories) == {'', 'pkg'}
    assert snapshot.root_hash != hash_content(b'a')


def test_ignore_rules(tmp_path):
    from smriti.merkle import RepositoryScanner

    (tmp_path / '.git').mkdir()
    (tmp_path / '.git' / 'secret').write_text('hidden')
    (tmp_path / '.gitignore').write_text('*.log\n!important.log\n')
    (tmp_path / 'skip.log').write_text('skip')
    (tmp_path / 'important.log').write_text('keep')
    snapshot = RepositoryScanner().scan(tmp_path)
    assert 'skip.log' not in snapshot.files
    assert 'important.log' in snapshot.files
    assert '.git/secret' not in snapshot.files


def test_symlinks_are_never_followed(tmp_path):
    import os

    import pytest

    from smriti.merkle import RepositoryScanner

    try:
        os.symlink(tmp_path, tmp_path / 'cycle', target_is_directory=True)
    except OSError as error:
        pytest.skip('Windows symlink privilege unavailable: ' + str(error))
    snapshot = RepositoryScanner().scan(tmp_path)
    assert set(snapshot.files) == {'cycle'}
    assert set(snapshot.directories) == {''}


def test_diff_skips_equal_subtrees(tmp_path):
    from smriti.merkle import RepositoryScanner, changed_paths

    (tmp_path / 'a').mkdir()
    (tmp_path / 'a' / 'f.py').write_text('unchanged')
    (tmp_path / 'b.py').write_text('old')
    scanner = RepositoryScanner()
    old = scanner.scan(tmp_path)
    (tmp_path / 'b.py').write_text('new')
    new = scanner.scan(tmp_path)
    assert changed_paths(old, new) == {'b.py'}
    assert changed_paths(new, new) == set()


def test_created_files():
    from smriti.merkle import MerkleSnapshot, created_files

    changes = created_files(MerkleSnapshot(), MerkleSnapshot({'new.py': hash_content(b'n')}))
    assert [(event.kind, event.path) for event in changes] == [('created', 'new.py')]


def test_modified_files():
    from smriti.merkle import MerkleSnapshot, modified_files

    old = MerkleSnapshot({'a.py': hash_content(b'a'), 'b.py': hash_content(b'b')})
    new = MerkleSnapshot({'a.py': hash_content(b'new'), 'b.py': hash_content(b'b')})
    assert [event.path for event in modified_files(old, new)] == ['a.py']


def test_deleted_files():
    from smriti.merkle import MerkleSnapshot, deleted_files

    changes = deleted_files(MerkleSnapshot({'old.py': hash_content(b'n')}), MerkleSnapshot())
    assert [(event.kind, event.path) for event in changes] == [('deleted', 'old.py')]


def test_moves_are_verified_and_ambiguity_is_retained():
    from smriti.merkle import MerkleSnapshot, diff_snapshots

    digest = hash_content(b'same')
    events = diff_snapshots(MerkleSnapshot({'a.py': digest}), MerkleSnapshot({'b.py': digest}))
    assert [(event.kind, event.path, event.old_path) for event in events] == [
        ('moved', 'b.py', 'a.py')
    ]
    events = diff_snapshots(
        MerkleSnapshot({'a.py': digest}), MerkleSnapshot({'b.py': digest, 'c.py': digest})
    )
    assert all(event.kind != 'moved' for event in events)


def test_symlink_leaf_never_reads_target_directory(tmp_path, monkeypatch):
    """Exercise no traversal even when Windows forbids creating real symlinks."""
    import os
    from pathlib import Path

    from smriti.merkle import RepositoryScanner

    link = tmp_path / 'linked'
    link.mkdir()
    (link / 'outside.py').write_text('must not be indexed')
    original = Path.is_symlink
    monkeypatch.setattr(Path, 'is_symlink', lambda path: path == link or original(path))
    monkeypatch.setattr(os, 'readlink', lambda path: 'external-target')
    snapshot = RepositoryScanner().scan(tmp_path)
    assert snapshot.files == {'linked': hash_content(b'symlink\0external-target')}
    assert set(snapshot.directories) == {''}
