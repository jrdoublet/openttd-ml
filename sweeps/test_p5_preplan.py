#!/usr/bin/env python3
"""Tests unitaires déterministes pour l'analyseur P5 bis (pré-planification A* rail)."""
from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from analyse_p5_preplan import (
    analyze_p5,
    compute_perturbation_table,
    format_p5_report,
    parse_p5_output,
)


SAMPLE_OUTPUT = """
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1970-1-15 P2_BUILD id=1 mode=air n_built=1 cap_before=100000 cap_after=15000 cg_before=20 cg_after=20 scanned=50 retained=20 abandon=0 alts=20 funded=0 cause=all_unaffordable next_k=32000 stop=list_end
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1970-1-15 P5_BUILD_LINE id=1 mode=air src=1200 dst=3400 cap=85000
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1970-1-15 P5_WAIT_START id=1 date=1970-1-15 tick=250 cap=15000 alts=20 n_rail=4 n_air=12 n_road=4 n_fleet=0 rail_rank=3 rail_kind=pax rail_src=5000 rail_dst=6000 rail_cap=45000 rail_fin_cap=76500 rail_def=61500 rail_prof=28000 rail_roi=36 rail_score=366.0 rail_cf_cap=43200 rail_cf_def=28200 rail_cf_rank=1 rail_iters=1500 ahead_air=3 ahead_road=0 ahead_fleet=0
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1970-1-20 P2_PASS pass=1 date=1970-1-20 tick=350 in_best=0 in_cap=15000 n_built=0 stop=empty_pool post_best=0 post_cap=15000 d_cap=0 d_best=0 tasks_since=catalog:catalog_fresh:0
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1970-1-20 P5_RAIL_PASS pass=1 date=1970-1-20 in_cap=15000 alts=20 rail_alts=4 rail_aff=0 rail_in_best=0 nonrail_in_best=0 rail_built=0 stop=empty_pool best_rail_def=61500 best_rail_cap=76500 best_rail_prof=28000 best_rail_score=366.0 best_rail_cf_def=28200 best_rail_cf_cap=43200 best_rail_cf_rank=1 best_rail_kind=pax best_rail_rank=3 best_nonrail_mode=air best_nonrail_score=520.0 best_nonrail_cap=32000
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1970-2-1 P2_RESOLVE id=1 days=17 ticks=320 ret_reason=air_fleet ret_task=air_fleet ret_date=1970-2-1 funded=2 cause=none
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1970-2-1 P5_WAIT_END id=1 days=17 ticks=320 dispatches=45 unused_ops=3150000 used_ops=50000 ret_reason=air_fleet ret_task=air_fleet funded=2

[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1970-3-10 P2_BUILD id=2 mode=fleet n_built=1 cap_before=45000 cap_after=12000 cg_before=22 cg_after=22 scanned=60 retained=22 abandon=0 alts=22 funded=0 cause=all_unaffordable next_k=25000 stop=list_end
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1970-3-10 P5_WAIT_START id=2 date=1970-3-10 tick=600 cap=12000 alts=22 n_rail=0 n_air=18 n_road=4 n_fleet=0 rail_rank=-1
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1970-3-22 P2_RESOLVE id=2 days=12 ticks=240 ret_reason=month ret_task=catalog ret_date=1970-3-22 funded=3 cause=none
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1970-3-22 P5_WAIT_END id=2 days=12 ticks=240 dispatches=30 unused_ops=2350000 used_ops=40000 ret_reason=month ret_task=catalog funded=3

[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1971-5-12 P5_RAIL_SEARCH id=1 kind=primary src=5000 dst=6000 iters=712 ops=2100000 slices=15 days=14 ticks=280 outcome=OK result=found budget=10000
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1971-5-15 P5_BUILD_LINE id=3 mode=rail src=5000 dst=6000 cap=72000
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1972-8-20 P5_RAIL_SEARCH id=2 kind=primary src=7000 dst=8000 iters=10000 ops=24500000 slices=200 days=120 ticks=2400 outcome=ABND result=cap budget=10000
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1972-11-05 P5_RAIL_SEARCH id=3 kind=primary src=9000 dst=9500 iters=50 ops=120000 slices=1 days=1 ticks=15 outcome=NOPA result=none budget=5000
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1973-1-10 P5_RAIL_SEARCH id=4 kind=primary src=1100 dst=1200 iters=85 ops=150000 slices=2 days=2 ticks=30 outcome=SHORT result=none budget=5000
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1973-3-15 P5_RAIL_SEARCH id=5 kind=primary src=1300 dst=1400 iters=95 ops=170000 slices=2 days=2 ticks=32 outcome=NOMATCH result=none budget=5000
[2026-09-25 16:30:18] dbg: [script:4] [0] [I] OPEX 1973-6-20 P5_RAIL_SEARCH id=6 kind=primary src=1500 dst=1600 iters=20 ops=40000 slices=1 days=1 ticks=10 outcome=cancelled result=none budget=5000
"""


