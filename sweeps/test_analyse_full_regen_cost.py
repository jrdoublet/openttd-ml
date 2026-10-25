#!/usr/bin/env python3
"""test_analyse_full_regen_cost.py

Test unitaire minimal pour sweeps/analyse_full_regen_cost.py.
Valide le parsing des lignes réelles émises par ai/OpexAI/task_report.nut:1450 (OpexC76Log, probes.nut:2412)
et l'agrégation statistique par motif et par année.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sweeps.analyse_full_regen_cost import (
    aggregate_events,
    parse_log_files,
    parse_log_line,
)


class TestAnalyseFullRegenCost(unittest.TestCase):
    def test_phase_regen_after_other_fields(self) -> None:
        line = ("[2026-10-12 14:26:20] dbg: [script:4] [0] [I] "
                "OPEX 1972-1-3 C76_REGEN kind=full reason=reactive "
                "year=1972 ops=180000 phase=regen days=25")
        self.assertEqual(parse_log_line(line), {
            "kind": "full", "reason": "reactive", "ops": 180000,
            "days": 25, "modes": None, "year": 1972,
        })

    def test_reordered_log_is_included_in_total_300k(self) -> None:
        logs = (
            "[0] [I] OPEX 1972-1-2 C76_REGEN phase=regen kind=full "
            "reason=reactive year=1972 days=20 ops=120000\n"
            "[0] [I] OPEX 1972-1-3 C76_REGEN kind=full reason=reactive "
            "year=1972 ops=180000 phase=regen days=25\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reference_seed42_r0.log"
            path.write_text(logs, encoding="utf-8")
            events = parse_log_files([path], kind_filter="full")
        summary = aggregate_events(events)
        self.assertEqual(summary["total_events"], 2)
        self.assertEqual(summary["total_ops"], 300000)
        self.assertEqual(summary["by_reason"]["reactive"]["total_ops"], 300000)

    def test_publish_phase_is_still_rejected_with_reordered_kvs(self) -> None:
        line = ("[0] [I] OPEX 1972-1-4 C76_REGEN kind=full "
                "reason=reactive ops=999999 year=1972 phase=publish days=12")
        self.assertIsNone(parse_log_line(line))

    def test_parse_log_line_formats(self) -> None:
        # Ligne 1 : Reconstruction périodique annuelle C78 découpée terminée à l'application
        line1 = "[2026-10-12 14:26:20] dbg: [script:4] [0] [I] OPEX 1951-1-3 C76_REGEN phase=regen kind=full reason=periodic year=1951 days=28 days_since_prev=0 ops=254120 towns_n=40"
        rec1 = parse_log_line(line1)
        self.assertIsNotNone(rec1)
        assert rec1 is not None
        self.assertEqual(rec1["kind"], "full")
        self.assertEqual(rec1["reason"], "periodic")
        self.assertEqual(rec1["ops"], 254120)
        self.assertEqual(rec1["days"], 28)
        self.assertEqual(rec1["year"], 1951)

        # Ligne 2 : Reconstruction post-build sous staged_bootstrap (task_projects.nut:2076)
        line2 = "[2026-10-12 14:26:20] dbg: [script:4] [0] [I] OPEX 1950-1-3 C76_REGEN phase=regen kind=full reason=staged year=1950 days=0 days_since_prev=0 ops=112000 towns_n=40"
        rec2 = parse_log_line(line2)
        self.assertIsNotNone(rec2)
        assert rec2 is not None
        self.assertEqual(rec2["reason"], "staged")
        self.assertEqual(rec2["ops"], 112000)
        self.assertEqual(rec2["year"], 1950)

        # Ligne 3 : Changement de couche non filtrable par C80 (ex: towns ou lines)
        line3 = "[2026-10-12 14:26:20] dbg: [script:4] [0] [I] OPEX 1952-1-3 C76_REGEN phase=regen kind=full reason=layers year=1952 days=22 days_since_prev=0 ops=245000 towns_n=40"
        rec3 = parse_log_line(line3)
        self.assertIsNotNone(rec3)
        assert rec3 is not None
        self.assertEqual(rec3["reason"], "layers")
        self.assertEqual(rec3["ops"], 245000)
        self.assertEqual(rec3["year"], 1952)

        # Ligne 4 : Régénération par mode (kind=mode avec champ modes=...) qui doit être filtrée par kind=full
        line4 = "[2026-10-12 14:26:20] dbg: [script:4] [0] [I] OPEX 1953-1-3 C76_REGEN phase=regen kind=mode reason=layers year=1953 days=2 days_since_prev=0 ops=45000 modes=rail,road towns_n=40"
        rec4 = parse_log_line(line4)
        self.assertIsNotNone(rec4)
        assert rec4 is not None
        self.assertEqual(rec4["kind"], "mode")
        self.assertEqual(rec4["modes"], "rail,road")

    def test_aggregation_and_filtering(self) -> None:
        synthetic_logs = (
            "[2026-10-12 14:26:20] dbg: [script:4] [0] [I] OPEX 1950-1-3 C76_REGEN phase=regen kind=full reason=staged year=1950 days=0 days_since_prev=0 ops=100000 towns_n=40\n"
            "[2026-10-12 14:26:20] dbg: [script:4] [0] [I] OPEX 1951-1-3 C76_REGEN phase=regen kind=full reason=periodic year=1951 days=20 days_since_prev=0 ops=200000 towns_n=40\n"
            "[2026-10-12 14:26:20] dbg: [script:4] [0] [I] OPEX 1952-1-3 C76_REGEN phase=regen kind=full reason=periodic year=1952 days=30 days_since_prev=0 ops=300000 towns_n=40\n"
            "[2026-10-12 14:26:20] dbg: [script:4] [0] [I] OPEX 1951-1-3 C76_REGEN phase=regen kind=mode reason=layers year=1951 days=5 days_since_prev=0 ops=50000 modes=rail towns_n=40\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
            f.write(synthetic_logs)
            temp_path = Path(f.name)

        try:
            # Filtre 'full' : la ligne kind=mode doit être ignorée
            events = parse_log_files([temp_path], kind_filter="full")
            self.assertEqual(len(events), 3)

            summary = aggregate_events(events)
            self.assertEqual(summary["total_events"], 3)
            self.assertEqual(summary["total_ops"], 600000)

            # Vérification par motif
            by_reason = summary["by_reason"]
            self.assertIn("periodic", by_reason)
            self.assertIn("staged", by_reason)
            self.assertEqual(by_reason["periodic"]["count"], 2)
            self.assertEqual(by_reason["periodic"]["total_ops"], 500000)
            self.assertEqual(by_reason["periodic"]["median_ops"], 250000.0)
            self.assertAlmostEqual(by_reason["periodic"]["share_pct"], 83.33, places=1)

            self.assertEqual(by_reason["staged"]["count"], 1)
            self.assertEqual(by_reason["staged"]["total_ops"], 100000)
            self.assertAlmostEqual(by_reason["staged"]["share_pct"], 16.67, places=1)

            # Vérification chronologique
            by_year = summary["by_year"]
            self.assertIn("1950", by_year)
            self.assertIn("1951", by_year)
            self.assertIn("1952", by_year)
            self.assertEqual(by_year["1950"]["reasons"]["staged"]["total_ops"], 100000)
            self.assertEqual(by_year["1951"]["reasons"]["periodic"]["total_ops"], 200000)
            self.assertEqual(by_year["1952"]["reasons"]["periodic"]["total_ops"], 300000)
        finally:
            if temp_path.exists():
                temp_path.unlink()


if __name__ == "__main__":
    unittest.main()
