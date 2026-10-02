import unittest

from bench.codemem.metrics import stale_metrics


class MetricsTests(unittest.TestCase):
    def test_metrics_report_undefined_without_invented_success(self):
        self.assertIsNone(stale_metrics([])['recall'])
        rows = [
            {'expected': 'stale', 'observed': 'fresh'},
            {'expected': 'fresh', 'observed': 'stale'},
            {'expected': 'orphaned', 'observed': 'orphaned'},
        ]
        result = stale_metrics(rows)
        self.assertEqual(result['precision'], 0.5)
        self.assertEqual(result['recall'], 0.5)
