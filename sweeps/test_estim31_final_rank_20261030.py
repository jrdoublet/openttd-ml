"""Economic criterion and technical-health constraints of the final ranker."""
import unittest

from sweeps.estim31_final_rank_20261030 import rank


class FinalRankingContracts(unittest.TestCase):
    def test_ratio_of_means_is_not_mean_of_individual_ratios(self):
        opex = [100, 20]
        aaa = [100, 1000]
        correct = 100 * sum(opex) / sum(aaa)
        wrong = sum(100 * x / y for x, y in zip(opex, aaa)) / len(opex)
        self.assertAlmostEqual(correct, 10.909090909090908)
        self.assertNotEqual(correct, wrong)

    def test_anchor_exists_with_source_and_complete_paired_games(self):
        from sweeps.estim31_joint_next_prepare import REPO
        report = rank(REPO)
        anchor = next(r for r in report['ranked'] if r['suite'] == 'v161')
        self.assertEqual(anchor['health'], '80/80 complete')
        self.assertEqual(len(anchor['pairs']), 40)
        self.assertEqual(len(anchor['source_bundle_sha256']), 64)
        self.assertAlmostEqual(anchor['ratio_pct'], 103.79866719805844)


if __name__ == '__main__':
    unittest.main()
