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
