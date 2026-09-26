import sqlite3
import unittest

from smriti.memory.operations import canonical


class OperationTests(unittest.TestCase):
    pass

    def test_canonical_json(self):
        self.assertEqual(canonical({'b': 1, 'a': 'α'}), '{"a":"α","b":1}')
        with self.assertRaises(ValueError):
            canonical({'v': float('nan')})

    def test_content_address(self):
        from smriti.memory.operations import Operation, digest

        self.assertEqual(digest({'a': 1, 'b': 2}), digest({'b': 2, 'a': 1}))
        a = Operation('add', 'x', digest({'text': 'hello'}), (), '2025-01-01T00:00:00+00:00', {})
        b = Operation('add', 'x', digest({'text': 'changed'}), (), a.recorded_at, {})
        self.assertNotEqual(a.id, b.id)
        self.assertNotIn('hello', canonical(a.to_dict()))

    def test_dag_parents(self):
        from smriti.memory.operations import OperationLog

        db = sqlite3.connect(':memory:')
        log = OperationLog(db)
        a = log.append('add', 'x', {'text': 'rule'})
        b = log.append('update', 'x', {'text': 'new'}, parents=[a.id])
        self.assertEqual(log.get(b.id).parents, (a.id,))
        self.assertEqual([o.id for o in log.ancestry(b.id)], [a.id, b.id])
        self.assertEqual(log.payload(a)['text'], 'rule')
        with self.assertRaises(KeyError):
            log.append('bad', parents=['missing'])
        db.close()

    def test_metadata_is_immutable(self):
        from smriti.memory.operations import OperationLog

        db = sqlite3.connect(':memory:')
        log = OperationLog(db)
        metadata = {'nested': {'value': 'original'}}
        operation = log.append('add', 'x', {'id': 'x', 'text': 'fact'}, metadata=metadata)
        original_id = operation.id
        metadata['nested']['value'] = 'changed input'
        observed = operation.metadata
        observed['nested']['value'] = 'changed output'
        self.assertEqual(operation.metadata['nested']['value'], 'original')
        self.assertEqual(operation.id, original_id)
        self.assertEqual(log.get(original_id), operation)
        db.close()

    def test_operation_rejects_naive_timestamp(self):
        from smriti.memory.operations import Operation

        with self.assertRaises(ValueError):
            Operation('add', 'x', None, (), '2025-01-01T00:00:00', {})
