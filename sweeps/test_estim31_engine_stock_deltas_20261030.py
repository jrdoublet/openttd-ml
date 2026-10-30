import unittest

from sweeps.estim31_engine_stock_deltas_20261030 import MONTHS, summarize


class EngineSteps(unittest.TestCase):
    def test_monthly_changes_are_lower_bounds_not_purchases(self):
        rows = []
        for date in MONTHS:
            counts = {'223': 3} if date <= '1970-03-01' else {'223': 1, '228': 2}
            rows.append({'duel_policy_id': 'v', 'run': ['OpexAI', 42, 0],
                         'source_bundle_sha256': 'source', 'date': date,
                         'air_engine_counts': counts})
        result = summarize(rows, 'v', 'source', seeds=(42,))
        self.assertEqual(result['positive_observed_stock_steps'], {'223': 3, '228': 2})
        self.assertEqual(result['negative_observed_stock_steps'], {'223': 2})
        self.assertEqual(result['final_stock'], {'223': 1, '228': 2})
        self.assertIn('not gross', result['limitations'])
        rows[0]['source_bundle_sha256'] = 'other'
        with self.assertRaisesRegex(ValueError, 'source hash'):
            summarize(rows, 'v', 'source', seeds=(42,))


if __name__ == '__main__':
    unittest.main()
