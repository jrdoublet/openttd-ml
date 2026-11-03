"""Contract tests for ROAD1Y PAX fundScore distance bonus (road1y_next2).

Verifies:
- setting declared default 0 at all four difficulties (0..192);
- ROAD1Y_NEXT2 global declared default 0 in globals_pre.nut;
- ROAD1Y_NEXT2 read in OpexLoadSettings and OpexLoadBusDistrictSettings,
  clamped to 0..192 and forced to 0 outside road-only mode;
- the bonus multiplies OpexProjectFundProfit for road PAX only when
  ROAD1Y_NEXT2 > 0 and distance > N, after calibration and before fundScore;
- profitAnnual, freight generation, next floor, weak and gap stay untouched;
- Squirrel hazards: no try/yield, no anonymous functions, no reserved locals.
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


class TestRoad1yNext2(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertEqual(info_src.count('name = "road1y_next2"'), 1)
        setting_block = info_src.split('name = "road1y_next2",')[1].split("});")[0]
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 192", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)

    def test_global_pre_declaration(self):
        self.assertIn("ROAD1Y_NEXT2 <- 0;", source("globals_pre.nut"))

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_next2")'), 2)
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn('GetSetting("road1y_next2")', path.read_text(encoding="utf-8"), path.name)
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_NEXT2 = AIController.GetSetting("road1y_next2");', load_fn)
        self.assertIn("if (ROAD1Y_NEXT2 < 0 || ROAD1Y_NEXT2 > 192) ROAD1Y_NEXT2 = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_NEXT2 = 0;", load_fn)
        defined = load_fn.index("local road1yRoadOnly =")
        self.assertLess(defined, load_fn.index('GetSetting("road1y_next2")'))

        loader = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertIn('ROAD1Y_NEXT2 = AIController.GetSetting("road1y_next2");', loader)
        self.assertIn("if (ROAD1Y_NEXT2 < 0 || ROAD1Y_NEXT2 > 192) ROAD1Y_NEXT2 = 0;", loader)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_NEXT2 = 0;", loader)
        self.assertLess(loader.index("local road1yRoadOnly ="), loader.index('GetSetting("road1y_next2")'))
        self.assertLess(
            loader.index("if (!road1yRoadOnly) ROAD1Y_NEXT2 = 0;"),
            loader.index('require("bus_districts_overrides.nut")'),
        )
        self.assertNotIn("road1y_next2", source("persist.nut"))
        self.assertNotIn("ROAD1Y_NEXT2", source("persist.nut"))

    def test_fund_profit_bonus_not_a_floor(self):
        code = body("projects_selection.nut", "OpexProjectFundProfit")
        bonus = "calibrated = calibrated * project.distance / ROAD1Y_NEXT2;"
        guard = "if (ROAD1Y_NEXT2 > 0 && project != null && project.mode == \"road\""
        self.assertEqual(code.count(bonus), 1)
        self.assertEqual(code.count(guard), 1)
        self.assertLess(code.index("OpexCalibratedProfit(project)"), code.index(guard))
        self.assertLess(code.index(guard), code.index(bonus))
        self.assertLess(code.index("project.distance > ROAD1Y_NEXT2"), code.index(bonus))
        self.assertIn('project.kind == "pax"', code)
        floor = "if (ROAD1Y_NEXT > 0 && distance < ROAD1Y_NEXT) continue;"
        self.assertEqual(body("bus_districts_overrides.nut", "OpexRoad100SoloPaxCandidates").count(floor), 1)
        self.assertNotIn("ROAD1Y_NEXT2", source("bus_districts_overrides.nut"))
        self.assertNotIn("ROAD1Y_NEXT2", source("candidates.nut"))
        self.assertNotIn("ROAD1Y_NEXT2", source("po01c_regen.nut"))
        self.assertNotIn("ROAD1Y_NEXT2", source("builder_road.nut"))

    def test_squirrel_hazards_and_reserved_words(self):
        code = body("projects_selection.nut", "OpexProjectFundProfit")
        self.assertNotIn("yield", code)
        self.assertNotIn("function(", code)
        self.assertNotIn(".find(", code)
        reserved = ("clone", "base", "par", "parent", "static", "delegate", "resume", "vargc", "vargv")
        for word in reserved:
            self.assertIsNone(
                re.search(r"\blocal\s+" + word + r"\b", code),
                f"Reserved word '{word}' used as local variable",
            )


if __name__ == "__main__":
    unittest.main()
