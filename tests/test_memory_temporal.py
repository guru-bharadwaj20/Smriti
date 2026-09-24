import unittest
from datetime import datetime, timezone, timedelta
from smriti.memory.temporal import ValidInterval


class TemporalTests(unittest.TestCase):
    pass

    def test_half_open_valid_interval(self):
        a = datetime(2025, 1, 1, tzinfo=timezone.utc)
        b = datetime(2025, 2, 1, tzinfo=timezone.utc)
        span = ValidInterval(a, b)
        self.assertTrue(span.contains(a))
        self.assertFalse(span.contains(b))

    def test_independent_transaction_time(self):
        from smriti.memory.temporal import TransactionInterval, TemporalVersion
        a = datetime(2025, 1, 1, tzinfo=timezone.utc)
        b = datetime(2025, 2, 1, tzinfo=timezone.utc)
        c = datetime(2025, 3, 1, tzinfo=timezone.utc)
        v = TemporalVersion("x", {"text": "known later"}, ValidInterval(a, b), TransactionInterval(b, c))
        self.assertTrue(v.valid.contains(a))
        self.assertFalse(v.transaction.contains(a))

    def test_aware_timestamps(self):
        from smriti.memory.temporal import timestamp
        self.assertEqual(timestamp("2025-01-01T05:30:00+05:30"), datetime(2025, 1, 1, tzinfo=timezone.utc))
        with self.assertRaises(ValueError):
            timestamp(datetime(2025, 1, 1))

    def test_open_ended(self):
        a = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.assertTrue(ValidInterval(a).contains(datetime(2200, 1, 1, tzinfo=timezone.utc)))

    def test_valid_time_query(self):
        from smriti.memory.temporal import Timeline, TemporalVersion, TransactionInterval
        a = datetime(2025, 1, 1, tzinfo=timezone.utc)
        b = datetime(2025, 2, 1, tzinfo=timezone.utc)
        version = TemporalVersion("x", {"text": "old"}, ValidInterval(a, b), TransactionInterval(a))
        timeline = Timeline([version])
        self.assertEqual(timeline.valid_at(a), [version])
        self.assertEqual(timeline.valid_at(b), [])
