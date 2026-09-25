from smriti.watch import ChangeWatcher


def test_native_watcher_delivers_file_event(tmp_path):
    import time
    watcher = ChangeWatcher(tmp_path)
    watcher.start()
    try:
        (tmp_path / "new.py").write_text("value = 1")
        events = []
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not events:
            time.sleep(0.05)
            events = watcher.poll()
        assert any(event.path == "new.py" for event in events)
    finally:
        watcher.stop()
    assert watcher.observer is None


def test_debounce_coalesces_events(tmp_path):
    watcher = ChangeWatcher(tmp_path)
    watcher.feed("modified", "a.py")
    watcher.feed("modified", "a.py")
    assert watcher.poll() == []
    assert len(watcher.poll(force=True)) == 1
    assert watcher.poll(force=True) == []


def test_checkout_burst_requests_single_rescan(tmp_path):
    watcher = ChangeWatcher(tmp_path)
    for name in ["a.py", "b.py", ".git/HEAD", ".git/index"]:
        watcher.feed("modified", name)
    events = watcher.poll(force=True)
    assert [(event.kind, event.path) for event in events] == [("rescan", "")]


def test_affected_jobs_do_not_parse_deletions():
    from smriti.watch import affected_file_jobs
    from smriti.merkle import FileChange
    parse, remove, rescan = affected_file_jobs([FileChange("modified", "a.py"), FileChange("deleted", "b.py"), FileChange("moved", "d.py", "c.py")])
    assert parse == ["a.py", "d.py"]
    assert remove == ["b.py", "c.py"]
    assert not rescan


def test_symbol_delta_detects_edits_and_deletion():
    from smriti.watch import diff_symbols
    from smriti.parse import parse_file
    old = parse_file("a.py", "def a():\n    return 1\ndef b():\n    pass\n").symbols
    new = parse_file("a.py", "def a():\n    return 2\n").symbols
    delta = diff_symbols(old, new)
    assert [s.name for s in delta.removed] == ["b"]
    assert {s.name for s in delta.changed} == {"a", "a"}
    assert not delta.added


def test_verified_rename_preserves_id():
    from smriti.watch import preserve_symbol_ids
    from smriti.parse import parse_file
    old = parse_file("a.py", "def first(value):\n    return value + 1\n").symbols
    new = parse_file("a.py", "def second(value):\n    return value + 1\n").symbols
    renamed, mapping = preserve_symbol_ids(old, new)
    assert renamed[1].id == old[1].id
    assert renamed[1].name == "second"
    assert mapping[new[1].id] == old[1].id
    different = parse_file("a.py", "def third(value):\n    return value + 2\n").symbols
    assert preserve_symbol_ids(old, different)[1] == {}


def test_graph_deletion_prunes_both_directions():
    from smriti.watch import prune_edges
    from smriti.models import Edge
    edges = [Edge("a", "b", "calls"), Edge("b", "c", "calls"), Edge("c", "a", "calls")]
    assert prune_edges(edges, {"b"}) == [edges[2]]


def test_lexical_and_vector_updates_match_symbol_delta():
    from smriti.watch import SymbolDelta, update_search_indexes
    from smriti.models import Symbol
    added = Symbol("new", "a.py", "new", "a.new", "function")
    removed = Symbol("old", "a.py", "old", "a.old", "function")
    unchanged = Symbol("same", "a.py", "same", "a.same", "function")
    calls = []
    update_search_indexes(SymbolDelta([added], [], [removed], [unchanged], []),
        lexical_upsert=lambda s: calls.append(("lex+", s.id)), lexical_delete=lambda i: calls.append(("lex-", i)),
        vector_upsert=lambda s: calls.append(("vec+", s.id)), vector_delete=lambda i: calls.append(("vec-", i)))
    assert calls == [("lex-", "old"), ("vec-", "old"), ("lex+", "new"), ("vec+", "new")]


def test_incremental_and_fresh_symbol_equivalence(tmp_path):
    from smriti.parse import SourceParser
    from smriti.merkle import RepositoryScanner, diff_snapshots
    from smriti.watch import apply_file_symbols, affected_file_jobs
    scanner, parser = RepositoryScanner(), SourceParser()
    (tmp_path / "a.py").write_text("def a():\n    return 1\n")
    (tmp_path / "b.py").write_text("def b():\n    return 2\n")
    old = scanner.scan(tmp_path)
    symbols = [s for path in sorted(old.files) for s in parser.parse(path, (tmp_path / path).read_bytes()).symbols]
    (tmp_path / "a.py").write_text("def a():\n    return 3\n")
    (tmp_path / "b.py").unlink()
    (tmp_path / "c.py").write_text("def c():\n    return 4\n")
    new = scanner.scan(tmp_path)
    parse, deleted, _ = affected_file_jobs(diff_snapshots(old, new))
    updated = apply_file_symbols(symbols, {path: parser.parse(path, (tmp_path / path).read_bytes()).symbols for path in parse}, set(deleted))
    fresh = [s for path in sorted(new.files) for s in SourceParser().parse(path, (tmp_path / path).read_bytes()).symbols]
    assert updated == fresh


def test_refresh_hashes_only_affected_leaf(tmp_path, monkeypatch):
    import smriti.watch as watch
    from smriti.merkle import RepositoryScanner
    (tmp_path / "a.py").write_text("old")
    (tmp_path / "b.py").write_text("same")
    scanner = RepositoryScanner()
    old = scanner.scan(tmp_path)
    (tmp_path / "a.py").write_text("new")
    original = watch.hash_file
    reads = []
    def tracked(path):
        reads.append(path.name)
        return original(path)
    monkeypatch.setattr(watch, "hash_file", tracked)
    refreshed = watch.refresh_snapshot(tmp_path, old, ["a.py"])
    assert reads == ["a.py"]
    assert refreshed == scanner.scan(tmp_path)
