import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from smriti.memory import Anchor, MemoryStore, MergeConflict
from smriti.memory.sync import (
    export_bundle,
    import_bundle,
    verify_bundle,
)

KEY = b'k' * 32
REPO = 'test-repository'


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.alice = MemoryStore(root / 'alice.sqlite')
        self.bob = MemoryStore(root / 'bob.sqlite')

    def tearDown(self):
        self.alice.close()
        self.bob.close()
        self.directory.cleanup()

    def exchange(self, source, destination, branch):
        import_bundle(destination, export_bundle(source, REPO, KEY), REPO, KEY, branch)

    def test_authentication_and_repository_scope(self):
        self.alice.remember('source fact', fact_id='shared')
        bundle = export_bundle(self.alice, REPO, KEY)
        tampered = copy.deepcopy(bundle)
        tampered['document']['head'] = None
        with self.assertRaises(ValueError):
            verify_bundle(tampered, REPO, KEY)
        with self.assertRaises(ValueError):
            verify_bundle(bundle, REPO, b'x' * 32)
        with self.assertRaises(ValueError):
            verify_bundle(bundle, 'another-project', KEY)
        self.assertEqual(self.bob.recall(), [])

    def test_peer_branch_rewind_is_rejected_atomically(self):
        self.alice.remember('first', fact_id='one')
        old = export_bundle(self.alice, REPO, KEY)
        self.alice.remember('second', fact_id='two')
        self.exchange(self.alice, self.bob, 'peer/alice')
        before = self.bob.branches()
        with self.assertRaises(ValueError):
            import_bundle(self.bob, old, REPO, KEY, 'peer/alice')
        self.assertEqual(self.bob.branches(), before)

    def test_import_never_overwrites_active_branch(self):
        self.alice.remember('first', fact_id='one')
        with self.assertRaises(ValueError):
            import_bundle(
                self.bob,
                export_bundle(self.alice, REPO, KEY),
                REPO,
                KEY,
                self.bob.current_branch,
            )
        self.assertEqual(self.bob.recall(), [])
        self.assertEqual(self.bob.log(), [])


if __name__ == '__main__':
    unittest.main()
