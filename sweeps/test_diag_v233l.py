#!/usr/bin/env python3
"""Tests unitaires pour sweeps/diag_v233l.py."""
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_v233l import (
    DiagV233LLogParser,
    EVENT_CITATIONS,
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
        # A single track line that receives additional trains via V190 add_train or V284
        log_content = [
            "OPEX 1972-5-2 RAIL_BUILD line=20 src=5000 dst=6000 cargo=GOOD dist=190 trains=1 wagons=5",
            "OPEX 1972-5-2 V190 action=fallback_single line=5000->6000 trains=1 reason=LOOPFAIL step=LOOP skip=4",
            # Train addition 1: V190 add_train
            "OPEX 1973-2-10 V190 action=add_train line=20 trains=2 reason=OK",
            # Train addition 2: V284
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

        # Verify cross-referenced train addition events with file:line citations
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
            # Year 1972: Profit negative, wait_a present
            "OPEX 1972-1-15 LINE_REVENUE line=30 mode=rail cargo=COAL year=1972 real_prof=-1200 vehs=1 wait_a=20",
            # Year 1973: Profit zero, wait_a absent
            "OPEX 1973-1-15 LINE_REVENUE line=30 mode=rail cargo=COAL year=1973 real_prof=0 vehs=1",
            # Year 1974: Profit positive
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

        # Vehicle level logs absent -> 'non journalisé'
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
        self.assertEqual(counts["V233L_REINFORCE"], 1)
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


if __name__ == "__main__":
    unittest.main()
