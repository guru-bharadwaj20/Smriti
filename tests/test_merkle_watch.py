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
