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

    def test_project_fact(self):
        store = MemoryStore(":memory:")
        self.assertEqual(store.remember("Uses SQLite").scope, "project")
        store.close()

    def test_anchor_relationships(self):
        from smriti.memory import Anchor
        store = MemoryStore(":memory:")
        f = store.remember("rule", anchors=[Anchor("x", "h")])
        self.assertEqual(store.db.execute("SELECT fact_id FROM fact_anchors WHERE symbol_id='x'").fetchone()[0], f.id)
        store.close()

    def test_changed_anchor(self):
        from smriti.memory import Anchor
        store = MemoryStore(":memory:")
        store.remember("rule", anchors=[Anchor("x", "old")])
        self.assertEqual(store.refresh({"x": "new"})[0].freshness, "stale")
        store.close()

    def test_deleted_anchor(self):
        from smriti.memory import Anchor
        store = MemoryStore(":memory:")
        store.remember("rule", anchors=[Anchor("x", "old")])
        self.assertEqual(store.refresh({})[0].freshness, "orphaned")
        store.close()

    def test_verified_rename(self):
        from smriti.memory import Anchor
        store = MemoryStore(":memory:")
        store.remember("rule", anchors=[Anchor("old", "hash")])
        store.refresh({"new": "hash"}, renames={"old": "new"})
        self.assertEqual(store.recall()[0].anchors[0].symbol_id, "new")
        store.close()

    def test_freshness_reason(self):
        from smriti.memory import Anchor
        store = MemoryStore(":memory:")
        store.remember("rule", anchors=[Anchor("x", "old")])
        f = store.refresh({"x": "new"}, commit="deadbeef")[0]
        self.assertEqual((f.freshness_reason, f.triggering_commit), ("anchor_changed", "deadbeef"))
        store.close()

    def test_multiple_anchor_policy(self):
        from smriti.memory import Anchor
        store = MemoryStore(":memory:")
        f = store.remember("rule", anchors=[Anchor("a", "1"), Anchor("b", "2")])
        self.assertEqual(store.anchor_states(f.id, {"a": "1", "b": "3"}), {"a": "fresh", "b": "stale"})
        self.assertEqual(store.refresh({"a": "1"})[0].freshness, "orphaned")
        store.close()

    def test_stale_ranking(self):
        from smriti.memory import Anchor
        store = MemoryStore(":memory:")
        store.remember("rule stale", anchors=[Anchor("x", "old")], fact_id="a")
        store.remember("rule fresh", fact_id="z")
        store.refresh({"x": "new"})
        self.assertEqual(store.recall("rule")[0].id, "z")
        store.close()

    def test_recall_freshness_output(self):
        store = MemoryStore(":memory:")
        f = store.remember("rule")
        self.assertEqual(f.to_dict()["freshness"], "fresh")
        self.assertFalse(f.to_dict()["requires_revalidation"])
        store.close()

    def test_revalidation_audit(self):
        from smriti.memory import Anchor
        store = MemoryStore(":memory:")
        f = store.remember("rule", anchors=[Anchor("x", "old")])
        store.refresh({"x": "new"})
        self.assertEqual(store.revalidate(f.id, {"x": "new"}).freshness, "fresh")
        self.assertEqual(store.audit(f.id)[0]["before"].anchors[0].content_hash, "old")
        self.assertEqual(len(store.audit(f.id)), 2)
        store.close()

    def test_contradiction_subject(self):
        store = MemoryStore(":memory:")
        a = store.remember("timeout 5", subject="timeout")
        b = store.remember("timeout 10", subject="timeout")
        store.remember("unrelated")
        self.assertEqual(store.contradictions(a.id), [b])
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
