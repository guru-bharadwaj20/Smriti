import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from smriti.memory import MemoryStore


class AtomicMemoryTests(unittest.TestCase):
    def test_failed_derivation_edge_rolls_back_fact_and_log(self):
        store = MemoryStore(':memory:')
        try:
            source = store.remember('source')
            derived = store.remember('independent')
            head = store.head
            store.db.execute(
                "CREATE TRIGGER reject_edge BEFORE INSERT ON memory_derivations BEGIN SELECT RAISE(ABORT,'edge failure'); END"
            )
            store.db.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                store.add_derivations(derived.id, [source.id])
            self.assertEqual(store.head, head)
            self.assertEqual(next(f for f in store.recall() if f.id == derived.id).derived_from, ())
            self.assertTrue(store.verify())
        finally:
            store.close()

    def test_interrupted_write_rolls_back_operation_and_view(self):
        store = MemoryStore(':memory:')
        original = store._record

        def interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise KeyboardInterrupt('simulated cancellation')

        try:
            with patch.object(store, '_record', side_effect=interrupted):
                with self.assertRaises(KeyboardInterrupt):
                    store.remember('cancelled payload')
            self.assertEqual(store.recall(), [])
            self.assertEqual(store.log(), [])
            self.assertTrue(store.verify())
        finally:
            store.close()

    def test_concurrent_forget_cannot_miss_new_derivation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'memory.db'
            seed = MemoryStore(path)
            source = seed.remember('source')
            seed.close()
            ready = threading.Event()
            validated = threading.Event()
            resume = threading.Event()
            forgetting = threading.Event()
            finished = threading.Event()
            errors = []
            result = {}

            def create_derived():
                store = None
                try:
                    if not ready.wait(10):
                        raise TimeoutError('forget worker not ready')
                    store = MemoryStore(path)
                    validate = store._validate_derivations

                    def pause_after_validation(*args):
                        validate(*args)
                        validated.set()
                        if not resume.wait(10):
                            raise TimeoutError('write worker not resumed')

                    with patch.object(
                        store, '_validate_derivations', side_effect=pause_after_validation
                    ):
                        fact = store.remember('derived', derived_from=[source.id])
                        result['derived'] = fact.id
                except BaseException as error:
                    errors.append(error)
                finally:
                    if store is not None:
                        store.close()

            def forget_source():
                store = None
                try:
                    store = MemoryStore(path)
                    ready.set()
                    if not validated.wait(10):
                        raise TimeoutError('derived source not validated')
                    forgetting.set()
                    result['forgotten'] = store.forget(source.id)
                except BaseException as error:
                    errors.append(error)
                finally:
                    if store is not None:
                        store.close()
                    finished.set()

            writers = [
                threading.Thread(target=create_derived),
                threading.Thread(target=forget_source),
            ]
            for writer in writers:
                writer.start()
            try:
                self.assertTrue(forgetting.wait(10))
                self.assertFalse(finished.wait(0.1))
            finally:
                resume.set()
                for writer in writers:
                    writer.join(10)
            self.assertFalse(any(writer.is_alive() for writer in writers))
            self.assertEqual(errors, [])
            self.assertEqual(set(result['forgotten']), {source.id, result['derived']})
            store = MemoryStore(path)
            try:
                self.assertEqual(store.recall(), [])
                self.assertTrue(store.verify())
            finally:
                store.close()
