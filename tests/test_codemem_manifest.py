import copy
import json
import unittest
from pathlib import Path

from bench.codemem.manifest import validate_manifest


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(
            Path('bench/codemem/requests-200.json').read_text(encoding='utf-8')
        )

    def test_real_sequence_has_exactly_200_commits(self):
        validate_manifest(self.manifest, 200)
        self.assertEqual(len(self.manifest['commits']), 200)

    def test_missing_commit_is_rejected(self):
        broken = copy.deepcopy(self.manifest)
        broken['commits'].pop()
        with self.assertRaises(ValueError):
            validate_manifest(broken, 200)

    def test_tampered_ancestry_is_rejected(self):
        broken = copy.deepcopy(self.manifest)
        broken['commits'][1]['parents'] = []
        with self.assertRaises(ValueError):
            validate_manifest(broken, 200)
