"""Contract tests for ROAD1Y road freight vehicle cap (road1y_freight).

At 0 (default), ROAD1Y_FREIGHT is inactive and road freight vehicle cap remains
at historical OpexRoadPhysicalVehicleCap(1, 1) = 2.
At N > 0, ROAD1Y_FREIGHT raises the cap for freight lines up to N trucks,
improving freight candidate volume and fundScore to compete with PAX.
Gated to 0 outside road-only mode.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from test_v261_forum_behaviours import body, source

AI = ROOT / "ai" / "OpexAI"


class TestRoad1yFreight(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertEqual(info_src.count('name = "road1y_freight"'), 1)
        setting_block = info_src.split('name = "road1y_freight",')[1].split("});")[0]
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 30", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)
        self.assertNotIn("AICONFIG_BOOLEAN", setting_block)

    def test_global_pre_declaration(self):
        self.assertIn("ROAD1Y_FREIGHT <- 0;", source("globals_pre.nut"))

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_freight")'), 2)
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn(
                'GetSetting("road1y_freight")',
                path.read_text(encoding="utf-8"),
                path.name,
            )
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_FREIGHT = AIController.GetSetting("road1y_freight");', load_fn)
        self.assertIn("if (ROAD1Y_FREIGHT < 0 || ROAD1Y_FREIGHT > 30) ROAD1Y_FREIGHT = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_FREIGHT = 0;", load_fn)
        defined = load_fn.index("local road1yRoadOnly =")
        read_at = load_fn.index('GetSetting("road1y_freight")')
        clamp_at = load_fn.index("if (ROAD1Y_FREIGHT < 0 || ROAD1Y_FREIGHT > 30) ROAD1Y_FREIGHT = 0;")
        gate_at = load_fn.index("if (!road1yRoadOnly) ROAD1Y_FREIGHT = 0;")
        self.assertLess(defined, read_at)
        self.assertLess(read_at, clamp_at)
        self.assertLess(clamp_at, gate_at)
        self.assertLess(load_fn.index("if (!road1yRoadOnly) ROAD1Y_MAIL2 = 0;"), read_at)

        loader = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertIn('ROAD1Y_FREIGHT = AIController.GetSetting("road1y_freight");', loader)
        self.assertIn("if (ROAD1Y_FREIGHT < 0 || ROAD1Y_FREIGHT > 30) ROAD1Y_FREIGHT = 0;", loader)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_FREIGHT = 0;", loader)
        self.assertLess(loader.index("local road1yRoadOnly ="), loader.index('GetSetting("road1y_freight")'))
        self.assertLess(
            loader.index("if (!road1yRoadOnly) ROAD1Y_MAIL2 = 0;"),
            loader.index('GetSetting("road1y_freight")'),
        )
        self.assertLess(
            loader.index("if (!road1yRoadOnly) ROAD1Y_FREIGHT = 0;"),
            loader.index('require("bus_districts.nut")'),
        )
        self.assertNotIn("road1y_freight", source("persist.nut"))
        self.assertNotIn("ROAD1Y_FREIGHT", source("persist.nut"))

    def test_economy_freight_vehicle_cap(self):
        econ = body("economy.nut", "OpexRoadLineEconomics")
        self.assertIn("if (ROAD1Y_FREIGHT > 0 && kind == \"freight\")", econ)
        self.assertIn("if (ROAD1Y_FREIGHT > roadVehicleCap) roadVehicleCap = ROAD1Y_FREIGHT;", econ)
        self.assertNotIn("function(", econ)
        self.assertNotIn(".find(", econ)
        self.assertNotIn("yield", econ)
        for word in ("clone", "base", "parent", "static", "delegate", "resume", "vargc", "vargv"):
            self.assertIsNone(re.search(r"\blocal\s+" + word + r"\b", econ), word)

    def test_candidates_freight_admission_boost(self):
        cand = body("candidates.nut", "OpexBuildRoadCandidates")
        self.assertIn("if (ROAD1Y_FREIGHT > 0)", cand)
        self.assertIn('if (c.kind == "freight")', cand)
        self.assertIn("c.profitAnnual = c.profitAnnual * 2;", cand)
        self.assertIn("c.ratio = c.ratio * 2;", cand)
        self.assertNotIn("function(", cand)
        self.assertNotIn(".find(", cand)
        for word in ("clone", "base", "parent", "static", "delegate", "resume", "vargc", "vargv"):
            self.assertIsNone(re.search(r"\blocal\s+" + word + r"\b", cand), word)


if __name__ == "__main__":
    unittest.main()
