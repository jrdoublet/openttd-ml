import re
import unittest
from pathlib import Path
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air


ROOT = Path(__file__).resolve().parents[1]
AIR = read_builder_air()
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")


class C108AirOneStepPhysicalEconomicsTests(unittest.TestCase):
    def test_setting_is_off_by_default_and_loaded(self):
        self.assertIn("C108_AIR_ONESTEP_PHYSICAL_ECONOMICS <- false;", GLOBALS)
        start = INFO.index('name = "c108_air_onestep_physical_economics"')
        snippet = INFO[start:start + 760]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)
        self.assertIn('AIController.GetSetting("c108_air_onestep_physical_economics")', SETTINGS)

    def test_c108_enables_global_physical_timing(self):
        trip = re.search(r"function OpexAirTripModel\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(trip)
        self.assertIn("C108_AIR_ONESTEP_PHYSICAL_ECONOMICS", trip.group(1))

    def test_one_step_rule_is_relative_and_non_recursive(self):
        match = re.search(r"function OpexC107OneStepMarginalPhysicalChoice\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("marginalRoi * 1000.0 >= runner.economics.roi * relativeRoiPermille", body)
        self.assertNotIn("while (true)", body)
        self.assertNotIn("AICompany.GetBankBalance", body)

    def test_active_helper_keeps_physical_economics(self):
        match = re.search(r"function OpexC108ChooseRoutePlane\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("OpexC107OneStepMarginalPhysicalChoice", body)
        self.assertIn("return { plane = choice.plane, economics = choice.economics };", body)
        self.assertNotIn("legacy = OpexAirEconomics", body)

    def test_branch_is_isolated(self):
        full = AIR[AIR.index("function OpexAirChooseRoutePlaneFull("):]
        self.assertIn("if (C108_AIR_ONESTEP_PHYSICAL_ECONOMICS && C72_PLANE_CHOICE == 0", full)
        self.assertIn("!C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE", full)
        self.assertIn("!C109_AIR_SPEED_ELASTICITY_PHYSICAL", full)


if __name__ == "__main__":
    unittest.main()
