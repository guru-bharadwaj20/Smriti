import unittest
import sqlite3
from smriti.memory.operations import canonical


class OperationTests(unittest.TestCase):
    pass

    def test_canonical_json(self):
        self.assertEqual(canonical({"b": 1, "a": "α"}), '{"a":"α","b":1}')
        with self.assertRaises(ValueError):
            canonical({"v": float("nan")})
