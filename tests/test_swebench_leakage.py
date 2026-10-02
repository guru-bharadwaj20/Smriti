from pathlib import Path

import pytest

from bench.swebench.leakage import added_lines, assert_no_leakage
from smriti.parse import SourceParser

PATCH = """diff --git a/pkg/core.py b/pkg/core.py
--- a/pkg/core.py
+++ b/pkg/core.py
@@ -1,2 +1,2 @@
 def total(values):
-    return sum(values)
+    return sum(value for value in values if value is not None)
"""


def _index(root: Path, source: str):
    (root / 'pkg').mkdir()
    (root / 'pkg/core.py').write_text(source)
    return SourceParser().parse('pkg/core.py', source).symbols


def test_clean_base_index_passes(tmp_path: Path) -> None:
    symbols = _index(tmp_path, 'def total(values):\n    return sum(values)\n')
    assert added_lines(PATCH) == {
        'pkg/core.py': {'return sum(value for value in values if value is not None)'}
    }
    assert assert_no_leakage('total crashes on None', PATCH, tmp_path, symbols) == {
        'checked_post_fix_lines': 1
    }


def test_post_fix_index_and_patch_in_query_are_rejected(tmp_path: Path) -> None:
    fixed = 'def total(values):\n    return sum(value for value in values if value is not None)\n'
    symbols = _index(tmp_path, 'def total(values):\n    return sum(values)\n')
    leaked = SourceParser().parse('pkg/core.py', fixed).symbols
    with pytest.raises(ValueError, match='Post-fix'):
        assert_no_leakage('issue', PATCH, tmp_path, leaked)
    with pytest.raises(ValueError, match='patch text'):
        assert_no_leakage('see ' + PATCH, PATCH, tmp_path, symbols)
