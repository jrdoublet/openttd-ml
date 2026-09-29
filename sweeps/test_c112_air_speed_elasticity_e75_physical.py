import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")


class C112AirSpeedElasticityE75PhysicalTests(unittest.TestCase):
    def test_setting_is_off_by_default_and_loaded(self):
        self.assertIn("C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL <- false;", GLOBALS)
        start = INFO.index('name = "c112_air_speed_elasticity_e75_physical"')
        snippet = INFO[start:start + 760]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)
        self.assertIn(
            'C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL = AIController.GetSetting("c112_air_speed_elasticity_e75_physical") != 0;',
            SETTINGS,
        )

    def test_c112_uses_e75_relative_speed_profit_elasticity(self):
        match = re.search(r"function OpexC112ChooseRoutePlane\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("OpexC109OneStepSpeedElasticityChoice", body)
        self.assertIn("opcodePadding, 750);", body)
        self.assertNotIn("AICompany.GetBankBalance", body)
        self.assertNotIn("EngineID", body)

    def test_c112_enables_physical_route_economics(self):
        trip = re.search(r"function OpexAirTripModel\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(trip)
        self.assertIn("C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL", trip.group(1))

    def test_c112_has_isolated_active_branch(self):
        full = AIR[AIR.index("function OpexAirChooseRoutePlaneFull("):]
        self.assertIn("if (C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL && C72_PLANE_CHOICE == 0", full)
        self.assertIn("return OpexC112ChooseRoutePlane", full)
        self.assertIn("!C111_AIR_C100_DECISION_SHADOW", full)


if __name__ == "__main__":
    unittest.main()
