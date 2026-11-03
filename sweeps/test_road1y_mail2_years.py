"""Contract tests for ROAD1Y child MAIL cash reserve duration (road1y_mail2_years).

At 0 the window condition is trivially true (ROAD1Y_MAIL2_YEARS == 0),
preserving the exact behavior of road1y_mail2 across the entire game.
When N > 0, child MAIL cash reserve lowering only applies while
AIDate.GetYear(AIDate.GetCurrentDate()) < OPEX_START_YEAR + N.
After that window, the historical cash reserve (25000, or the
fleet-unlock / pax-refleet floors) returns.
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

HISTORICAL_RESERVE = (
    "local cashReserve = (ROAD1Y_FLEET_UNLOCK & 2) != 0 ? 10000 "
    ": (ROAD1Y_PAX_REFLEET ? 15000 : 25000);"
)
MAIL2_LOWER = (
    "if (ROAD1Y_MAIL2 > 0 && (ROAD1Y_MAIL2_YEARS == 0 || AIDate.GetYear(AIDate.GetCurrentDate()) < OPEX_START_YEAR + ROAD1Y_MAIL2_YEARS) && cashReserve > ROAD1Y_MAIL2 * 1000) "
    "cashReserve = ROAD1Y_MAIL2 * 1000;"
)


class TestRoad1yMail2Years(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertEqual(info_src.count('name = "road1y_mail2_years"'), 1)
        setting_block = info_src.split('name = "road1y_mail2_years",')[1].split("});")[0]
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 20", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)
        self.assertNotIn("AICONFIG_BOOLEAN", setting_block)

    def test_global_pre_declaration(self):
        self.assertIn("ROAD1Y_MAIL2_YEARS <- 0;", source("globals_pre.nut"))
        self.assertIn("OPEX_START_YEAR <- 1970;", source("globals_pre.nut"))

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_mail2_years")'), 2)
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn(
                'GetSetting("road1y_mail2_years")',
                path.read_text(encoding="utf-8"),
                path.name,
            )
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_MAIL2_YEARS = AIController.GetSetting("road1y_mail2_years");', load_fn)
        self.assertIn("if (ROAD1Y_MAIL2_YEARS < 0 || ROAD1Y_MAIL2_YEARS > 20) ROAD1Y_MAIL2_YEARS = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_MAIL2_YEARS = 0;", load_fn)
        defined = load_fn.index("local road1yRoadOnly =")
        read_at = load_fn.index('GetSetting("road1y_mail2_years")')
        clamp_at = load_fn.index("if (ROAD1Y_MAIL2_YEARS < 0 || ROAD1Y_MAIL2_YEARS > 20) ROAD1Y_MAIL2_YEARS = 0;")
        gate_at = load_fn.index("if (!road1yRoadOnly) ROAD1Y_MAIL2_YEARS = 0;")
        self.assertLess(defined, read_at)
        self.assertLess(read_at, clamp_at)
        self.assertLess(clamp_at, gate_at)
        self.assertLess(load_fn.index("if (!road1yRoadOnly) ROAD1Y_MAIL2 = 0;"), read_at)

        loader = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertIn('ROAD1Y_MAIL2_YEARS = AIController.GetSetting("road1y_mail2_years");', loader)
        self.assertIn("if (ROAD1Y_MAIL2_YEARS < 0 || ROAD1Y_MAIL2_YEARS > 20) ROAD1Y_MAIL2_YEARS = 0;", loader)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_MAIL2_YEARS = 0;", loader)
        self.assertLess(loader.index("local road1yRoadOnly ="), loader.index('GetSetting("road1y_mail2_years")'))
        self.assertLess(
            loader.index("if (!road1yRoadOnly) ROAD1Y_MAIL2 = 0;"),
            loader.index('GetSetting("road1y_mail2_years")'),
        )
        self.assertLess(
            loader.index("if (!road1yRoadOnly) ROAD1Y_MAIL2_YEARS = 0;"),
            loader.index('require("bus_districts.nut")'),
        )
        self.assertNotIn("road1y_mail2_years", source("persist.nut"))
        self.assertNotIn("ROAD1Y_MAIL2_YEARS", source("persist.nut"))

    def test_window_condition_in_bus_districts(self):
        districts = source("bus_districts.nut")
        pair = HISTORICAL_RESERVE + "\n  " + MAIL2_LOWER
        self.assertEqual(districts.count(HISTORICAL_RESERVE), 2)
        self.assertEqual(districts.count(MAIL2_LOWER), 2)
        self.assertEqual(districts.count(pair), 2)
        refleet = body("bus_districts.nut", "OpexRoad1yRefleetMailLine")
        step = body("bus_districts.nut", "OpexRoad1yMailStep")
        for code in (refleet, step):
            self.assertLess(code.index(HISTORICAL_RESERVE), code.index(MAIL2_LOWER))
        self.assertLess(
            refleet.index(MAIL2_LOWER),
            refleet.index("if (unitPrice <= 0 || money < cashReserve + unitPrice) return;"),
        )
        self.assertLess(
            step.index(MAIL2_LOWER),
            step.index("local needCash = cashReserve + 2 * catalog.costRoadTruckStop + engine.price;"),
        )
        self.assertNotIn("ROAD1Y_MAIL2_YEARS", body("bus_districts.nut", "OpexRoad1yBuildMailChild"))
        for code in (refleet, step):
            self.assertNotIn("function(", code)
            self.assertNotIn(".find(", code)
            self.assertNotIn("yield", code)
            for word in ("clone", "base", "parent", "static", "delegate", "resume", "vargc", "vargv"):
                self.assertIsNone(re.search(r"\blocal\s+" + word + r"\b", code), word)


if __name__ == "__main__":
    unittest.main()
