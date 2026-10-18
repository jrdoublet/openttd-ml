"""sweeps/test_v262_save_probe.py - Tests contractuels de l'instrumentation Save() (V262 T04).

Vérifie :
1. La garde stricte sous DECISION_LOG dans persist.nut (aucun opcode consommé hors DECISION_LOG).
2. Le format exact de la ligne journalisée V262_SAVE.
3. Le lecteur sweeps/analyze_v262_save.py sur des journaux fictifs (.log et .log.gz).
"""

import gzip
from pathlib import Path
import re
import sys
import tempfile
import unittest

SWEEPS_DIR = Path(__file__).resolve().parent
if str(SWEEPS_DIR) not in sys.path:
    sys.path.insert(0, str(SWEEPS_DIR))

from test_v261_forum_behaviours import body, source
from analyze_v262_save import (
    aggregate_by_seed_year,
    extrapolate_ops_vs_lah,
    extract_seed_from_filename,
    format_report_markdown,
    linear_regression,
    parse_log_file,
    parse_v262_save_line,
)


class TestSaveProbeSquirrelContracts(unittest.TestCase):
    """Contrats Squirrel sur OpexAI::Save dans persist.nut."""

    def setUp(self):
        self.save_body = body("persist.nut", "OpexAI::Save")

    def test_save_ops_measurement_strictly_guarded_by_decision_log(self):
        """AIController.GetOpsTillSuspend() ne doit être appelé que sous DECISION_LOG."""
        # 1. Vérifier l'initialisation au début de Save()
        self.assertRegex(
            self.save_body,
            r"local\s+startOps\s*=\s*null;\s*if\s*\(\s*DECISION_LOG\s*\)\s*startOps\s*=\s*AIController\.GetOpsTillSuspend\(\);",
            "startOps doit être initialisé sous garde DECISION_LOG",
        )

        # 2. Vérifier que tout GetOpsTillSuspend est précédé de DECISION_LOG
        matches = [m.start() for m in re.finditer(r"AIController\.GetOpsTillSuspend\(", self.save_body)]
        self.assertGreaterEqual(len(matches), 3, "GetOpsTillSuspend doit être appelé au début et aux deux sorties")

        for idx in matches:
            prefix = self.save_body[max(0, idx - 120):idx]
            self.assertIn("DECISION_LOG", prefix, "Chaque appel GetOpsTillSuspend() doit être sous garde DECISION_LOG")

    def test_save_probe_logging_guarded_and_both_paths_covered(self):
        """Vérifie que les deux chemins (shortSave et saveObj) journalisent V262_SAVE sous garde."""
        # Chemin shortSave (!SAVE_FULL_STATE)
        short_save_idx = self.save_body.index("return shortSave;")
        prefix_short = self.save_body[:short_save_idx]
        self.assertIn('OpexDecide("V262_SAVE"', prefix_short)
        self.assertIn("full=0", prefix_short)
        self.assertIn("if (DECISION_LOG && startOps != null)", prefix_short)

        # Chemin saveObj (SAVE_FULL_STATE)
        save_obj_idx = self.save_body.index("return saveObj;")
        prefix_full = self.save_body[short_save_idx:save_obj_idx]
        self.assertIn('OpexDecide("V262_SAVE"', prefix_full)
        self.assertIn("full=1", prefix_full)
        self.assertIn("if (DECISION_LOG && startOps != null)", prefix_full)

    def test_save_probe_format_line_tokens(self):
        """La ligne journalisée doit respecter le format exact prescrit."""
        # Format requis: V262_SAVE ops=<consommés> budget=100000 lines=<L> abandons=<A> abandonCounts=<H> tasks=<n> full=<save_full_state>
        expected_tokens = [
            '"V262_SAVE"',
            '"ops=" + opsSpent',
            '" budget=100000 lines=" + lCount',
            '" abandons=" + aCount',
            '" abandonCounts=" + hCount',
            '" tasks=" + tCount',
            '" full=0"',
            '" full=1"',
        ]
        for token in expected_tokens:
            self.assertIn(token, self.save_body, f"Token manquant dans OpexAI::Save : {token}")

    def test_save_state_counters_sourced_correctly(self):
        """Vérifie que L, A, H et n comptent fidèlement les structures d'état de l'IA."""
        self.assertIn("(this._lines != null) ? this._lines.len() : 0", self.save_body)
        self.assertIn("(this._abandonedPairs != null) ? this._abandonedPairs.len() : 0", self.save_body)
        self.assertIn("(this._abandonCounts != null) ? this._abandonCounts.len() : 0", self.save_body)
        self.assertIn("(this._taskQueue != null) ? this._taskQueue.len() : 0", self.save_body)


