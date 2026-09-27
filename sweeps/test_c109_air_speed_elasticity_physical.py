import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")


class C109AirSpeedElasticityPhysicalTests(unittest.TestCase):
    def test_setting_is_off_by_default_and_loaded(self):
        self.assertIn("C109_AIR_SPEED_ELASTICITY_PHYSICAL <- false;", GLOBALS)
        start = INFO.index('name = "c109_air_speed_elasticity_physical"')
        snippet = INFO[start:start + 700]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)
        self.assertIn('AIController.GetSetting("c109_air_speed_elasticity_physical")', SETTINGS)

    def test_global_economics_use_c100_1_physical_timing(self):
        trip = re.search(r"function OpexAirTripModel\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(trip)
        self.assertIn("C109_AIR_SPEED_ELASTICITY_PHYSICAL", trip.group(1))

    def test_elasticity_rule_is_relative_and_has_no_cash_or_capital_threshold(self):
        match = re.search(r"function OpexC109OneStepSpeedElasticityChoice\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("profitGainPermille", body)
        self.assertIn("speedGainPermille", body)
        self.assertIn("relativeElasticityPermille", body)
        self.assertNotIn("AICompany.GetBankBalance", body)
        self.assertNotIn("economics.capital", body)
        self.assertNotIn("plane.price", body)

    def test_active_helper_uses_e50_and_returns_physical_economics(self):
        match = re.search(r"function OpexC109ChooseRoutePlane\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("OpexC109OneStepSpeedElasticityChoice", body)
        self.assertIn("opcodePadding, 500", body)
        self.assertIn("economics = choice.economics", body)
        self.assertNotIn("forceC100RankReplay", body)

    def test_active_branch_is_isolated(self):
        full = AIR[AIR.index("function OpexAirChooseRoutePlaneFull("):]
        self.assertIn("if (C109_AIR_SPEED_ELASTICITY_PHYSICAL && C72_PLANE_CHOICE == 0", full)
        self.assertIn("!C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS", full)
        self.assertIn("!C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE", full)
        self.assertIn("!C109_AIR_SPEED_ELASTICITY_PHYSICAL", full)


if __name__ == "__main__":
    unittest.main()
