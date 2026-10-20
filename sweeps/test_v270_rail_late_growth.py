"""Tests de contrat V270 : allongement tardif des rames rail saturees (v270_rail_late_growth)."""
from pathlib import Path
import unittest

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class TestV270RailLateGrowth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = read("info.nut")
        cls.settings = read("settings.nut")
        cls.globals = read("globals_pre.nut")
        cls.main = read("main.nut")
        cls.task_rail = read("task_rail.nut")
        cls.task_report = read("task_report.nut")

    def test_setting_declared_in_info(self):
        self.assertIn('name = "v270_rail_late_growth"', self.info)
        start = self.info.index('name = "v270_rail_late_growth"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 9", block)
        self.assertIn("easy_value = 0", block)
        self.assertIn("medium_value = 0", block)
        self.assertIn("hard_value = 0", block)
        self.assertIn("custom_value = 0", block)
        self.assertIn("flags = 0", block)

    def test_setting_loaded_in_settings(self):
        self.assertEqual(self.settings.count('GetSetting("v270_rail_late_growth")'), 1)
        self.assertIn("V270_RAIL_LATE_GROWTH = (lateGrowth != null && lateGrowth > 0 && lateGrowth <= 9) ? lateGrowth : 0;", self.settings)

    def test_globals_declared(self):
        self.assertIn("V270_RAIL_LATE_GROWTH <- 0;", self.globals)
        self.assertIn("V270_IDLE_CASH_MIN <- 1000000;", self.globals)
        self.assertIn("V270_MIN_SPEED_PCT <- 85;", self.globals)

    def test_main_method_declared(self):
        self.assertIn("function _v270StartWagonExpansion(year);", self.main)

    def test_inert_at_zero(self):
        start = self.task_rail.index("function OpexV270Active(year)")
        end = self.task_rail.index("}", start)
        body = self.task_rail[start:end]
        self.assertIn("if (V270_RAIL_LATE_GROWTH <= 0) return false;", body)

    def test_v257_mutual_exclusion(self):
        self.assertIn("if (this._v257Pending != null) return false;", self.task_rail)

    def test_probe_under_decision_log(self):
        start = self.task_report.index('if (lMode == "rail") {')
        dl = self.task_report.rfind("if (DECISION_LOG) {", 0, start)
        self.assertGreater(dl, 0)


if __name__ == "__main__":
    unittest.main()
