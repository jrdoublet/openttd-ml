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
        from unittest.mock import patch
        from sweeps.estim31_joint_next_prepare import REPO
        target = REPO / 'results/estim31_engine_dispatch_air15_root_20261029/results/estim31_engine_dispatch_air15_40x5_20261029.jsonl'
        if target.exists():
            report = rank(REPO)
        else:
            # Fixture minimale autonome : isole l'ancre V161 qualifiée sans exiger
            # les artefacts volumineux non suivis de la campagne complète 40x5.
            with patch('sweeps.estim31_final_rank_20261030.analyze_40x5',
                       return_value={'complete': [], 'pending': []}):
                report = rank(REPO)
        anchor = next(r for r in report['ranked'] if r['suite'] == 'v161')
        self.assertEqual(anchor['health'], '80/80 complete')
        self.assertEqual(len(anchor['pairs']), 40)
        self.assertEqual(len(anchor['source_bundle_sha256']), 64)
        self.assertAlmostEqual(anchor['ratio_pct'], 103.79866719805844)


if __name__ == '__main__':
    unittest.main()
