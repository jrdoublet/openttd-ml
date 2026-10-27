#!/usr/bin/env python3
"""Tests unitaires pour sweeps/diag_v233l.py."""
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

from sweeps.diag_v233l import (
    DiagV233LLogParser,
    EVENT_CITATIONS,
    compare_summaries,
    format_comparison_text,
    format_report_text,
    parse_filename_meta,
    run_diag,
)


class TestDiagV233LMeta(unittest.TestCase):
    def test_filename_parsing(self):
        arm, seed, rep = parse_filename_meta("reference_seed42_r0.log")
        self.assertEqual(arm, "reference")
        self.assertEqual(seed, "42")
        self.assertEqual(rep, "0")

        arm, seed, rep = parse_filename_meta("/path/to/v233_long_good_seed100_r1.log.gz")
        self.assertEqual(arm, "v233_long_good")
        self.assertEqual(seed, "100")
        self.assertEqual(rep, "1")

        arm, seed, rep = parse_filename_meta("OpexAI_seed999.log")
        self.assertEqual(arm, "OpexAI")
        self.assertEqual(seed, "999")
        self.assertEqual(rep, "0")


class TestDiagV233LLogParser(unittest.TestCase):
    def _create_synthetic_log(self, lines, filename="v233l_seed42_r0.log", is_gz=False):
        tmp_dir = tempfile.mkdtemp()
        filepath = Path(tmp_dir) / filename
        content = "\n".join(lines) + "\n"
        if is_gz:
            with gzip.open(filepath, "wt", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(filepath, "wt", encoding="utf-8") as f:
                f.write(content)
        return filepath

    def test_good_line_double_and_single_track(self):
        log_content = [
            "OPEX 1972-5-2 RAIL_BUILD line=10 src=1000 dst=2000 cargo=GOOD dist=180 trains=2 wagons=6",
            "OPEX 1972-5-2 V190 action=build_double line=10 trains=2 reason=OK",
            "OPEX 1973-6-10 RAIL_BUILD line=11 src=3000 dst=4000 cargo=GOOD dist=220 trains=1 wagons=5",
            "OPEX 1973-6-10 V190 action=fallback_single line=11 trains=1 reason=TRK2FAIL step=BUILD_TRACK skip=4",
            "OPEX 1974-1-10 LINE_REVENUE line=10 mode=rail cargo=GOOD year=1974 real_prof=50000 vehs=2 double=1 dist=180 wait_a=15",
            "OPEX 1974-1-10 LINE_REVENUE line=11 mode=rail cargo=GOOD year=1974 real_prof=25000 vehs=1 double=0 dist=220 wait_a=40",
        ]
        log_path = self._create_synthetic_log(log_content)
        parser = DiagV233LLogParser(log_path)
        summary = parser.parse()

        self.assertEqual(summary["rail_lines_total"], 2)
        self.assertEqual(summary["lines_by_cargo"], {"GOOD": 2})

        good_lines = summary["good_lines"]
        self.assertEqual(len(good_lines), 2)

        # Line 10: Double track
        l10 = next(l for l in good_lines if l["line_id"] == "10")
        self.assertEqual(l10["dist"], 180)
        self.assertEqual(l10["trains"], 2)
        self.assertTrue(l10["double_track"])
        self.assertIn("V190 build_double", l10["double_track_source"])
        self.assertIsNone(l10["fallback_single"])

        # Line 11: Single track with fallback
        l11 = next(l for l in good_lines if l["line_id"] == "11")
        self.assertEqual(l11["dist"], 220)
        self.assertEqual(l11["trains"], 1)
        self.assertFalse(l11["double_track"])
        self.assertIsNotNone(l11["fallback_single"])
        self.assertEqual(l11["fallback_single"]["reason"], "TRK2FAIL")
        self.assertEqual(l11["fallback_single"]["step"], "BUILD_TRACK")

        # No alert on single track with 1 train
        self.assertEqual(len(summary["single_track_multi_train_alerts"]), 0)

    def test_alert_single_track_multi_train_cross_events(self):
        log_content = [
            "OPEX 1972-5-2 RAIL_BUILD line=20 src=5000 dst=6000 cargo=GOOD dist=190 trains=1 wagons=5",
            "OPEX 1972-5-2 V190 action=fallback_single line=5000->6000 trains=1 reason=LOOPFAIL step=LOOP skip=4",
            "OPEX 1973-2-10 V190 action=add_train line=20 trains=2 reason=OK",
            "OPEX 1974-3-15 V284 action=done line=20 kind=train old_vehicle=123 new_vehicle=456 wagons=5 trains=3",
            "OPEX 1975-1-10 LINE_REVENUE line=20 mode=rail cargo=GOOD year=1975 real_prof=-150 vehs=3 double=0 dist=190 wait_a=80",
        ]
        log_path = self._create_synthetic_log(log_content)
        parser = DiagV233LLogParser(log_path)
        summary = parser.parse()

        alerts = summary["single_track_multi_train_alerts"]
        self.assertEqual(len(alerts), 1)
        al = alerts[0]
        self.assertEqual(al["line_id"], "20")
        self.assertEqual(al["cargo"], "GOOD")
        self.assertEqual(al["trains"], 3)
        self.assertIsNotNone(al["fallback_single"])
        self.assertEqual(al["fallback_single"]["reason"], "LOOPFAIL")

        additions = al["train_additions"]
        self.assertEqual(len(additions), 2)
        v190_add = additions[0]
        self.assertEqual(v190_add["action"], "V190 add_train")
        self.assertEqual(v190_add["citation"], EVENT_CITATIONS["V190_add_train"])
        self.assertEqual(v190_add["citation"], "ai/OpexAI/task_rail.nut:516")

        v284_add = additions[1]
        self.assertEqual(v284_add["action"], "V284 done (train)")
        self.assertEqual(v284_add["citation"], EVENT_CITATIONS["V284_done_train"])
        self.assertEqual(v284_add["citation"], "ai/OpexAI/task_v284.nut:465")

    def test_blocked_or_useless_trains_and_missing_fields(self):
        log_content = [
            "OPEX 1971-1-10 RAIL_BUILD line=30 src=11 dst=22 cargo=COAL dist=80 trains=1 wagons=4",
            "OPEX 1972-1-15 LINE_REVENUE line=30 mode=rail cargo=COAL year=1972 real_prof=-1200 vehs=1 wait_a=20",
            "OPEX 1973-1-15 LINE_REVENUE line=30 mode=rail cargo=COAL year=1973 real_prof=0 vehs=1",
            "OPEX 1974-1-15 LINE_REVENUE line=30 mode=rail cargo=COAL year=1974 real_prof=15000 vehs=1 wait_a=0",
        ]
        log_path = self._create_synthetic_log(log_content)
        parser = DiagV233LLogParser(log_path)
        summary = parser.parse()

        blocked = summary["blocked_lines"]
        self.assertEqual(len(blocked), 1)
        bl = blocked[0]
        self.assertEqual(bl["line_id"], "30")
        self.assertEqual(len(bl["unprofitable_years"]), 2)

        y72 = bl["unprofitable_years"][0]
        self.assertEqual(y72["year"], "1972")
        self.assertEqual(y72["real_prof"], -1200.0)
        self.assertEqual(y72["wait_a"], "20")

        y73 = bl["unprofitable_years"][1]
        self.assertEqual(y73["year"], "1973")
        self.assertEqual(y73["real_prof"], 0.0)
        self.assertEqual(y73["wait_a"], "non journalisé")

        self.assertFalse(summary["vehicle_level_telemetry"]["available"])
        self.assertEqual(summary["vehicle_level_telemetry"]["status"], "non journalisé")

    def test_v233l_events_counting(self):
        log_content = [
            "OPEX 1973-1-1 V233L_QUOTE line=10 src=59522 dst=24111 dist=210 score=1200",
            "OPEX 1973-1-2 V233L_QUOTE line=11 src=44972 dst=12124 dist=150 score=950",
            "OPEX 1973-2-15 V233L_BUILD line=70 src=59522 dst=24111 double=1 trains=2",
            "OPEX 1974-6-10 V233L_REINFORCE line=70 stock=350 extra_train=1",
        ]
        log_path = self._create_synthetic_log(log_content)
        parser = DiagV233LLogParser(log_path)
        summary = parser.parse()

        counts = summary["v233l_events_count"]
        self.assertEqual(counts["V233L_QUOTE"], 2)
        self.assertEqual(counts["V233L_BUILD"], 1)
        self.assertEqual(counts["V233L_REFORCE" if "V233L_REFORCE" in counts else "V233L_REINFORCE"], 1)
        self.assertEqual(summary["v233l_events_total"], 4)

    def test_gzipped_log(self):
        log_content = [
            "OPEX 1971-1-10 RAIL_BUILD line=40 src=11 dst=22 cargo=WOOD dist=95 trains=1 wagons=4",
            "OPEX 1972-1-15 LINE_REVENUE line=40 mode=rail cargo=WOOD year=1972 real_prof=10000 vehs=1 wait_a=10",
        ]
        log_path = self._create_synthetic_log(log_content, filename="test_seed99_r0.log.gz", is_gz=True)
        parser = DiagV233LLogParser(log_path)
        summary = parser.parse()

        self.assertEqual(summary["rail_lines_total"], 1)
        self.assertEqual(summary["lines_by_cargo"], {"WOOD": 1})
        self.assertEqual(summary["seed"], "99")

    def test_format_report_text(self):
        log_content = [
            "OPEX 1972-5-2 RAIL_BUILD line=10 src=1000 dst=2000 cargo=GOOD dist=180 trains=2 wagons=6",
            "OPEX 1972-5-2 V190 action=build_double line=10 trains=2 reason=OK",
            "OPEX 1973-6-10 RAIL_BUILD line=11 src=3000 dst=4000 cargo=GOOD dist=220 trains=2 wagons=5",
            "OPEX 1973-6-10 V190 action=fallback_single line=11 trains=1 reason=TRK2FAIL step=BUILD_TRACK skip=4",
            "OPEX 1974-1-1 V190 action=add_train line=11 trains=2 reason=OK",
            "OPEX 1975-1-1 LINE_REVENUE line=11 mode=rail cargo=GOOD year=1975 real_prof=-500 vehs=2 wait_a=100",
            "OPEX 1975-2-1 V233L_GROWTH line=11 status=saturated",
        ]
        log_path = self._create_synthetic_log(log_content)
        parser = DiagV233LLogParser(log_path)
        summary = parser.parse()
        report = format_report_text(summary)

        self.assertIn("Rapport Smoke Diag V233L", report)
        self.assertIn("GOOD   : 2 ligne(s)", report)
        self.assertIn("Ligne 10 : 180 tuiles, 2 train(s), DOUBLE VOIE", report)
        self.assertIn("Ligne 11 : 220 tuiles, 2 train(s), VOIE UNIQUE", report)
        self.assertIn("[ALERTE] Ligne 11 (cargo=GOOD, 220 tuiles) : VOIE UNIQUE avec 2 trains !", report)
        self.assertIn("ai/OpexAI/task_rail.nut:516", report)
        self.assertIn("profit nul ou négatif", report)
        self.assertIn("V233L_GROWTH : 1", report)

    def test_v233l_site_search_breakdown(self):
        # Format réel : [script:4] [0] [I] OPEX AAAA-M-J ...
        log_content = [
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE src=6172 dst=46727 side=A phase=admission reason=OK plans=4 length=3 ring=2 ops=17081 clear=4 cargo=4 cmd=4 terrain=21 acceptance=0 parallel=12 authority=0 native=0 catchment=0 spread=0 error=0",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE_PLAN src=6172 dst=46727 side=A phase=admission anchor=5915 parallel=5914 direction=2 length=3 exit=5915 lead=5659 cargo_value=1 threshold=1",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE src=6172 dst=46727 side=B phase=admission reason=budget plans=0 length=3 ring=3 ops=20509 clear=0 cargo=0 cmd=0 terrain=66 acceptance=0 parallel=8 authority=0 native=0 catchment=0 spread=0 error=0",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE src=62245 dst=46727 side=A phase=admission reason=OK plans=4 length=2 ring=1 ops=9221 clear=4 cargo=4 cmd=4 terrain=14 acceptance=0 parallel=3 authority=0 native=0 catchment=0 spread=0 error=0",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE src=62245 dst=46727 side=B phase=admission reason=OK plans=2 length=2 ring=4 ops=15000 clear=2 cargo=2 cmd=2 terrain=30 acceptance=0 parallel=5 authority=0 native=0 catchment=0 spread=0 error=0",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE src=3000 dst=4000 side=A phase=admission reason=total_budget plans=0 length=2 ring=5 ops=22000",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE_STEP src=3000 dst=4000 side=A station=-1 action=continue from=4:0:0 next=5:0:0 reason=total_budget slices=2 ops=22000 total_ops=240000 limit=240000 early_acceptance=0",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE_WAIT src=3000 dst=4000 reason=SITE_PENDING phase=admission site_a=budget site_b=OK",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE_LIMIT src=3000 dst=4000",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_REJECT reason=SITE_BUDGET src=6172 dst=46727 phase=admission site_a=OK site_b=budget",
        ]
        log_path = self._create_synthetic_log(log_content)
        parser = DiagV233LLogParser(log_path)
        summary = parser.parse()

        site_search = summary["site_search"]

        # Côté A
        side_a = site_search["A"]
        self.assertEqual(side_a["searches"], 3)
        self.assertEqual(side_a["ok_count"], 2)
        self.assertEqual(side_a["budget_count"], 0)
        self.assertEqual(side_a["other_reasons"], {"total_budget": 1})
        self.assertEqual(side_a["other_reasons_count"], 1)
        self.assertEqual(side_a["opcodes"]["median"], 17081.0)
        self.assertEqual(side_a["opcodes"]["max"], 22000)
        self.assertEqual(side_a["opcodes"]["sum"], 17081 + 9221 + 22000)
        self.assertEqual(side_a["rings"]["min"], 1)
        self.assertEqual(side_a["rings"]["max"], 5)
        self.assertEqual(side_a["rings"]["counts"], {1: 1, 2: 1, 5: 1})
        self.assertEqual(side_a["opcodes"]["cumul_par_paire"]["6172->46727"], 17081)
        self.assertEqual(side_a["opcodes"]["cumul_par_paire"]["62245->46727"], 9221)
        self.assertEqual(side_a["opcodes"]["cumul_par_paire"]["3000->4000"], 22000)
        self.assertEqual(side_a["plans_count"], 1)
        self.assertEqual(side_a["step_count"], 1)

        # Côté B
        side_b = site_search["B"]
        self.assertEqual(side_b["searches"], 2)
        self.assertEqual(side_b["ok_count"], 1)
        self.assertEqual(side_b["budget_count"], 1)
        self.assertEqual(side_b["opcodes"]["median"], (20509 + 15000) / 2)
        self.assertEqual(side_b["opcodes"]["max"], 20509)
        self.assertEqual(side_b["opcodes"]["sum"], 20509 + 15000)
        self.assertEqual(side_b["rings"]["min"], 3)
        self.assertEqual(side_b["rings"]["max"], 4)
        self.assertEqual(side_b["opcodes"]["cumul_par_paire"]["6172->46727"], 20509)
        self.assertEqual(side_b["opcodes"]["cumul_par_paire"]["62245->46727"], 15000)

        # Total
        tot = site_search["total"]
        self.assertEqual(tot["searches"], 5)
        self.assertEqual(tot["opcodes"]["sum"], 48302 + 35509)
        self.assertEqual(tot["opcodes"]["cumul_par_paire"]["6172->46727"], 17081 + 20509)

        # Événements associés
        evs = summary["site_events_summary"]
        self.assertEqual(evs["V233L_SITE"], 5)
        self.assertEqual(evs["V233L_SITE_STEP"], 1)
        self.assertEqual(evs["V233L_SITE_WAIT"], 1)
        self.assertGreaterEqual(evs["V233L_SITE_PENDING"], 1)
        self.assertEqual(evs["V233L_SITE_LIMIT"], 1)
        self.assertEqual(evs["V233L_SITE_PLAN"], 1)

        # Format texte
        report = format_report_text(summary)
        self.assertIn("5. Recherche de site V233L (A/B) :", report)
        self.assertIn("Côté A : 3 recherche(s)", report)
        self.assertIn("Côté B : 2 recherche(s)", report)
        self.assertIn("V233L_SITE=5", report)

    def test_v233l_site_b_join(self):
        log_content = [
            "[script:4] [0] [I] OPEX 1974-5-10 V233L_SITE_B_JOIN src=6172 dst=46727 phase=admission_first station=5 ok=1 reason=OK ops=14200 scan_ops=12000",
            "[script:4] [0] [I] OPEX 1974-5-11 V233L_SITE_B_JOIN src=6172 dst=46727 phase=admission_first station=-1 ok=0 reason=no_airport ops=100 scan_ops=0",
            "[script:4] [0] [I] OPEX 1974-5-12 V233L_SITE_B_JOIN src=62245 dst=46727 phase=admission_first station=8 ok=0 reason=distance ops=1500 scan_ops=1200",
            "[script:4] [0] [I] OPEX 1974-5-13 V233L_SITE_B_JOIN src=62245 dst=46727 phase=recheck station=5 ok=0 reason=native ops=2500 scan_ops=0",
        ]
        log_path = self._create_synthetic_log(log_content)
        parser = DiagV233LLogParser(log_path)
        summary = parser.parse()

        join = summary["site_b_join"]
        self.assertEqual(join["attempts"], 4)
        self.assertEqual(join["successes"], 1)
        self.assertEqual(join["failures"], 3)
        self.assertEqual(join["failures_by_reason"], {"no_airport": 1, "distance": 1, "native": 1})
        self.assertEqual(join["reasons"], {"OK": 1, "no_airport": 1, "distance": 1, "native": 1})

        cost = join["cost"]
        self.assertEqual(cost["total_ops"], 14200 + 100 + 1500 + 2500)
        self.assertEqual(cost["max_ops"], 14200)
        self.assertEqual(cost["min_ops"], 100)
        self.assertEqual(cost["median_ops"], 2000.0)
        self.assertEqual(cost["total_scan_ops"], 12000 + 1200)

        report = format_report_text(summary)
        self.assertIn("6. Jointure de site B (V233L_SITE_B_JOIN) :", report)
        self.assertIn("Tentatives : 4 (succès : 1, échecs : 3)", report)
        self.assertIn("no_airport : 1", report)
        self.assertIn("distance : 1", report)
        self.assertIn("native : 1", report)
        self.assertIn("total = 18300 ops", report)

    def test_v233l_site_funnel_tolerant(self):
        # Format prévu : V233L_SITE_FUNNEL town= axis= radius= tiles= buildable= accepting= checked= ok= ops= reason=
        log_content = [
            # Ligne complète nominale
            "[script:4] [0] [I] OPEX 1975-2-12 V233L_SITE_FUNNEL town=12 axis=1 radius=6 tiles=20 buildable=15 accepting=10 checked=5 ok=1 ops=1200 reason=OK",
            # Champs vides / manquants town= axis=
            "[script:4] [0] [I] OPEX 1975-2-12 V233L_SITE_FUNNEL town= axis= radius=4 tiles=12 buildable=8 accepting=0 checked=0 ok=0 ops=800 reason=no_acceptance",
            # Ordre différent et champ imprévu
            "[script:4] [0] [I] OPEX 1975-2-12 V233L_SITE_FUNNEL reason=terrain ok=0 ops=2400 tiles=15 checked=10 unpredicted_field=999",
            # ok=true
            "[script:4] [0] [I] OPEX 1975-2-12 V233L_SITE_FUNNEL town=14 ok=true ops=1600 reason=OK",
        ]
        log_path = self._create_synthetic_log(log_content)
        parser = DiagV233LLogParser(log_path)
        summary = parser.parse()

        funnel = summary["site_funnel"]
        self.assertEqual(funnel["count"], 4)
        self.assertEqual(funnel["successes"], 2)
        self.assertEqual(funnel["failures"], 2)
        self.assertEqual(funnel["by_reason"], {"OK": 2, "no_acceptance": 1, "terrain": 1})

        cost = funnel["cost"]
        self.assertEqual(cost["total_ops"], 1200 + 800 + 2400 + 1600)
        self.assertEqual(cost["min_ops"], 800)
        self.assertEqual(cost["max_ops"], 2400)
        self.assertEqual(cost["median_ops"], 1400.0)

        # Agrégats par motif
        c_by_r = funnel["cost_by_reason"]
        self.assertEqual(c_by_r["OK"]["count"], 2)
        self.assertEqual(c_by_r["OK"]["total_ops"], 2800)
        self.assertEqual(c_by_r["OK"]["mean_ops"], 1400.0)
        self.assertEqual(c_by_r["no_acceptance"]["count"], 1)
        self.assertEqual(c_by_r["no_acceptance"]["total_ops"], 800)
        self.assertEqual(c_by_r["terrain"]["count"], 1)
        self.assertEqual(c_by_r["terrain"]["total_ops"], 2400)

        # Agrégats globaux de tuiles
        self.assertEqual(funnel["aggregates"]["total_tiles"], 20 + 12 + 15)

        report = format_report_text(summary)
        self.assertIn("7. Entonnoir de site (V233L_SITE_FUNNEL) :", report)
        self.assertIn("Événements : 4 (succès : 2, échecs : 2)", report)
        self.assertIn("no_acceptance", report)
        self.assertIn("terrain", report)

    def test_v233l_comparison_two_logs(self):
        # Référence
        ref_lines = [
            "[script:4] [0] [I] OPEX 1972-5-2 RAIL_BUILD line=10 src=1000 dst=2000 cargo=GOOD dist=180 trains=1 wagons=6",
            "[script:4] [0] [I] OPEX 1972-5-2 V190 action=fallback_single line=10 trains=1 reason=LOOPFAIL step=LOOP skip=4",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE src=1000 dst=2000 side=A reason=OK plans=4 ops=30000 ring=2",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE src=1000 dst=2000 side=B reason=OK plans=2 ops=50000 ring=3",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE src=1000 dst=3000 side=B reason=budget plans=0 ops=20000 ring=4",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_REJECT reason=SITE_BUDGET src=1000 dst=3000",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_REJECT reason=distance src=1000 dst=4000",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_REJECT reason=distance src=1000 dst=5000",
        ]
        # Variante
        var_lines = [
            "[script:4] [0] [I] OPEX 1972-5-2 RAIL_BUILD line=10 src=1000 dst=2000 cargo=GOOD dist=180 trains=2 wagons=6",
            "[script:4] [0] [I] OPEX 1972-5-2 V190 action=build_double line=10 trains=2 reason=OK",
            "[script:4] [0] [I] OPEX 1973-6-1 RAIL_BUILD line=20 src=3000 dst=4000 cargo=GOOD dist=220 trains=2 wagons=6",
            "[script:4] [0] [I] OPEX 1973-6-1 V190 action=build_double line=20 trains=2 reason=OK",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE src=1000 dst=2000 side=A reason=OK plans=4 ops=35000 ring=2",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE src=1000 dst=2000 side=B reason=OK plans=2 ops=45000 ring=3",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE src=1000 dst=3000 side=B reason=OK plans=3 ops=48000 ring=3",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_SITE_B_JOIN src=1000 dst=4000 phase=admission_first station=50 ok=1 reason=OK ops=10000",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_REJECT reason=distance src=1000 dst=5000",
            "[script:4] [0] [I] OPEX 1972-7-10 V233L_REJECT reason=economics_or_site src=1000 dst=6000",
        ]

        ref_path = self._create_synthetic_log(ref_lines, filename="ref_seed100_r0.log")
        var_path = self._create_synthetic_log(var_lines, filename="var_seed100_r0.log")

        p_ref = DiagV233LLogParser(ref_path)
        s_ref = p_ref.parse()
        p_var = DiagV233LLogParser(var_path)
        s_var = p_var.parse()

        comp = compare_summaries(s_ref, s_var)

        # 1. Sites B trouvés
        sb = comp["sites_b_found"]
        self.assertEqual(sb["reference"], 1)  # 1 scan OK
        self.assertEqual(sb["variant"], 3)    # 2 scan OK + 1 join OK
        self.assertEqual(sb["delta"], +2)

        # 2. Opcodes de recherche
        so = comp["search_opcodes"]
        self.assertEqual(so["side_a"]["reference"], 30000)
        self.assertEqual(so["side_a"]["variant"], 35000)
        self.assertEqual(so["side_a"]["delta"], +5000)

        self.assertEqual(so["side_b"]["reference"], 70000)
        self.assertEqual(so["side_b"]["variant"], 93000)
        self.assertEqual(so["side_b"]["delta"], +23000)

        self.assertEqual(so["total"]["reference"], 100000)
        self.assertEqual(so["total"]["variant"], 128000)
        self.assertEqual(so["total"]["delta"], +28000)

        # 3. Lignes rail GOOD posées
        gl = comp["good_lines"]
        self.assertEqual(gl["count"]["reference"], 1)
        self.assertEqual(gl["count"]["variant"], 2)
        self.assertEqual(gl["count"]["delta"], +1)
        self.assertEqual(gl["double_track_count"]["reference"], 0)
        self.assertEqual(gl["double_track_count"]["variant"], 2)
        self.assertEqual(gl["double_track_count"]["delta"], +2)

        # 4. V233L_REJECT par raison
        rej = comp["v233l_reject_by_reason"]
        by_r = rej["by_reason"]
        self.assertEqual(by_r["SITE_BUDGET"]["reference"], 1)
        self.assertEqual(by_r["SITE_BUDGET"]["variant"], 0)
        self.assertEqual(by_r["SITE_BUDGET"]["delta"], -1)

        self.assertEqual(by_r["distance"]["reference"], 2)
        self.assertEqual(by_r["distance"]["variant"], 1)
        self.assertEqual(by_r["distance"]["delta"], -1)

        self.assertEqual(by_r["economics_or_site"]["reference"], 0)
        self.assertEqual(by_r["economics_or_site"]["variant"], 1)
        self.assertEqual(by_r["economics_or_site"]["delta"], +1)

        self.assertEqual(rej["total"]["reference"], 3)
        self.assertEqual(rej["total"]["variant"], 2)
        self.assertEqual(rej["total"]["delta"], -1)

        # Format texte
        comp_text = format_comparison_text(comp)
        self.assertIn("Résumé comparatif", comp_text)
        self.assertIn("1. Sites B trouvés :", comp_text)
        self.assertIn("Delta     : +2", comp_text)
        self.assertIn("2. Opcodes de recherche de site :", comp_text)
        self.assertIn("3. Lignes rail GOOD posées :", comp_text)
        self.assertIn("4. V233L_REJECT par raison :", comp_text)
        self.assertIn("SITE_BUDGET", comp_text)

        # Test run_diag avec 2 fichiers et output_json=True
        # Capture stdout
        saved_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            rc = run_diag([ref_path, var_path], output_json=True)
            self.assertEqual(rc, 0)
            output_str = sys.stdout.getvalue()
        finally:
            sys.stdout = saved_stdout

        data = json.loads(output_str)
        self.assertIn("summaries", data)
        self.assertIn("comparison", data)
        self.assertEqual(len(data["summaries"]), 2)
        self.assertEqual(data["comparison"]["sites_b_found"]["delta"], 2)


if __name__ == "__main__":
    unittest.main()
