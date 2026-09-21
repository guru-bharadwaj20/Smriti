import tempfile
import unittest
from pathlib import Path
from smriti.memory import MemoryStore


class MemoryTests(unittest.TestCase):
    def test_provenance(self):
        store = MemoryStore(":memory:")
        fact = store.remember("rule", user="alice", session="s1", tool="mcp", source="review")
        self.assertEqual(store.recall()[0].source, "review")
        self.assertEqual(fact.user, "alice")
        store.close()

    def test_fact_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.db"
            store = MemoryStore(path)
            fact = store.remember("Parser accepts unicode")
            store.close()
            store = MemoryStore(path)
            self.assertEqual(store.recall("unicode"), [fact])
            with self.assertRaises(ValueError):
                store.remember(" ")
            store.close()


if __name__ == "__main__":
    unittest.main()