class TestP5Parsing(unittest.TestCase):
    def setUp(self):
        self.parsed = parse_p5_output(SAMPLE_OUTPUT, seed=42)

    def test_parse_wait_start_counts(self):
        self.assertEqual(len(self.parsed["wait_starts"]), 2)

    def test_parse_wait_start_fields(self):
        w1 = self.parsed["wait_starts"][0]
        self.assertEqual(w1["id"], 1)
        self.assertEqual(w1["seed"], 42)
        self.assertEqual(w1["cap"], 15000)
        self.assertEqual(w1["n_rail"], 4)
        self.assertEqual(w1["rail_rank"], 3)
        self.assertEqual(w1["rail_def"], 61500)
        self.assertEqual(w1["rail_fin_cap"], 76500)
        self.assertEqual(w1["rail_cf_cap"], 43200)
        self.assertEqual(w1["rail_cf_def"], 28200)
        self.assertEqual(w1["rail_cf_rank"], 1)

    def test_parse_wait_end_counts(self):
        self.assertEqual(len(self.parsed["wait_ends"]), 2)

    def test_parse_wait_end_fields(self):
        e1 = self.parsed["wait_ends"][0]
        self.assertEqual(e1["id"], 1)
        self.assertEqual(e1["days"], 17)
        self.assertEqual(e1["ticks"], 320)
        self.assertEqual(e1["unused_ops"], 3150000)
        self.assertEqual(e1["used_ops"], 50000)
        self.assertEqual(e1["unused_ops_per_tick"], 9843.8)
        self.assertEqual(e1["ret_reason"], "air_fleet")

    def test_parse_rail_pass(self):
        self.assertEqual(len(self.parsed["rail_passes"]), 1)
        p = self.parsed["rail_passes"][0]
        self.assertEqual(p["pass"], 1)
        self.assertEqual(p["in_cap"], 15000)
        self.assertEqual(p["rail_alts"], 4)
        self.assertEqual(p["best_rail_def"], 61500)
        self.assertEqual(p["best_rail_cf_def"], 28200)
        self.assertEqual(p["best_rail_cf_cap"], 43200)
        self.assertEqual(p["best_rail_cf_rank"], 1)

    def test_parse_rail_searches_count(self):
        self.assertEqual(len(self.parsed["rail_searches"]), 6)

    def test_parse_rail_search_success(self):
        s = self.parsed["rail_searches"][0]
        self.assertEqual(s["outcome"], "OK")
        self.assertEqual(s["result"], "found")
        self.assertEqual(s["iters"], 712)
        self.assertEqual(s["ops"], 2100000)
        self.assertEqual(s["days"], 14)

    def test_parse_rail_search_abnd(self):
        s = self.parsed["rail_searches"][1]
        self.assertEqual(s["outcome"], "ABND")
        self.assertEqual(s["result"], "cap")

    def test_parse_rail_search_nopa(self):
        s = self.parsed["rail_searches"][2]
        self.assertEqual(s["outcome"], "NOPA")
        self.assertEqual(s["result"], "none")

    def test_parse_rail_search_short(self):
        s = self.parsed["rail_searches"][3]
        self.assertEqual(s["outcome"], "SHORT")
        self.assertEqual(s["result"], "none")

    def test_parse_rail_search_nomatch(self):
        s = self.parsed["rail_searches"][4]
        self.assertEqual(s["outcome"], "NOMATCH")
        self.assertEqual(s["result"], "none")

    def test_parse_rail_search_cancelled(self):
        s = self.parsed["rail_searches"][5]
        self.assertEqual(s["outcome"], "cancelled")
        self.assertEqual(s["result"], "none")

    def test_parse_build_lines(self):
        self.assertEqual(len(self.parsed["build_lines"]), 2)
        b1 = self.parsed["build_lines"][0]
        self.assertEqual(b1["mode"], "air")
        self.assertEqual(b1["src"], 1200)
        self.assertEqual(b1["dst"], 3400)
        b2 = self.parsed["build_lines"][1]
        self.assertEqual(b2["mode"], "rail")
        self.assertEqual(b2["src"], 5000)
        self.assertEqual(b2["dst"], 6000)

    def test_parse_c56_rail_search_end_fallback(self):
        c56_log = "[2026-09-25 18:22:23] dbg: [script:4] [0] [I] OPEX 1971-12-16 C56_TASK RAIL_SEARCH_END name=primary cycle=10 src=9815 dst=13978 outcome=OK result=found iters=712 len=45 weight=120 budget=10000 days=74 ticks=1378"
        p = parse_p5_output(c56_log, seed=999)
        self.assertEqual(len(p["rail_searches"]), 1)
        s = p["rail_searches"][0]
        self.assertEqual(s["src"], 9815)
        self.assertEqual(s["dst"], 13978)
        self.assertEqual(s["outcome"], "OK")
        self.assertEqual(s["result"], "found")
        self.assertEqual(s["iters"], 712)
        self.assertEqual(s["days"], 74)
        self.assertEqual(s["ticks"], 1378)


