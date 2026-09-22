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
