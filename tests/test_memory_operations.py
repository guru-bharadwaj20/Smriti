import unittest
import sqlite3
from smriti.memory.operations import canonical


class OperationTests(unittest.TestCase):
    pass

    def test_canonical_json(self):
        self.assertEqual(canonical({"b": 1, "a": "α"}), '{"a":"α","b":1}')
        with self.assertRaises(ValueError):
            canonical({"v": float("nan")})

    def test_content_address(self):
        from smriti.memory.operations import Operation, digest
        self.assertEqual(digest({"a": 1, "b": 2}), digest({"b": 2, "a": 1}))
        a = Operation("add", "x", digest({"text": "hello"}), (), "2025-01-01T00:00:00+00:00", {})
        b = Operation("add", "x", digest({"text": "changed"}), (), a.recorded_at, {})
        self.assertNotEqual(a.id, b.id)
        self.assertNotIn("hello", canonical(a.to_dict()))
