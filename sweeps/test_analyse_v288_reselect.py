#!/usr/bin/env python3
"""Tests unitaires pour l'analyseur des re-sélections (analyse_v288_reselect.py)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyse_v288_reselect import (
    aggregate_all_seeds,
    analyse_single_seed,
    compute_exclusive_op,
    days_between,
    ordinal,
    parse_log_reselect,
    render_markdown,
    seed_from_path,
)

SYNTHETIC_LOG = """\
[script:4] [0] [I] OPEX 1970-1-10 SPAN id=1 par=0 dep=0 n=loop.orch ds=1970-1-10 t0=100 tk=10 op=50000
[script:4] [0] [I] OPEX 1970-1-10 B6_PORTFOLIO path=reselect snapshot_budget=100000 live_budget=100000 actual_mode=air actual_profit=5000 actual_cap=20000 actual_rank_score=100
[script:4] [0] [I] OPEX 1970-1-10 SPAN id=3 par=2 dep=2 n=pub.select.flatten ds=1970-1-10 t0=101 tk=0 op=100
[script:4] [0] [I] OPEX 1970-1-10 SPAN id=4 par=2 dep=2 n=pub.select.score ds=1970-1-10 t0=101 tk=1 op=1000
[script:4] [0] [I] OPEX 1970-1-10 SPAN id=2 par=1 dep=1 n=select.reselect ds=1970-1-10 t0=101 tk=1 op=1200
[script:4] [0] [I] OPEX 1970-1-10 B6_PORTFOLIO path=reselect snapshot_budget=100000 live_budget=100000 actual_mode=air actual_profit=5000 actual_cap=20000 actual_rank_score=100
[script:4] [0] [I] OPEX 1970-1-10 SPAN id=6 par=5 dep=2 n=pub.select.flatten ds=1970-1-10 t0=105 tk=0 op=100
[script:4] [0] [I] OPEX 1970-1-10 SPAN id=5 par=1 dep=1 n=select.reselect ds=1970-1-10 t0=105 tk=0 op=500
[script:4] [0] [I] OPEX 1970-1-12 SPAN id=10 par=1 dep=1 n=fleet.inject ds=1970-1-12 t0=200 tk=5 op=20000
[script:4] [0] [I] OPEX 1970-1-12 B6_PORTFOLIO path=reselect snapshot_budget=100000 live_budget=100000 actual_mode=rail actual_profit=8000 actual_cap=30000 actual_rank_score=150
[script:4] [0] [I] OPEX 1970-1-12 SPAN id=12 par=11 dep=3 n=pub.select.score ds=1970-1-12 t0=201 tk=1 op=2000
[script:4] [0] [I] OPEX 1970-1-12 SPAN id=11 par=10 dep=2 n=select.reselect ds=1970-1-12 t0=201 tk=1 op=2500
[script:4] [0] [I] OPEX 1971-1-5 B6_PORTFOLIO path=reselect snapshot_budget=150000 live_budget=150000 actual_mode=rail actual_profit=8000 actual_cap=30000 actual_rank_score=150
[script:4] [0] [I] OPEX 1971-1-5 SPAN id=21 par=1 dep=1 n=select.reselect ds=1971-1-5 t0=300 tk=1 op=800
[script:4] [1] [I] OPEX 1970-1-10 SPAN id=99 par=0 dep=0 n=select.reselect ds=1970-1-10 t0=1 tk=1 op=9999
"""


class TestAnalyseV288Reselect(unittest.TestCase):
    def test_calendar_and_seed(self):
        self.assertEqual(ordinal(1970, 1, 1), 1970 * 365)
        self.assertEqual(ordinal(1970, 1, 10), 1970 * 365 + 9)
        self.assertEqual(days_between((1970, 1, 10), (1970, 1, 12)), 2)
        self.assertEqual(days_between((1970, 1, 10), (1970, 1, 10)), 0)
        self.assertEqual(days_between((1970, 12, 31), (1971, 1, 1)), 1)
        self.assertEqual(seed_from_path("reference_seed42_r0.log"), "42")
        self.assertEqual(seed_from_path("/dir/reference_seed1234_r0.log"), "1234")
        self.assertEqual(seed_from_path("custom_log.txt"), "custom_log")

    def test_synthetic_log_analysis(self):
        spans, children, reselect_events = parse_log_reselect(SYNTHETIC_LOG, company_filter=0)

        # Compagnie 1 doit être ignorée (span 99 filtré)
        self.assertEqual(len(reselect_events), 4)
        self.assertNotIn('99', spans)

        # Vérification des spans select.reselect et de leurs enfants
        s2 = spans['2']
        self.assertEqual(s2['op'], 1200)
        # s2 a pour enfants directs id 3 (op 100) et id 4 (op 1000)
        # exclusif = 1200 - 1100 = 100
        self.assertEqual(compute_exclusive_op(s2, children), 100)

        s5 = spans['5']
        self.assertEqual(s5['op'], 500)
        # s5 a pour enfant id 6 (op 100), exclusif = 500 - 100 = 400
        self.assertEqual(compute_exclusive_op(s5, children), 400)

        s11 = spans['11']
        self.assertEqual(s11['op'], 2500)
        # s11 a pour enfant id 12 (op 2000), exclusif = 2500 - 2000 = 500
        self.assertEqual(compute_exclusive_op(s11, children), 500)

        s21 = spans['21']
        self.assertEqual(s21['op'], 800)
        # s21 n'a pas d'enfant direct, exclusif = 800
        self.assertEqual(compute_exclusive_op(s21, children), 800)

        report = analyse_single_seed(spans, children, reselect_events, "test_seed")

        self.assertEqual(report['total_count'], 4)
        # total_inc_ops = 1200 + 500 + 2500 + 800 = 5000
        self.assertEqual(report['total_inc_ops'], 5000)
        # total_exc_ops = 100 + 400 + 500 + 800 = 1800
        self.assertEqual(report['total_exc_ops'], 1800)

        # Année 1970
        y1970 = report['years'][1970]
        self.assertEqual(y1970['count'], 3)
        self.assertEqual(y1970['inc_ops'], 4200)
        self.assertEqual(y1970['exc_ops'], 1000)

        # Appelants 1970 : 2 par loop.orch (id 2 et id 5), 1 par fleet.inject (id 11)
        self.assertEqual(y1970['callers']['loop.orch']['count'], 2)
        self.assertEqual(y1970['callers']['fleet.inject']['count'], 1)

        # Stabilité du choix en 1970 :
        # Item 1: air, 5000, 20000
        # Item 2: air, 5000, 20000 -> same (1)
        # Item 3: rail, 8000, 30000 -> diff (1)
        self.assertEqual(y1970['same_choice_year_reset'], 1)
        self.assertEqual(y1970['diff_choice_year_reset'], 1)

        # Année 1971
        y1971 = report['years'][1971]
        self.assertEqual(y1971['count'], 1)
        # Item 4: 1er item de 1971 -> 0 comparaison si reset
        self.assertEqual(y1971['same_choice_year_reset'], 0)
        self.assertEqual(y1971['diff_choice_year_reset'], 0)
        # En continu : compare avec Item 3 (rail, 8000, 30000) -> same !
        self.assertEqual(y1971['same_choice_continuous'], 1)

        # Intervalles :
        # Item 1 -> Item 2 : 0 jour (1970-1-10 -> 1970-1-10)
        # Item 2 -> Item 3 : 2 jours (1970-1-10 -> 1970-1-12)
        # Item 3 -> Item 4 : 358 jours (1970-1-12 -> 1971-1-5)
        # En 1970 : intervalles = [0, 2] -> médiane = 1.0, <1j = 50%, <7j = 100%
        self.assertEqual(y1970['intervals']['median_days'], 1.0)
        self.assertEqual(y1970['intervals']['pct_lt_1d'], 50.0)
        self.assertEqual(y1970['intervals']['pct_lt_7d'], 100.0)

        # Agrégation
        agg = aggregate_all_seeds([report])
        self.assertEqual(agg['total_count'], 4)
        self.assertEqual(agg['total_inc_ops'], 5000)
        self.assertEqual(agg['total_exc_ops'], 1800)
        self.assertEqual(agg['same_choice_year_reset'], 1)
        self.assertEqual(agg['same_choice_continuous'], 2)

        # Rendu markdown
        md = render_markdown([report], agg)
        self.assertIn("Audit et Vérification Quantitative des Re-sélections", md)
        self.assertIn("pub.select.score", md)
        self.assertIn("fleet.inject", md)


if __name__ == "__main__":
    unittest.main()
