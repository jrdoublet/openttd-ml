"""Tests unitaires pour sweeps/analyse_v88_chains.py."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from analyse_v88_chains import (
    date_to_days,
    load_events,
    analyse_seed_events,
    aggregate_metrics,
    parse_fields,
    selftest,
)


class TestAnalyseV88Chains(unittest.TestCase):
    def test_parse_fields(self):
        fields = parse_fields("line=4 year=1972 profit=15000 rev=20000")
        self.assertEqual(fields["line"], "4")
        self.assertEqual(fields["year"], "1972")
        self.assertEqual(fields["profit"], "15000")
        self.assertEqual(fields["rev"], "20000")

    def test_date_to_days(self):
        d1 = date_to_days(1971, 1, 1)
        d2 = date_to_days(1971, 1, 15)
        self.assertEqual(d2 - d1, 14)

    def test_selftest_runs_cleanly(self):
        selftest()

    def test_complete_chain_lifecycle_parsing(self):
        sample_lines = [
            {"seed": 100, "grep": "OPEX 1971-04-01 CHAIN_CHOSEN fact=10 town=5 inCargo=1 goodsCargo=6 src=101 dst=202"},
            {"seed": 100, "grep": "OPEX 1971-04-01 CHAIN_STEP1_SEARCH pending=1"},
            {"seed": 100, "grep": "OPEX 1971-06-15 CHAIN_SEARCH_END step=1 iters=450 len=60 weight=120 outcome=OK"},
            {"seed": 100, "grep": "OPEX 1971-07-01 CHAIN_STEP1 line=10 fact=10"},
            {"seed": 100, "grep": "OPEX 1971-07-01 CHAIN_STEP2_SEARCH pending=1"},
            {"seed": 100, "grep": "OPEX 1971-09-10 CHAIN_SEARCH_END step=2 iters=400 len=50 weight=120 outcome=OK"},
            {"seed": 100, "grep": "OPEX 1971-10-01 CHAIN_STEP2 line=11 town=5"},
            {"seed": 100, "grep": "OPEX 1972-02-15 CHAIN_DELIVERY line=11 year=1972 profit=12000 rev=18000"},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_file = Path(tmpdir) / "test_lifecycle.jsonl"
            with open(tmp_file, "w", encoding="utf-8") as f:
                for line in sample_lines:
                    f.write(json.dumps(line) + "\n")

            events = load_events(tmp_file)
            self.assertIn(100, events)
            analysis = analyse_seed_events(events[100])
            self.assertEqual(analysis["total_chosen"], 1)
            self.assertEqual(analysis["total_completed"], 1)
            self.assertEqual(analysis["total_delivering"], 1)
            self.assertEqual(analysis["total_failed"], 0)

            ch = analysis["chains"][0]
            self.assertEqual(ch["step1_line"], "10")
            self.assertEqual(ch["step2_line"], "11")
            self.assertIsNotNone(ch["delay_step1_search_days"])
            self.assertIsNotNone(ch["delay_step2_search_days"])
            self.assertIsNotNone(ch["delay_total_decision_to_step2_days"])
            self.assertIsNotNone(ch["delay_step2_to_delivery_days"])

            agg = aggregate_metrics({100: analysis})
            self.assertEqual(agg["total_completed"], 1)
            self.assertEqual(agg["pathfinder"]["step1_iters_med"], 450)
            self.assertEqual(agg["pathfinder"]["step2_iters_med"], 400)


if __name__ == "__main__":
    unittest.main()
