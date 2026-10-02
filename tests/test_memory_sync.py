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

    def test_divergent_teammates_require_conflict_resolution(self):
        self.alice.remember(
            'original', fact_id='shared', user='Alice', anchors=[Anchor('function', 'hash')]
        )
        self.exchange(self.alice, self.bob, 'peer/alice')
        self.bob.merge('peer/alice')
        self.alice.update('shared', text='Alice changed implementation')
        self.bob.update('shared', text='Bob changed implementation')
        self.exchange(self.alice, self.bob, 'peer/alice')
        with self.assertRaises(MergeConflict):
            self.bob.merge('peer/alice')
        self.bob.merge('peer/alice', resolutions={'shared': 'theirs'})
        fact = self.bob.recall()[0]
        self.assertEqual(fact.text, 'Alice changed implementation')
        self.assertEqual(fact.user, 'Alice')
        self.assertEqual(fact.anchors, (Anchor('function', 'hash'),))
        self.assertTrue(self.bob.verify())

    def test_old_bundle_cannot_resurrect_purged_source_or_derived_fact(self):
        self.alice.remember('SECRET source', fact_id='source')
        self.alice.remember('SECRET child', fact_id='child', derived_from=['source'])
        old = export_bundle(self.alice, REPO, KEY)
        import_bundle(self.bob, old, REPO, KEY, 'peer/alice')
        self.bob.merge('peer/alice')
        self.bob.forget('source')
        import_bundle(self.bob, old, REPO, KEY, 'peer/alice-old')
        self.bob.switch('peer/alice-old')
        self.assertEqual(self.bob.recall(), [])
        self.assertEqual(self.bob.db.execute('SELECT count(*) FROM memory_blobs').fetchone()[0], 0)
        self.assertTrue(self.bob.verify())

    def test_remote_tombstones_remove_local_derivation(self):
        self.alice.remember('source', fact_id='source')
        self.exchange(self.alice, self.bob, 'peer/alice')
        self.bob.merge('peer/alice')
        self.bob.remember('Bob inference', fact_id='local-child', derived_from=['source'])
        self.alice.forget('source')
        self.exchange(self.alice, self.bob, 'peer/alice')
        self.assertEqual(self.bob.recall(), [])
        self.assertTrue(self.bob.is_purged('local-child'))

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

    def test_merge_base_scales_with_shared_history(self):
        for index in range(40):
            self.alice.remember('Shared history', fact_id='shared-' + str(index))
        base = self.alice.head
        self.alice.branch('teammate')
        self.alice.remember('Alice work', fact_id='alice-work')
        left = self.alice.head
        self.alice.switch('teammate')
        self.alice.remember('Teammate work', fact_id='teammate-work')
        right = self.alice.head
        with patch.object(
            self.alice.operations, 'ancestry', wraps=self.alice.operations.ancestry
        ) as ancestry:
            self.assertEqual(self.alice.common_base(left, right), base)
            self.assertLessEqual(ancestry.call_count, 2)


if __name__ == '__main__':
    unittest.main()
