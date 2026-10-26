"""MULTI-1 AIR-before-unprepared-RAIL: permanent OFF and C77 contracts."""
import re
import unittest
from pathlib import Path

from n75_mc_legacy import historical_bytes


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class Multi1AirOverRailContracts(unittest.TestCase):
    def test_frozen_setting_and_off_path(self):
        info, settings = source("info.nut"), source("settings.nut")
        setting = re.findall(r'AddSetting\(\{\s*name = "multi1_air_over_rail".*?\}\);', info, re.S)
        self.assertEqual(len(setting), 1)
        self.assertIn("min_value = 0, max_value = 2", setting[0])
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting[0], rf"{level}_value\s*=\s*0\b")
        self.assertEqual(settings.count('AIController.GetSetting("multi1_air_over_rail")'), 1)
        self.assertIn("MULTI1_AIR_OVER_RAIL <- 0;", source("globals_pre.nut"))
        self.assertIn("? multi1AirOverRail : 0;", settings)
        for name in ("info.nut", "settings.nut"):
            self.assertNotIn(b"multi1_air_over_rail", historical_bytes(name, (AI / name).read_bytes()))

        code = source("projects_selection.nut")
        self.assertEqual(code.count("OpexMulti1AirOverRail("), 2)
        self.assertIn("if (realSelection && MULTI1_AIR_OVER_RAIL > 0)\n"
                      "    OpexMulti1AirOverRail(affordable, capitalBudget, MULTI1_AIR_OVER_RAIL);", code)
        self.assertNotIn("multi1_air_over_rail", source("persist.nut"))

    def test_pre_registered_selection_gates(self):
        code = source("projects_selection.nut")
        block = code[code.index("function OpexMulti1AirOverRail("):
                     code.index("function OpexProjectSelectAffordable(")]
        for required in (
            "!MODE_AIR || !MODE_RAIL || !MODE_ROAD",
            "year < 1971 || year > 1973",
            'head.mode != "rail"',
            "OpexProjectDefensiveAirPriority(head) != 0",
            'head.payload.railPlan != null',
            "affordable.len() < 8 ? affordable.len() : 8",
            'air.mode != "air"',
            "air.fundScore < 0.80 * head.fundScore",
            "air.profitAnnual < 0.70 * head.profitAnnual",
            "OpexProjectDefensiveAirPriority(air) != 0",
            "OpexProjectFinanceCapital(air) > capitalBudget",
            'action=" + (level == 2 ? "promote" : "shadow")',
        ):
            with self.subTest(gate=required):
                self.assertIn(required, block)
        self.assertIn('if (level == 2) {\n      affordable.remove(i);', block)
        self.assertEqual(block.count("affordable.remove("), 1)
        self.assertNotIn("AAAHogEx", block)
        self.assertNotIn("OpexProjectScore(", block)
        self.assertNotIn("OpexBuild", block)


if __name__ == "__main__":
    unittest.main()
