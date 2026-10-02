import unittest

from bench.codemem.labels import identical_renames, label


class OracleTests(unittest.TestCase):
    def test_ambiguous_copies_do_not_claim_rename(self):
        self.assertEqual(identical_renames({'old': 'x'}, {'a': 'x', 'b': 'x'}), {})
        self.assertEqual(identical_renames({'old': 'x'}, {'new': 'x'}), {'old': 'new'})

    def test_distinguishes_change_deletion_and_exact_move(self):
        self.assertEqual(label('a', 'x', {'a': 'y'}, {}).expected, 'stale')
        self.assertEqual(label('a', 'x', {}, {}).expected, 'orphaned')
        self.assertEqual(label('a', 'x', {'b': 'x'}, {'a': 'b'}).expected, 'fresh')