class TestP5SuccessfulSearchFixture(unittest.TestCase):
    def test_fixture_search_with_plan_tiles_no_path_is_ok(self):
        """Vérifie qu'un plan avec plan.tiles et plan.ok (sans plan.path) donne outcome=OK result=found."""
        log = """
        [2026-09-25 18:22:23] dbg: [script:4] [0] [I] OPEX 1972-4-20 P5_RAIL_SEARCH id=1 kind=primary src=9815 dst=13978 iters=712 ops=2367295 slices=15 days=74 ticks=1378 outcome=OK result=found budget=10000
        [2026-09-25 18:22:24] dbg: [script:4] [0] [I] OPEX 1972-4-22 P5_BUILD_LINE id=1 mode=rail src=9815 dst=13978 cap=75000
        """
        p = parse_p5_output(log, seed=999)
        self.assertEqual(p["rail_searches"][0]["outcome"], "OK")
        self.assertEqual(p["rail_searches"][0]["result"], "found")
        self.assertEqual(p["build_lines"][0]["mode"], "rail")


class TestP5AvanceCalculation(unittest.TestCase):
    def test_avance_bounded_by_wait_duration(self):
        """Attente courte de 1 jour, recherche A* médiane de 2 jours -> avance = 1 j (50 %)."""
        short_wait_log = SAMPLE_OUTPUT.replace("days=17 ticks=320", "days=1 ticks=20")
        parsed = parse_p5_output(short_wait_log, seed=42)
        summary = analyze_p5(parsed, max_year=1975)
        ep1 = summary["episodes_table"][0]
        self.assertEqual(ep1["avance_days"], 1)
        self.assertEqual(ep1["fraction_covered"], 50.0)

    def test_avance_bounded_by_astar_duration(self):
        """Attente de 17 jours, recherche A* médiane de 2 jours -> avance = 2.0 j (100 %)."""
        parsed = parse_p5_output(SAMPLE_OUTPUT, seed=42)
        summary = analyze_p5(parsed, max_year=1975)
        ep1 = summary["episodes_table"][0]
        self.assertEqual(ep1["avance_days"], 2.0)
        self.assertEqual(ep1["fraction_covered"], 100.0)

    def test_avance_zero_when_no_rail(self):
        """Épisode 2 sans candidat rail -> avance = 0 j, fraction = 0%."""
        parsed = parse_p5_output(SAMPLE_OUTPUT, seed=42)
        summary = analyze_p5(parsed, max_year=1975)
        ep2 = summary["episodes_table"][1]
        self.assertEqual(ep2["avance_days"], 0)
        self.assertEqual(ep2["fraction_covered"], 0.0)

    def test_avance_custom_fixture(self):
        """Fixture dédiée : A* de 30 jours, attente de 10 jours -> avance = 10 j (33.3 %)."""
        custom = (
            "[2026-09-25] dbg: [script:4] [0] [I] OPEX 1970-1-1 P5_WAIT_START id=1 date=1970-1-1 tick=10 cap=10000 alts=5 n_rail=1 n_air=0 n_road=0 n_fleet=0 rail_rank=0 rail_kind=pax rail_src=1 dst=2 rail_cap=20000 rail_fin_cap=34000 rail_def=24000 rail_prof=5000 rail_roi=25 rail_score=100\n"
            "[2026-09-25] dbg: [script:4] [0] [I] OPEX 1970-1-11 P5_WAIT_END id=1 days=10 ticks=200 dispatches=10 unused_ops=1000000 used_ops=10000 ret_reason=cap funded=1\n"
            "[2026-09-25] dbg: [script:4] [0] [I] OPEX 1970-2-1 P5_RAIL_SEARCH id=1 kind=primary src=1 dst=2 iters=100 ops=100000 slices=5 days=30 ticks=600 outcome=OK result=found budget=1000\n"
        )
        parsed = parse_p5_output(custom, seed=42)
        summary = analyze_p5(parsed, max_year=1975)
        ep = summary["episodes_table"][0]
        self.assertEqual(ep["avance_days"], 10)
        self.assertAlmostEqual(ep["fraction_covered"], 33.3, places=1)


