"""Contract tests for ROAD1Y PAX 96-127 infra-tile credit (road1y_next3).

At 0 the compare is false and OpexRoadLineEconomics keeps the historical
full corridor charge. N>0 may only shorten infra distance, and only for a
passenger pair whose distance argument is 96..127. 128+ and shorts stay
on the historical formula. This is not a fundScore distance multiplier.
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

CREDIT = (
    "if (ROAD1Y_NEXT3 > 0 && kind == \"pax\" && distance >= 96 && distance <= 127) {\n"
    "    local credited = infraDist - ROAD1Y_NEXT3;\n"
    "    if (credited < 0) credited = 0;\n"
    "    infraDist = credited;\n"
    "  }"
)


class TestRoad1yNext3(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertEqual(info_src.count('name = "road1y_next3"'), 1)
        setting_block = info_src.split('name = "road1y_next3",')[1].split("});")[0]
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 96", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)
        self.assertNotIn("AICONFIG_BOOLEAN", setting_block)

    def test_global_pre_declaration(self):
        self.assertIn("ROAD1Y_NEXT3 <- 0;", source("globals_pre.nut"))

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_next3")'), 2)
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn(
                'GetSetting("road1y_next3")',
                path.read_text(encoding="utf-8"),
                path.name,
            )
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_NEXT3 = AIController.GetSetting("road1y_next3");', load_fn)
        self.assertIn("if (ROAD1Y_NEXT3 < 0 || ROAD1Y_NEXT3 > 96) ROAD1Y_NEXT3 = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_NEXT3 = 0;", load_fn)
        defined = load_fn.index("local road1yRoadOnly =")
        read_at = load_fn.index('GetSetting("road1y_next3")')
        clamp_at = load_fn.index("if (ROAD1Y_NEXT3 < 0 || ROAD1Y_NEXT3 > 96) ROAD1Y_NEXT3 = 0;")
        gate_at = load_fn.index("if (!road1yRoadOnly) ROAD1Y_NEXT3 = 0;")
        self.assertLess(defined, read_at)
        self.assertLess(read_at, clamp_at)
        self.assertLess(clamp_at, gate_at)
        self.assertLess(load_fn.index("if (!road1yRoadOnly) ROAD1Y_MAIL2 = 0;"), read_at)

        loader = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertIn('ROAD1Y_NEXT3 = AIController.GetSetting("road1y_next3");', loader)
        self.assertIn("if (ROAD1Y_NEXT3 < 0 || ROAD1Y_NEXT3 > 96) ROAD1Y_NEXT3 = 0;", loader)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_NEXT3 = 0;", loader)
        self.assertLess(loader.index("local road1yRoadOnly ="), loader.index('GetSetting("road1y_next3")'))
        self.assertLess(
            loader.index("if (!road1yRoadOnly) ROAD1Y_MAIL2 = 0;"),
            loader.index('GetSetting("road1y_next3")'),
        )
        self.assertLess(
            loader.index("if (!road1yRoadOnly) ROAD1Y_NEXT3 = 0;"),
            loader.index('require("bus_districts.nut")'),
        )
        self.assertNotIn("road1y_next3", source("persist.nut"))
        self.assertNotIn("ROAD1Y_NEXT3", source("persist.nut"))

    def test_credit_is_capital_only_on_the_96_127_pax_band(self):
        econ = body("economy.nut", "OpexRoadLineEconomics")
        self.assertEqual(econ.count(CREDIT), 1)
        assign = "local infraDist = (routeDistance != null && routeDistance > 0) ? routeDistance : distance;"
        charge = "local infraCost = infraDist * catalog.costRoadPerTile + 2 * stopCost + catalog.costRoadDepot;"
        self.assertLess(econ.index(assign), econ.index(CREDIT))
        self.assertLess(econ.index(CREDIT), econ.index(charge))
        self.assertNotIn("ROAD1Y_NEXT3", body("projects_selection.nut", "OpexProjectFundProfit"))
        self.assertNotIn("ROAD1Y_NEXT3", source("projects_selection.nut"))
        self.assertNotIn("function(", CREDIT)
        self.assertNotIn(".find(", CREDIT)
        self.assertNotIn("yield", CREDIT)
        for word in ("clone", "base", "parent", "static", "delegate", "resume", "vargc", "vargv"):
            self.assertIsNone(re.search(r"\blocal\s+" + word + r"\b", CREDIT), word)


if __name__ == "__main__":
    unittest.main()
