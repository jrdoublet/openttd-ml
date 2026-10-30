"""The economic objective is ratio of arithmetic means, never mean ratios."""
import unittest

from sweeps.estim31_joint_safe_40x5_analyse_20261030 import END, ratio


class RankingFormulaContract(unittest.TestCase):
    def test_ratio_of_means_uses_two_separate_company_sums(self):
        seeds = (42,100)
        rows = {
            (42,'OpexAI',END): {'profit_year':100},
            (42,'AAAHogEx',END): {'profit_year':100},
            (100,'OpexAI',END): {'profit_year':200},
            (100,'AAAHogEx',END): {'profit_year':400},
        }
        self.assertEqual(ratio(rows,seeds), 60.0)
        self.assertNotEqual(ratio(rows,seeds), (100.0+50.0)/2)

    def test_invalid_competitor_denominator_rejected(self):
        seeds = (42,)
        rows = {(42,'OpexAI',END): {'profit_year':100},
                (42,'AAAHogEx',END): {'profit_year':0}}
        with self.assertRaisesRegex(ValueError,'non-positive'):
            ratio(rows,seeds)


if __name__=='__main__':
    unittest.main()
