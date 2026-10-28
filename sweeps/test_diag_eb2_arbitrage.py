#!/usr/bin/env python3
"""Tests for sweeps/diag_eb2_arbitrage.py."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_eb2_arbitrage import analyze_arbitrage, to_days


class TestDiagEb2Arbitrage(unittest.TestCase):
    def test_to_days(self):
        self.assertEqual(to_days("1970-1-1"), 1970 * 365 + 30 + 1)
        self.assertGreater(to_days("1971-1-1"), to_days("1970-1-1"))

    def test_analyze_arbitrage_synthetic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            engine_dir = tmppath / "campaign_engine"
            engine_dir.mkdir()

            manifest_path = tmppath / "campaign.manifest.json"
            manifest = {
                "campaign_id": "test_campaign",
                "execution": {
                    "options": {
                        "seeds": [42]
                    }
                }
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            # Synthetic variant log with 1 fallback
            var_log = (
                "[2026-10-28 00:00:00] dbg: [script:4] [0] [I] OPEX 1971-5-1 PROJECT_CHOSEN rank=1 mode=rail src=100 dst=200 cost=50000 profit=30000 roi=600\n"
                "[2026-10-28 00:00:00] dbg: [script:4] [0] [I] OPEX 1971-5-1 EB2_FALLBACK src=100 dst=200 join_end=B\n"
                "[2026-10-28 00:00:00] dbg: [script:4] [0] [I] OPEX 1971-5-10 RAIL_BUILD line=1 src=100 dst=200 cargo=COAL cost=80000\n"
                "[2026-10-28 00:00:00] dbg: [script:4] [0] [I] OPEX 1971-5-10 C39_PROJECTS_CADENCE capital_after=15000\n"
                "[2026-10-28 00:00:00] dbg: [script:4] [0] [I] OPEX 1971-5-10 C78_SLOT reason=cash next_mode=rail finance=60000\n"
            )
            (engine_dir / "eb2_new_station_seed42_r0.log").write_text(var_log, encoding="utf-8")

            # Synthetic reference log with 1 concurrent build 20 days later
            ref_log = (
                "[2026-10-28 00:00:00] dbg: [script:4] [0] [I] OPEX 1971-5-30 RAIL_BUILD line=1 src=300 dst=400 cargo=IRON cost=75000\n"
            )
            (engine_dir / "reference_seed42_r0.log").write_text(ref_log, encoding="utf-8")

            result = analyze_arbitrage(manifest_path)
            s = result["summary"]

            self.assertEqual(s["total_fallbacks_triggered"], 1)
            self.assertEqual(s["total_fallbacks_built"], 1)
            self.assertEqual(s["distinct_fallback_ods"], 1)
            self.assertEqual(s["distinct_fallback_built"], 1)
            self.assertEqual(s["quote_selection_mean"], 50000.0)
            self.assertEqual(s["actual_cost_mean"], 80000.0)
            self.assertEqual(s["overrun_mean"], 30000.0)
            self.assertEqual(s["immediate_cash_block_count"], 1)
            self.assertEqual(s["reference_concurrent_build_count"], 1)
            self.assertEqual(s["reference_concurrent_cost_mean"], 75000.0)

    def test_analyze_arbitrage_unbuilt_and_age1(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            engine_dir = tmppath / "campaign_engine"
            engine_dir.mkdir()

            manifest_path = tmppath / "campaign.manifest.json"
            manifest = {
                "campaign_id": "test_unbuilt",
                "execution": {
                    "options": {
                        "seeds": [100]
                    }
                }
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            # Fallback that hits A* cap
            var_log = (
                "[2026-10-28 00:00:00] dbg: [script:4] [0] [I] OPEX 1971-5-1 PROJECT_CHOSEN rank=0 mode=rail src=10 dst=20 cost=50000 profit=30000 roi=600\n"
                "[2026-10-28 00:00:00] dbg: [script:4] [0] [I] OPEX 1971-5-1 EB2_FALLBACK src=10 dst=20 join_end=B\n"
                "[2026-10-28 00:00:00] dbg: [script:4] [0] [I] OPEX 1971-5-20 C56_TASK RAIL_SEARCH_END name=primary outcome=ABND result=cap iters=5000 len=0 src=10 dst=20\n"
                "[2026-10-28 00:00:00] dbg: [script:4] [0] [I] OPEX 1971-5-20 ABANDON_PAIR key=freight|1|10|20 count=1 cooldown=365\n"
                "[2026-10-28 00:00:00] dbg: [script:4] [0] [I] OPEX 1971-6-1 RAIL_BUILD line=1 src=30 dst=40 cargo=PASS cost=60000\n"
                "[2026-10-28 00:00:00] dbg: [script:4] [0] [I] OPEX 1972-1-20 LINE_REVENUE line=1 mode=rail age=1 real_rev=20000 real_prof=15000\n"
            )
            (engine_dir / "eb2_new_station_seed100_r0.log").write_text(var_log, encoding="utf-8")

            result = analyze_arbitrage(manifest_path)
            s = result["summary"]

            self.assertEqual(s["total_fallbacks_triggered"], 1)
            self.assertEqual(s["distinct_fallback_ods"], 1)
            self.assertEqual(s["distinct_fallback_built"], 0)
            self.assertEqual(s["distinct_fallback_unbuilt"], 1)
            self.assertIn("astar_abandon_cap", s["unbuilt_breakdown"])
            self.assertEqual(s["performance_age1"]["non_fallback"]["count"], 1)
            self.assertEqual(s["performance_age1"]["non_fallback"]["profit_mean"], 15000.0)



if __name__ == "__main__":
    unittest.main()
