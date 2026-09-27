import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")


class C106AirMarginalPhysicalEngineChoiceTests(unittest.TestCase):
    def test_setting_is_off_by_default_and_loaded(self):
        self.assertIn("C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE <- false;", GLOBALS)
        start = INFO.index('name = "c106_air_marginal_physical_engine_choice"')
        snippet = INFO[start:start + 700]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)
        self.assertIn('AIController.GetSetting("c106_air_marginal_physical_engine_choice")', SETTINGS)

    def test_marginal_rule_is_relative_and_physical(self):
        match = re.search(r"function OpexC106MarginalPhysicalChoice\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("0, false, false, true, false", body)
        self.assertIn("marginalRoi * 1000.0 >= runner.economics.roi * relativeRoiPermille", body)
        self.assertNotIn("AICompany.GetBankBalance", body)
        self.assertNotIn("plane.id == 216", body)
        self.assertNotIn("plane.id == 217", body)

    def test_active_helper_returns_legacy_economics(self):
        match = re.search(r"function OpexC106ChooseRoutePlane\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("OpexC106MarginalPhysicalChoice", body)
        self.assertIn("legacy = OpexAirEconomics", body)
        self.assertIn("return { plane = choice.plane, economics = legacy };", body)
        self.assertNotIn("AICompany.GetBankBalance", body)

    def test_branch_is_isolated_from_other_engine_experiments(self):
        full = AIR[AIR.index("function OpexAirChooseRoutePlaneFull("):]
        self.assertIn("if (C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE && C72_PLANE_CHOICE == 0", full)
        self.assertIn("!C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS", full)
        self.assertIn("!C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE", full)


if __name__ == "__main__":
    unittest.main()
