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
