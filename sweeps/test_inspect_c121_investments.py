import unittest
from sweeps.inspect_c121_investments import investments


class InvestmentTests(unittest.TestCase):
    def test_forecasts_not_realised_and_no_cross_company(self):
        text = '\n'.join([
            '[script:4] [0] [I] C121_BUILD decision_n=2 actual_n=1 target_n=6 actual_profit=100',
            '[script:4] [1] [I] C121_BUILD decision_n=9 actual_n=1 target_n=9',
            '[script:4] [0] [I] C121_BUILD decision_n=1 actual_n=1 target_n=3',
        ])
        r = investments(text)
        self.assertEqual(r['build_events'], 2)
        self.assertEqual(r['decision_n_above_built'], 1)
        self.assertEqual(r['target_n_above_built'], 2)
        self.assertEqual(r['built_one'], 2)
        self.assertIsNone(r['realised_line_profit'])

    def test_missing_and_negative_are_not_zero(self):
        r = investments('[script:4] [0] [I] C121_BUILD decision_n=-1 actual_n=1 target_n=3')
        self.assertEqual(r['missing_counts'], 1)
        self.assertEqual(r['comparable_counts'], 0)
        self.assertEqual(investments('')['build_events'], 0)


if __name__ == '__main__':
    unittest.main()