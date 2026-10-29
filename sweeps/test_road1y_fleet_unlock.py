"""Contract tests for ROAD1Y-E fleet unlock setting (road1y_fleet_unlock).

Verifies bitmask behavior:
- default 0 is strictly identical to previous behavior;
- bit 1: joint stop cash reserve lowered to 5 000 £;
- bit 2: pax bus reinforcement cash reserve lowered to 10 000 £;
- bit 4: pax refleet driven by waiting & fleet cap tracks real joint stops;
- bit 8: fleet cap per stop raised to 6 when waiting > 100 at both ends;
- Squirrel syntax constraints and identifier safety.
"""
from pathlib import Path
import re
import unittest

from test_v261_forum_behaviours import body, source

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


class TestRoad1yFleetUnlock(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertIn('name = "road1y_fleet_unlock"', info_src)
        setting_block = info_src.split('name = "road1y_fleet_unlock",')[1].split('});')[0]
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 15", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)

    def test_global_pre_declaration(self):
        pre_src = source("globals_pre.nut")
        self.assertIn("ROAD1Y_FLEET_UNLOCK <- 0;", pre_src)

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_fleet_unlock")'), 1)
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_FLEET_UNLOCK = AIController.GetSetting("road1y_fleet_unlock");', load_fn)
        self.assertIn("if (ROAD1Y_FLEET_UNLOCK < 0 || ROAD1Y_FLEET_UNLOCK > 15) ROAD1Y_FLEET_UNLOCK = 0;", load_fn)

    def test_bit1_joint_stop_reserve_bus_districts(self):
        code = body("bus_districts.nut", "OpexRoad1yBuildExtraStop")
        self.assertIn("local cashReserve = (ROAD1Y_FLEET_UNLOCK & 1) != 0 ? 5000 : 50000;", code)
        self.assertIn("< cost + cashReserve", code)

    def test_bit2_bus_pax_reserves_overrides(self):
        code = body("bus_districts_overrides.nut", "OpexRoad1yRefleetSaved")
        # PAX wait fleet reserve
        self.assertIn("local waitFleetReserve = (ROAD1Y_FLEET_UNLOCK & 2) != 0 ? 10000 : 50000;", code)
        self.assertIn("money >= waitFleetReserve + waitFleetPrice", code)
        self.assertIn("(money - waitFleetReserve) / waitFleetPrice", code)
        # PAX balance tile reserve
        self.assertIn("local paxBalanceReserve = (ROAD1Y_FLEET_UNLOCK & 2) != 0 ? 10000 : 50000;", code)
        self.assertIn("(money - paxBalanceReserve) / busPrice", code)
        self.assertIn("(money - paxBalanceReserve) / busUnitPrice", code)
        # Freight reserve must remain unchanged at 50000
        self.assertIn('("kind" in line) && line.kind == "freight"', code)
        self.assertIn("money >= 50000", code)
        self.assertIn("(money - 50000) / unitPrice", code)

    def test_bit4_pax_refleet_and_joint_stop_tracking(self):
        code = body("bus_districts_overrides.nut", "OpexRoad1yRefleetSaved")
        self.assertIn("local paxRefleet = ROAD1Y_PAX_REFLEET || ((ROAD1Y_FLEET_UNLOCK & 4) != 0);", code)
        self.assertIn('line.kind == "pax" && paxRefleet', code)
        self.assertIn("(isPax && paxRefleet)", code)
        self.assertIn("? (road1yStopsA + road1yStopsB)", code)
        self.assertIn(": (road1yStopsB < road1yStopsA ? road1yStopsB : road1yStopsA)", code)

    def test_bit8_raised_fleet_cap_on_both_ends_waiting(self):
        code = body("bus_districts_overrides.nut", "OpexRoad1yRefleetSaved")
        self.assertIn("local fleetPerStop = ROAD1Y_FLEET;", code)
        self.assertIn("if (isPax && ((ROAD1Y_FLEET_UNLOCK & 8) != 0) && waitingA > 100 && waitingB > 100)", code)
        self.assertIn("if (fleetPerStop < 6) fleetPerStop = 6;", code)
        self.assertIn("local road1yCap = fleetPerStop * road1yStops;", code)

    def test_squirrel_hazards_and_reserved_words(self):
        for filename in ("bus_districts.nut", "bus_districts_overrides.nut"):
            code = source(filename)
            for word in ("clone", "base", "par", "parent", "static"):
                self.assertNotRegex(code, r"\blocal\s+" + word + r"\b", f"Found local {word} in {filename}")
            self.assertNotIn("function(", code, f"Found anonymous function in {filename}")
            self.assertNotIn(".find(", code, f"Found array .find in {filename}")
            # Ensure no yield inside try
            try_blocks = re.findall(r"try\s*\{[^}]*\}", code, re.DOTALL)
            for tb in try_blocks:
                self.assertNotIn("yield", tb, f"Found yield in try block in {filename}")


if __name__ == "__main__":
    unittest.main()