class TestAnalyzeV262SaveLogReader(unittest.TestCase):
    """Tests du lecteur sweeps/analyze_v262_save.py sur logs fictifs."""

    def test_parse_v262_save_line_dated(self):
        line = "dbg: [script:0] [0] [I] OPEX 1978-6-30 V262_SAVE ops=2450 budget=100000 lines=45 abandons=8 abandonCounts=12 tasks=6 full=1"
        ev = parse_v262_save_line(line)
        self.assertIsNotNone(ev)
        self.assertEqual(ev["year"], 1978)
        self.assertEqual(ev["month"], 6)
        self.assertEqual(ev["day"], 30)
        self.assertEqual(ev["ops"], 2450)
        self.assertEqual(ev["budget"], 100000)
        self.assertEqual(ev["lines"], 45)
        self.assertEqual(ev["abandons"], 8)
        self.assertEqual(ev["abandonCounts"], 12)
        self.assertEqual(ev["tasks"], 6)
        self.assertEqual(ev["full"], 1)
        self.assertEqual(ev["lah"], 65)  # 45 + 8 + 12
        self.assertEqual(ev["margin"], 97550)  # 100000 - 2450

    def test_parse_v262_save_line_short_format(self):
        line = "OPEX 1971-1-15 V262_SAVE ops=320 budget=100000 lines=0 abandons=1 abandonCounts=0 tasks=5 full=0"
        ev = parse_v262_save_line(line)
        self.assertIsNotNone(ev)
        self.assertEqual(ev["year"], 1971)
        self.assertEqual(ev["ops"], 320)
        self.assertEqual(ev["lines"], 0)
        self.assertEqual(ev["full"], 0)
        self.assertEqual(ev["lah"], 1)
        self.assertEqual(ev["margin"], 99680)

    def test_extract_seed_from_filename(self):
        self.assertEqual(extract_seed_from_filename("OpexAI_seed42_r0.log"), "42")
        self.assertEqual(extract_seed_from_filename("campaign_seed_100.log.gz"), "100")
        self.assertEqual(extract_seed_from_filename("ref_s314.log"), "314")
        self.assertEqual(extract_seed_from_filename("diag_s999_2026.log.gz"), "999")

    def test_parse_log_file_plain_and_gzip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            log_plain = tmp / "OpexAI_seed42_r0.log"
            log_gz = tmp / "OpexAI_seed100_r0.log.gz"

            content_plain = (
                "dbg: [script:0] [0] [I] OPEX 1970-3-1 TASK name=projects\n"
                "dbg: [script:0] [0] [I] OPEX 1970-6-30 V262_SAVE ops=1000 budget=100000 lines=2 abandons=0 abandonCounts=0 tasks=4 full=1\n"
                "dbg: [script:0] [0] [I] OPEX 1970-12-31 V262_SAVE ops=1200 budget=100000 lines=4 abandons=1 abandonCounts=1 tasks=4 full=1\n"
            )
            log_plain.write_text(content_plain, encoding="utf-8")

            content_gz = (
                "dbg: [script:0] [0] [I] OPEX 1971-6-30 V262_SAVE ops=2500 budget=100000 lines=10 abandons=2 abandonCounts=3 tasks=5 full=1\n"
            )
            with gzip.open(log_gz, "wt", encoding="utf-8") as gf:
                gf.write(content_gz)

            events_plain = parse_log_file(log_plain)
            self.assertEqual(len(events_plain), 2)
            self.assertEqual(events_plain[0]["seed"], "42")
            self.assertEqual(events_plain[0]["ops"], 1000)
            self.assertEqual(events_plain[1]["ops"], 1200)

            events_gz = parse_log_file(log_gz)
            self.assertEqual(len(events_gz), 1)
            self.assertEqual(events_gz[0]["seed"], "100")
            self.assertEqual(events_gz[0]["ops"], 2500)

    def test_aggregation_max_and_median(self):
        mock_events = [
            {"seed": "42", "year": 1975, "ops": 1000, "budget": 100000, "lines": 5, "abandons": 1, "abandonCounts": 2, "lah": 8, "margin": 99000},
            {"seed": "42", "year": 1975, "ops": 3000, "budget": 100000, "lines": 15, "abandons": 3, "abandonCounts": 4, "lah": 22, "margin": 97000},
            {"seed": "42", "year": 1975, "ops": 2000, "budget": 100000, "lines": 10, "abandons": 2, "abandonCounts": 3, "lah": 15, "margin": 98000},
            {"seed": "42", "year": 1976, "ops": 4000, "budget": 100000, "lines": 20, "abandons": 4, "abandonCounts": 5, "lah": 29, "margin": 96000},
        ]
        agg = aggregate_by_seed_year(mock_events)
        self.assertIn(("42", 1975), agg)
        row_75 = agg[("42", 1975)]
        self.assertEqual(row_75["ops_max"], 3000)
        self.assertEqual(row_75["ops_med"], 2000)
        self.assertEqual(row_75["l_max"], 15)
        self.assertEqual(row_75["l_med"], 10)
        self.assertEqual(row_75["a_max"], 3)
        self.assertEqual(row_75["a_med"], 2)
        self.assertEqual(row_75["h_max"], 4)
        self.assertEqual(row_75["h_med"], 3)
        self.assertEqual(row_75["margin_min"], 97000)
        self.assertEqual(row_75["margin_med"], 98000)

        self.assertIn(("42", 1976), agg)
        row_76 = agg[("42", 1976)]
        self.assertEqual(row_76["ops_max"], 4000)
        self.assertEqual(row_76["ops_med"], 4000)

    def test_linear_extrapolation_and_budget_year(self):
        # 3 points:
        # year 1970.0 -> lah = 10 -> ops = 1500
        # year 1971.0 -> lah = 20 -> ops = 2500
        # year 1972.0 -> lah = 30 -> ops = 3500
        # Modèle: ops = 100 * lah + 500
        # lah(t) = 10 * t + (-19690)
        # Budget = 100 000 -> x_crit = (100000 - 500) / 100 = 995
        # Année via lah: (995 - (-19690)) / 10 = 2068.5
        mock_events = [
            {"seed": "42", "year": 1970, "month": 1, "ops": 1500, "budget": 100000, "lines": 6, "abandons": 2, "abandonCounts": 2, "lah": 10, "margin": 98500},
            {"seed": "42", "year": 1971, "month": 1, "ops": 2500, "budget": 100000, "lines": 12, "abandons": 4, "abandonCounts": 4, "lah": 20, "margin": 97500},
            {"seed": "42", "year": 1972, "month": 1, "ops": 3500, "budget": 100000, "lines": 18, "abandons": 6, "abandonCounts": 6, "lah": 30, "margin": 96500},
        ]
        extrap = extrapolate_ops_vs_lah(mock_events, budget=100000)
        self.assertAlmostEqual(extrap["alpha"], 100.0, places=3)
        self.assertAlmostEqual(extrap["beta"], 500.0, places=3)
        self.assertAlmostEqual(extrap["r2"], 1.0, places=4)
        self.assertAlmostEqual(extrap["x_crit"], 995.0, places=3)
        self.assertIsNotNone(extrap["year_budget_reached_via_lah"])
        self.assertAlmostEqual(extrap["year_budget_reached_via_lah"], 2068.5, places=1)
        self.assertIsNotNone(extrap["year_budget_reached_direct"])
        self.assertAlmostEqual(extrap["year_budget_reached_direct"], 2068.5, places=1)

    def test_extrapolation_non_positive_slope_does_not_predict_past(self):
        # Cas où ops est constant ou décroissant: budget jamais atteint
        mock_events = [
            {"seed": "42", "year": 1970, "month": 1, "ops": 1500, "budget": 100000, "lines": 5, "abandons": 1, "abandonCounts": 1, "lah": 7, "margin": 98500},
            {"seed": "42", "year": 1971, "month": 1, "ops": 1400, "budget": 100000, "lines": 10, "abandons": 2, "abandonCounts": 2, "lah": 14, "margin": 98600},
        ]
        extrap = extrapolate_ops_vs_lah(mock_events, budget=100000)
        self.assertIsNone(extrap["x_crit"])
        self.assertIsNone(extrap["year_budget_reached_via_lah"])
        self.assertIsNone(extrap["year_budget_reached_direct"])

    def test_format_report_markdown(self):
        mock_events = [
            {"seed": "42", "year": 1970, "month": 6, "ops": 1200, "budget": 100000, "lines": 2, "abandons": 0, "abandonCounts": 0, "tasks": 4, "full": 1, "lah": 2, "margin": 98800},
            {"seed": "42", "year": 1971, "month": 6, "ops": 2400, "budget": 100000, "lines": 5, "abandons": 1, "abandonCounts": 1, "tasks": 5, "full": 1, "lah": 7, "margin": 97600},
        ]
        agg = aggregate_by_seed_year(mock_events)
        extrap = extrapolate_ops_vs_lah(mock_events, budget=100000)
        report = format_report_markdown(agg, extrap, budget=100000)

        self.assertIn("# Analyse du Coût de Save() (V262 T04)", report)
        self.assertIn("100,000 opcodes", report)
        self.assertIn("42", report)
        self.assertIn("1970", report)
        self.assertIn("1971", report)
        self.assertIn("Modèle de coût", report)


if __name__ == "__main__":
    unittest.main()
