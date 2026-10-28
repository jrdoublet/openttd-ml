#!/usr/bin/env python3
"""sweeps/test_eb2_new_station_fallback.py — Tests de contrat pour eb2_new_station_fallback."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


class TestEb2NewStationFallback(unittest.TestCase):
    def test_global_declaration(self):
        globals_pre = (AI / "globals_pre.nut").read_text(encoding="utf-8")
        self.assertIn("EB2_NEW_STATION_FALLBACK <- 0;", globals_pre)

    def test_setting_loaded_once(self):
        settings = (AI / "settings.nut").read_text(encoding="utf-8")
        self.assertIn('AIController.GetSetting("eb2_new_station_fallback")', settings)
        self.assertIn("EB2_NEW_STATION_FALLBACK =", settings)

    def test_info_declaration(self):
        info = (AI / "info.nut").read_text(encoding="utf-8")
        self.assertIn('name = "eb2_new_station_fallback"', info)
        self.assertIn("easy_value = 0", info)
        self.assertIn("custom_value = 0", info)

    def test_builder_rail_fallback_guard(self):
        builder = (AI / "builder_rail.nut").read_text(encoding="utf-8")
        self.assertIn("strictOriginReuseJoin", builder)
        self.assertIn("EB2_NEW_STATION_FALLBACK == 0", builder)
        self.assertIn('OpexDecide("EB2_FALLBACK"', builder)

    def test_probe_stats_propagation(self):
        builder = (AI / "builder_rail.nut").read_text(encoding="utf-8")
        task = (AI / "task_rail.nut").read_text(encoding="utf-8")
        self.assertIn('if ("statsA" in plan) failRes.statsA <- plan.statsA;', builder)
        self.assertIn('if ("statsB" in plan) failRes.statsB <- plan.statsB;', builder)
        self.assertIn('railPlan != null && ("statsA" in railPlan)', task)
        self.assertIn('railPlan != null && ("statsB" in railPlan)', task)


if __name__ == "__main__":
    unittest.main()
