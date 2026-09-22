from hashlib import sha256

from smriti.merkle import hash_content, hash_file


def test_file_hash_is_content_only(tmp_path):
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_bytes(b"hello\r\n")
    b.write_bytes(a.read_bytes())
    assert hash_file(a) == hash_file(b) == sha256(a.read_bytes()).hexdigest()
    assert hash_content(b"hello\n") != hash_file(a)
    assert hash_content(b"") == sha256(b"").hexdigest()


def test_directory_child_order():
    from smriti.merkle import ordered_children
    assert ordered_children({"z": "1", "a": "2"}) == [("a", "2"), ("z", "1")]


def test_directory_hash_composition():
    from smriti.merkle import hash_directory
    a, b = hash_content(b"a"), hash_content(b"b")
    assert hash_directory({"x": a, "y": b}) == hash_directory({"y": b, "x": a})
    assert hash_directory({"x": a}) != hash_directory({"y": a})
    assert hash_directory({}) != hash_content(b"")


def test_snapshot_persistence(tmp_path):
    from smriti.merkle import MerkleSnapshot
    snapshot = MerkleSnapshot({"a.py": hash_content(b"a")}, {"": hash_content(b"root")})
    path = tmp_path / "snapshot.json"
    snapshot.save(path)
    assert MerkleSnapshot.load(path) == snapshot
    assert not path.with_suffix(".json.tmp").exists()


def test_initial_repository_scan(tmp_path):
    from smriti.merkle import RepositoryScanner
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_bytes(b"a")
    snapshot = RepositoryScanner().scan(tmp_path)
    assert snapshot.files == {"pkg/a.py": hash_content(b"a")}
    assert set(snapshot.directories) == {"", "pkg"}
    assert snapshot.root_hash != hash_content(b"a")


def test_ignore_rules(tmp_path):
    from smriti.merkle import RepositoryScanner
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "secret").write_text("hidden")
    (tmp_path / ".gitignore").write_text("*.log\n!important.log\n")
    (tmp_path / "skip.log").write_text("skip")
    (tmp_path / "important.log").write_text("keep")
    snapshot = RepositoryScanner().scan(tmp_path)
    assert "skip.log" not in snapshot.files
    assert "important.log" in snapshot.files
    assert ".git/secret" not in snapshot.files
