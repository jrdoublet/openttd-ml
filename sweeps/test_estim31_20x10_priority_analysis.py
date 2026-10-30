"""Check sourced figures used to prioritize post-1974 economic work.

Pure offline tests. Never launch a benchmark or access results/ write-once data.
"""

import json
import unittest
from pathlib import Path


DOC = Path(__file__).resolve().parents[1] / 'docs'


def data(name):
    return json.loads((DOC / name).read_text(encoding='utf-8'))


class DecadeEconomicPriorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ranked = data('estim31_top3_20x10_20261030.json')['ranked_healthy_20x10']
        cls.trajectory = data('estim31_top3_decade_trajectory_20261030.json')['qualified_candidates']
        cls.accounts = data('estim31_ten_v161_accounts_1979_20261030.json')
        cls.report = (DOC / 'estim31_priorites_20x10_20261030.md').read_text(encoding='utf-8')
        cls.tasks = (DOC / 'taches.md').read_text(encoding='utf-8')

    def test_same_source_and_complete_sanity(self):
        self.assertEqual(len(self.ranked), 3)
        self.assertEqual(len(self.trajectory), 3)
        seed_set = None
        for candidate in self.ranked:
            self.assertEqual(candidate['health'], '40/40 complete')
            self.assertEqual(len(candidate['pairs']), 20)
            self.assertEqual(candidate['source_provenance'],
                             '40x5 frozen SHA matches 20x10 and all annual checkpoints')
            if seed_set is None:
                seed_set = set(candidate['pairs'])
            self.assertEqual(set(candidate['pairs']), seed_set)
            self.assertAlmostEqual(100 * candidate['opex_profit_mean'] /
                                   candidate['aaa_profit_mean'], candidate['ratio_pct'], places=10)

    def test_winner_correct_and_19_seed_losses(self):
        top = self.ranked[0]
        self.assertEqual(top['suite'], 'v161')
        self.assertAlmostEqual(top['ratio_pct'], 66.55772625601193, places=8)
        self.assertEqual(top['opex_wins'], 1)
        self.assertEqual(sum(pair['opex'] < pair['aaa']
                             for pair in top['pairs'].values()), 19)
        self.assertTrue(top['ratio_pct'] > self.ranked[1]['ratio_pct']
                        > self.ranked[2]['ratio_pct'])

    def test_ten_years_timing_and_growth(self):
        winner = self.trajectory[0]
        self.assertEqual(winner['suite'], 'v161')
        by_year = {int(y['date'][:4]): y['variant'] for y in winner['years']}
        self.assertEqual(set(by_year), set(range(1970, 1980)))
        self.assertAlmostEqual(by_year[1974]['ratio_of_means_pct'], 103.24, delta=.01)
        self.assertAlmostEqual(by_year[1975]['ratio_of_means_pct'], 88.88, delta=.01)
        self.assertAlmostEqual(by_year[1979]['ratio_of_means_pct'], 66.55772625601193)
        y74, y79 = by_year[1974], by_year[1979]
        self.assertAlmostEqual(y79['opex']['profit_year']-y74['opex']['profit_year'],
                               1_342_885, delta=3)
        self.assertAlmostEqual(y79['aaa']['profit_year']-y74['aaa']['profit_year'],
                               3_572_406, delta=3)
        self.assertAlmostEqual(y79['opex']['train_stock'], 29.55, places=2)
        self.assertAlmostEqual(y79['aaa']['train_stock'], 56.25, places=2)
        self.assertAlmostEqual(y79['opex']['aircraft_stock'], 84.25, places=2)
        self.assertAlmostEqual(y79['aaa']['aircraft_stock'], 48.0, places=2)
        self.assertAlmostEqual(y79['opex']['cash'], 14_742_506.8)
        self.assertEqual(y79['opex']['current_loan'], 0)
        for cand in self.trajectory:
            ys = {int(y['date'][:4]): y['variant']['ratio_of_means_pct'] for y in cand['years']}
            self.assertGreater(ys[1974], 100)
            self.assertLess(ys[1975], 100)

    def test_plyr_ytd_revenues_and_net_expenditure(self):
        items = self.accounts['mean_1979_ytd_net_postings']
        o = items['estim31v161_mix_a200_r075_w15_slope:OpexAI']
        a = items['estim31v161_mix_a200_r075_w15_slope:AAAHogEx']
        self.assertAlmostEqual(-o['train_revenue'], 799_231.15)
        self.assertAlmostEqual(-a['train_revenue'], 1_967_012.70)
        self.assertAlmostEqual(o['train_revenue'] - a['train_revenue'], 1_167_781.55)
        self.assertAlmostEqual(o['aircraft_revenue']-a['aircraft_revenue'], 857_232.60)
        self.assertAlmostEqual(o['construction_all_modes'], 60_677.45)
        self.assertAlmostEqual(o['new_vehicles_net_all_modes'], 167_348.70)
        self.assertAlmostEqual(a['new_vehicles_net_all_modes'], 719_492.75)
        self.assertIn('LESS sales', self.accounts['limitations'])

    def test_tasks_and_provenance_protect_against_reruns(self):
        for task in ('POST-1974-ENTONNOIR', 'RAIL-RENDEMENT-TARDIF',
                     'AIR-PRODUCTIVITÉ', 'QUALITÉ-TESTS-ESTIM31'):
            self.assertIn(task, self.tasks)
        self.assertIn('Aucun nouveau 1×10 lancé', self.tasks)
        self.assertIn('Aucun banc supplémentaire', self.report)
        self.assertIn('non transposable', self.tasks)
        self.assertIn('estim31_ten_v161_accounts_1979_20261030.json', self.report)


if __name__ == '__main__':
    unittest.main()
