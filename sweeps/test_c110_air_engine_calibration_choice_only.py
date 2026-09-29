import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
PROJECTS = (ROOT / "ai" / "OpexAI" / "projects.nut").read_text(encoding="utf-8")
REPORT = (ROOT / "ai" / "OpexAI" / "task_report.nut").read_text(encoding="utf-8")
PERSIST = (ROOT / "ai" / "OpexAI" / "persist.nut").read_text(encoding="utf-8")


class C110AirEngineCalibrationChoiceOnlyTests(unittest.TestCase):
    def test_setting_is_off_by_default_and_loaded(self):
        self.assertIn("C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY <- false;", GLOBALS)
        start = INFO.index('name = "c110_air_engine_calibration_choice_only"')
        snippet = INFO[start:start + 700]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)
        self.assertIn(
            'C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY = AIController.GetSetting("c110_air_engine_calibration_choice_only") != 0;',
            SETTINGS,
        )

    def test_choice_uses_existing_c82_engine_factor_path(self):
        self.assertIn(
            "if (C82_ENGINE_CALIBRATION || C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY) {\n"
            "    return OpexC82ChooseRoutePlane",
            AIR,
        )
        factor = re.search(r"function OpexC82EngineFactor\(engine\)(.*?)\n\}", PROJECTS, re.S)
        self.assertIsNotNone(factor)
        self.assertIn("!C82_ENGINE_CALIBRATION && !C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY", factor.group(1))

    def test_factor_learning_and_reload_are_enabled(self):
        self.assertIn("C82_ENGINE_CALIBRATION || C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY", REPORT)
        self.assertIn(
            "C82_ENGINE_CALIBRATION || C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY) OpexC82RecomputeFactors",
            PERSIST,
        )

    def test_project_scoring_stays_c70_under_c110(self):
        pointer = re.search(r"::OpexCalibratedProfit <- .*?;", SETTINGS)
        self.assertIsNotNone(pointer)
        self.assertIn("C82_ENGINE_CALIBRATION ? OpexC82Profit : OpexC70Profit", pointer.group(0))
        self.assertNotIn("C110", pointer.group(0))
        calibrated = re.search(r"C70_PROFIT_CALIBRATED = .*?;", SETTINGS)
        self.assertIsNotNone(calibrated)
        self.assertNotIn("C110", calibrated.group(0))


if __name__ == "__main__":
    unittest.main()
