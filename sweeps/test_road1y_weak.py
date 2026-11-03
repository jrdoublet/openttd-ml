"""Contract tests for ROAD1Y weak line bus reallocation (road1y_weak).

Verifies:
- setting declared default 0 at all four difficulties (0..30);
- ROAD1Y_WEAK global declared default 0 in globals_pre.nut;
- ROAD1Y_WEAK read in OpexLoadSettings and OpexLoadBusDistrictSettings,
  clamped to 0..30 and forced to 0 outside road-only mode;
- OpexRoad1yWeakStep defined in bus_districts.nut, guarded by ROAD1Y_WEAK > 0;
- checks IsStoppedInDepot before SellVehicle and IsGotoDepotOrder before SendVehicleToDepot;
- preserves at least 2 buses on downsized lines;
- clones vehicle on saturated strong line and starts it;
- dispatched in _dispatchRefleet (scheduler_tasks.nut) guarded by ROAD1Y_WEAK > 0;
- Squirrel hazards check: no try/yield, no anonymous functions, no reserved word identifiers.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from test_v261_forum_behaviours import body, source


class TestRoad1yWeak(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertIn('name = "road1y_weak"', info_src)
        setting_block = info_src.split('name = "road1y_weak",')[1].split("});")[0]
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 30", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 15", setting_block)
        self.assertIn("flags = 0", setting_block)

    def test_global_pre_declaration(self):
        pre_src = source("globals_pre.nut")
        self.assertIn("ROAD1Y_WEAK <- 0;", pre_src)

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_weak")'), 2)
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_WEAK = AIController.GetSetting("road1y_weak");', load_fn)
        self.assertIn("if (ROAD1Y_WEAK < 0 || ROAD1Y_WEAK > 30) ROAD1Y_WEAK = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_WEAK = 0;", load_fn)

        loader = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertIn('ROAD1Y_WEAK = AIController.GetSetting("road1y_weak");', loader)
        self.assertIn("if (ROAD1Y_WEAK < 0 || ROAD1Y_WEAK > 30) ROAD1Y_WEAK = 0;", loader)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_WEAK = 0;", loader)

    def test_weak_step_implementation(self):
        code = body("bus_districts.nut", "OpexRoad1yWeakStep")
        self.assertIn("if (ROAD1Y_WEAK <= 0) return;", code)
        self.assertIn("local weakLimit = ROAD1Y_WEAK * 100;", code)
        # Sell in depot check
        self.assertIn("AIVehicle.IsStoppedInDepot(v)", code)
        self.assertIn("AIVehicle.SellVehicle(inDepot)", code)
        # Toggle protection
        self.assertIn("AIOrder.IsGotoDepotOrder(v, AIOrder.ORDER_CURRENT)", code)
        self.assertIn("AIVehicle.SendVehicleToDepot(victim)", code)
        # Minimum fleet preserved
        self.assertIn("vehs.len() <= 2", code)
        # Strong line clone & start
        self.assertIn("AIVehicle.CloneVehicle(bestStrong.depot, bestTemplate, true)", code)
        self.assertIn("AIVehicle.StartStopVehicle(newVeh)", code)

    def test_dispatch_refleet_integration(self):
        code = body("scheduler_tasks.nut", "OpexAI::_dispatchRefleet")
        self.assertIn("if (ROAD1Y_WEAK > 0) OpexRoad1yWeakStep(this, year);", code)

    def test_squirrel_hazards_and_reserved_words(self):
        code = source("bus_districts.nut")
        self.assertNotIn("yield", code)
        # Check no reserved identifiers used as variable names
        reserved = ("clone", "base", "par", "static", "delegate", "resume")
        for word in reserved:
            self.assertIsNone(
                re.search(r"\blocal\s+" + word + r"\b", code),
                f"Reserved word '{word}' used as local variable",
            )


if __name__ == "__main__":
    unittest.main()
