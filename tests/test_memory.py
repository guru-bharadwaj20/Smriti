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

    def test_relatedness(self):
        from smriti.memory import Anchor
        store = MemoryStore(":memory:")
        a = store.remember("a", anchors=[Anchor("x", "h")])
        b = store.remember("b", anchors=[Anchor("x", "h")])
        self.assertAlmostEqual(store.relatedness(a, b, [1, 0], [1, 0]), 1)
        self.assertAlmostEqual(store.relatedness(a, b, [1, 0], [0, 1]), .3)
        store.close()

    def test_source_priority(self):
        store = MemoryStore(":memory:")
        a = store.remember("timeout 5", subject="timeout", source="user")
        b = store.remember("timeout 10", subject="timeout", source="code", confidence=.5)
        self.assertEqual(store.preferred(a.id), b)
        self.assertEqual(len(store.recall()), 2)
        store.close()

    def test_conflict_audit(self):
        store = MemoryStore(":memory:")
        a = store.remember("v1", subject="x", source="user")
        b = store.remember("v2", subject="x", source="code")
        store.preferred(a.id)
        self.assertEqual(store.conflict_history(a.id)[0]["winner"], b.id)
        self.assertEqual(len(store.recall()), 2)
        store.close()

    def test_edit_move_delete_lifecycle(self):
        from smriti.memory import Anchor
        store = MemoryStore(":memory:")
        f = store.remember("cache invariant", anchors=[Anchor("old", "v1")])
        store.refresh({"new": "v1"}, renames={"old": "new"}, commit="move")
        self.assertEqual(store.recall()[0].freshness, "fresh")
        store.refresh({"new": "v2"}, commit="edit")
        self.assertEqual(store.recall()[0].freshness, "stale")
        store.revalidate(f.id, {"new": "v2"})
        store.refresh({}, commit="delete")
        self.assertEqual(store.recall()[0].freshness, "orphaned")
        with self.assertRaises(ValueError):
            store.revalidate(f.id, {})
        store.close()

    def test_natural_language_memory_recall(self):
        store=MemoryStore(":memory:")
        store.remember("parser accepts unicode")
        store.remember("database uses SQLite")
        self.assertEqual(store.recall("Does the parser support unicode?")[0].text,"parser accepts unicode")
        store.close()

    def test_newer_fact_wins_source_tie(self):
        store=MemoryStore(":memory:")
        older=store.remember("timeout 5",fact_id="z-older",subject="timeout",source="user")
        newer=store.remember("timeout 10",fact_id="a-newer",subject="timeout",source="user")
        self.assertEqual(store.preferred(older.id),newer)
        self.assertIsNotNone(newer.created_at)
        self.assertLessEqual(older.created_at,newer.created_at)
        store.close()

    def test_user_source_beats_newer_inference(self):
        store=MemoryStore(":memory:")
        user=store.remember("use timeout 5",subject="timeout",source="user",confidence=.2)
        agent=store.remember("use timeout 10",subject="timeout",source="agent")
        self.assertEqual(store.preferred(agent.id),user)
        store.close()

    def test_add_operation_replay(self):
        store = MemoryStore(":memory:")
        f = store.remember("persisted")
        self.assertEqual(store.replay(), {f.id: f})
        self.assertEqual(store.operations.get(store.head).kind, "add")
        store.close()

    def test_persistent_bitemporal_correction(self):
        from datetime import datetime,timezone
        clock = [datetime(2025,3,1,tzinfo=timezone.utc)]
        store = MemoryStore(":memory:",clock=lambda:clock[0])
        f = store.remember("old",valid_from="2025-01-01T00:00:00+00:00")
        clock[0] = datetime(2025,4,1,tzinfo=timezone.utc)
        store.update(f.id,"new",valid_from="2025-02-01T00:00:00+00:00")
        self.assertEqual(store.recall(valid_at="2025-02-15T00:00:00+00:00",as_of="2025-03-15T00:00:00+00:00")[0].text,"old")
        self.assertEqual(store.recall(valid_at="2025-02-15T00:00:00+00:00",as_of="2025-04-15T00:00:00+00:00")[0].text,"new")
        self.assertEqual(store.recall(valid_at="2025-01-15T00:00:00+00:00",as_of="2025-04-15T00:00:00+00:00")[0].text,"old")
        self.assertEqual(store.replay()[f.id].text,"new")
        store.close()

    def test_invalidation_replay(self):
        store = MemoryStore(":memory:")
        f = store.remember("obsolete")
        store.invalidate(f.id)
        self.assertEqual(store.recall(),[])
        self.assertEqual(store.replay(),{})
        store.close()

    def test_forget_payload_purge(self):
        store = MemoryStore(":memory:")
        f = store.remember("PRIVATE SECRET")
        head = store.head
        store.forget(f.id)
        self.assertEqual(store.replay(head),{})
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM memory_blobs").fetchone()[0],0)
        with self.assertRaises(ValueError):
            store.remember("resurrection",fact_id=f.id)
        self.assertEqual(store.forget(f.id),[])
        store.close()

    def test_replay_determinism(self):
        store = MemoryStore(":memory:")
        store.remember("a",fact_id="a")
        store.remember("b",fact_id="b")
        self.assertEqual(store.replay_digest(),store.replay_digest())
        for op in store.operations.ancestry(store.head):
            self.assertEqual(store.operations.get(op.id),op)
        store.close()

    def test_memory_history(self):
        store = MemoryStore(":memory:")
        f=store.remember("old")
        store.update(f.id,"new")
        self.assertEqual([r["kind"] for r in store.log()],["update","add"])
        store.forget(f.id)
        self.assertTrue(all(r["payload"] is None for r in store.log()))
        store.close()

    def test_memory_diff(self):
        store=MemoryStore(":memory:")
        f=store.remember("a")
        base=store.head
        store.update(f.id,"b")
        other=store.remember("new")
        delta=store.diff(base)
        self.assertEqual(delta["changed"][f.id]["after"]["text"],"b")
        self.assertIn(other.id,delta["added"])
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
