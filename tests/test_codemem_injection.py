import tempfile
import unittest
from pathlib import Path

from bench.codemem.injection import inject, select_probes
from smriti.memory import MemoryStore
from smriti.models import Symbol


class InjectionTests(unittest.TestCase):
    def test_fixture_uses_only_library_functions_and_real_hashes(self):
        symbols = [
            Symbol('test', 'tests/test_x.py', 'test', 'test', 'function', content_hash='t'),
            Symbol('lib', 'src/requests/api.py', 'get', 'get', 'function', content_hash='abc'),
        ]
        probes = select_probes(reversed(symbols))
        self.assertEqual([p.symbol_id for p in probes], ['lib'])
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / 'memory.sqlite')
            try:
                inject(store, probes, 'actual-sha')
                fact = store.recall()[0]
                self.assertEqual(fact.anchors[0].content_hash, 'abc')
                self.assertEqual(fact.session, 'codemem/actual-sha')
            finally:
                store.close()

    def test_missing_library_symbols_fail(self):
        with self.assertRaises(ValueError):
            select_probes([])