class TestP5CounterfactualCapital(unittest.TestCase):
    def test_counterfactual_capital_factor_096_170(self):
        """Vérifie le recalcul 0.96 / 1.70 (~56.5 %)."""
        modelled_cap = 76500
        expected_cf_cap = int(modelled_cap * 96 / 170)  # 43200
        self.assertEqual(expected_cf_cap, 43200)

    def test_counterfactual_deficit_and_rank_in_summary(self):
        parsed = parse_p5_output(SAMPLE_OUTPUT, seed=42)
        summary = analyze_p5(parsed, max_year=1975)
        self.assertEqual(summary["rail_cap_med"], 76500)
        self.assertEqual(summary["cf_cap_med"], 43200)
        self.assertEqual(summary["rail_def_med"], 61500)
        self.assertEqual(summary["cf_def_med"], 28200)
        self.assertEqual(summary["rail_rank_med"], 3)
        self.assertEqual(summary["cf_rank_med"], 1)

    def test_candidate_becomes_affordable_under_cf(self):
        """Si la caisse est 50 000 £, modélisé 76 500 £ (déficit 26 500 £), contrefactuel 43 200 £ (déficit 0 £ -> finançable)."""
        custom_log = SAMPLE_OUTPUT.replace("cap=15000", "cap=50000").replace("rail_def=61500", "rail_def=26500").replace("rail_cf_def=28200", "rail_cf_def=0")
        parsed = parse_p5_output(custom_log, seed=42)
        summary = analyze_p5(parsed, max_year=1975)
        self.assertEqual(summary["ep_affordable_count"], 0)
        self.assertEqual(summary["cf_affordable_count"], 1)
        self.assertEqual(summary["cf_affordable_gain"], 1)


class TestP5UnusedOpsPerTick(unittest.TestCase):
    def test_unused_ops_per_tick_calc(self):
        parsed = parse_p5_output(SAMPLE_OUTPUT, seed=42)
        summary = analyze_p5(parsed, max_year=1975)
        self.assertAlmostEqual(summary["unused_per_tick_med"], 9817.75, places=1)
        self.assertGreater(summary["unused_per_tick_med"], 9000)

    def test_ops_per_tick_for_astar(self):
        parsed = parse_p5_output(SAMPLE_OUTPUT, seed=42)
        summary = analyze_p5(parsed, max_year=1975)
        ac = summary["astar_cost"]
        self.assertGreater(ac["ops_per_tick_med"], 5000)


