from bench.swebench.ground_truth import parse_changed_files


def test_only_changes_not_hunk_context_become_gold_lines() -> None:
    patch = '''diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,5 +1,5 @@
 def first():
     pass
 def second():
-    return 1
+    return 2
 # tail
'''
    change, = parse_changed_files(patch)
    assert change.old_path == change.new_path == 'app.py'
    assert change.removed_lines == (4,)
    assert change.added_at_base_lines == (5,)


def test_new_files_have_no_base_file() -> None:
    patch = '''diff --git a/new.py b/new.py
--- /dev/null
+++ b/new.py
@@ -0,0 +1 @@
+print('new')
'''
    change, = parse_changed_files(patch)
    assert change.old_path is None and change.new_path == 'new.py'
