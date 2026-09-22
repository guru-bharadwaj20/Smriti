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

    def test_confidence(self):
        store = MemoryStore(":memory:")
        for confidence in (-1, 2, float("nan")):
            with self.assertRaises(ValueError):
                store.remember("bad", confidence=confidence)
        with self.assertRaises(ValueError):
            store.remember("bad", source="")
        store.close()

    def test_anchors(self):
        from smriti.memory import Anchor
        store = MemoryStore(":memory:")
        fact = store.remember("anchored", anchors=[Anchor("parser.parse", "abc")])
        self.assertEqual(store.recall(), [fact])
        store.close()

    def test_anchor_hashes(self):
        from smriti.memory import Anchor
        store = MemoryStore(":memory:")
        with self.assertRaises(ValueError):
            store.remember("bad", anchors=[Anchor("p")])
        store.close()

    def test_infer_anchors(self):
        store = MemoryStore(":memory:")
        f = store.remember("rule", selected_context=[{"symbol_id": "x", "content_hash": "a"}])
        self.assertEqual(f.anchors[0].symbol_id, "x")
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