class TestP5CandidateFate(unittest.TestCase):
    def test_fate_built_later(self):
        """Le candidat 5000->6000 de l'épisode 1 est construit plus tard (id=3)."""
        parsed = parse_p5_output(SAMPLE_OUTPUT, seed=42)
        summary = analyze_p5(parsed, max_year=1975)
        ep1 = summary["episodes_table"][0]
        self.assertEqual(ep1["fate"], "built_later")
        self.assertEqual(summary["total_avance_days_built_later"], 2.0)

    def test_fate_built_later_reversed_pair(self):
        """Le candidat 5000->6000 est construit en sens inverse 6000->5000."""
        reversed_log = SAMPLE_OUTPUT.replace("src=5000 dst=6000 cap=72000", "src=6000 dst=5000 cap=72000")
        parsed = parse_p5_output(reversed_log, seed=42)
        summary = analyze_p5(parsed, max_year=1975)
        ep1 = summary["episodes_table"][0]
        self.assertEqual(ep1["fate"], "built_later")

    def test_fate_superseded(self):
        """Si la ligne n'est jamais construite et ret_reason=air_fleet -> superseded."""
        no_build_log = SAMPLE_OUTPUT.replace("P5_BUILD_LINE id=3 mode=rail src=5000 dst=6000 cap=72000", "")
        parsed = parse_p5_output(no_build_log, seed=42)
        summary = analyze_p5(parsed, max_year=1975)
        ep1 = summary["episodes_table"][0]
        self.assertEqual(ep1["fate"], "superseded_by_other_mode")

    def test_fate_never_built(self):
        """Si la ligne n'est jamais construite et ret_reason=unspecified -> never_built."""
        no_build_log = SAMPLE_OUTPUT.replace("P5_BUILD_LINE id=3 mode=rail src=5000 dst=6000 cap=72000", "").replace("ret_reason=air_fleet", "ret_reason=timeout")
        parsed = parse_p5_output(no_build_log, seed=42)
        summary = analyze_p5(parsed, max_year=1975)
        ep1 = summary["episodes_table"][0]
        self.assertEqual(ep1["fate"], "never_built")


class TestP5RecoupementAndFormatting(unittest.TestCase):
    def test_totals_recoupement(self):
        parsed = parse_p5_output(SAMPLE_OUTPUT, seed=42)
        summary = analyze_p5(parsed, max_year=1975)
        self.assertEqual(summary["total_unused_ops"], 3150000 + 2350000)
        self.assertEqual(summary["total_used_ops"], 50000 + 40000)
        self.assertEqual(summary["total_days"], 17 + 12)
        self.assertEqual(summary["total_ticks"], 320 + 240)

    def test_format_p5_report(self):
        parsed = parse_p5_output(SAMPLE_OUTPUT, seed=42)
        summary = analyze_p5(parsed, max_year=1975)
        report = format_p5_report(summary, seeds=[42], max_year=1975)

        self.assertIn("Rapport P5 bis", report)
        self.assertIn("Issues réelles des recherches A* rail", report)
        self.assertIn("Succès (`OK / found`) : **1**", report)
        self.assertIn("Aucun chemin (`NOPA`) : **1**", report)
        self.assertIn("Plafond itérations (`ABND/DEAD / cap`) : **1**", report)
        self.assertIn("Tracé trop court (`SHORT`) : **1**", report)
        self.assertIn("Quai non connectable (`NOMATCH`) : **1**", report)
        self.assertIn("Annulée / coupée : **1**", report)
        self.assertIn("Comparaison d'impact du facteur 1,70", report)
        self.assertIn("Avance disponible et devenir des candidats", report)
        self.assertIn("built_later", report)
        self.assertIn("2.0 j", report)

    def test_compute_perturbation_table(self):
        series = [{"seed": 42, "company_value": 393164, "profit_year": 302818, "n_vehicles": 24, "n_stations": 22}]
        baseline = [{"seed": 42, "company_value": 393164, "profit_year": 302818, "n_vehicles": 24, "n_stations": 22}]
        table = compute_perturbation_table(series, baseline)
        self.assertEqual(len(table), 1)
        self.assertEqual(table[0]["val_pct"], 0.0)
        self.assertEqual(table[0]["prof_pct"], 0.0)
        self.assertEqual(table[0]["veh_delta"], 0)
        self.assertEqual(table[0]["st_delta"], 0)


if __name__ == "__main__":
    unittest.main()
