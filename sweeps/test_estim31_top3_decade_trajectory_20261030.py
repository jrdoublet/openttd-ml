import unittest

from sweeps.estim31_top3_decade_trajectory_20261030 import summarize_year


def observation(profit, cash):
    return {'profit_year': profit, 'money': cash, 'current_loan': 0,
            'air_primary_vehicles': 10, 'primary_vehicles_by_mode': {'rail': 2},
            'air_airports': 5, 'airport_towns_opex_present': 4,
            'air_engine_counts': {'223': 4, '228': 1, '220': 0}}


class AnnualTrendTest(unittest.TestCase):
    def test_ratio_of_means_not_mean_of_ratios(self):
        result = summarize_year([observation(10, 100), observation(90, 300)],
                                [observation(5, 50), observation(180, 200)])
        self.assertAlmostEqual(result['ratio_of_means_pct'], 100 * 50 / 92.5)
        self.assertEqual(result['samples'], 2)
        self.assertEqual(result['opex']['cash'], 200)
        self.assertEqual(result['aaa']['train_stock'], 2)
        self.assertEqual(result['opex']['air_engine_stock_223'], 4)
        self.assertEqual(result['opex']['air_engine_stock_228'], 1)

    def test_reject_incomplete_and_negative_aaa(self):
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            summarize_year([observation(1, 0)], [])
        with self.assertRaisesRegex(ValueError, 'nonpositive'):
            summarize_year([observation(1, 0)], [observation(0, 0)])


if __name__ == '__main__':
    unittest.main()
