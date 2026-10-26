"""MULTI-1 opt-in selection boundaries (Squirrel execution checked by smoke).

This test protects the pre-registered scope and OFF path, including the
otherwise easy-to-break C77 AIR defence and legacy setting inventory.
"""
import re
import unittest
from pathlib import Path

from n75_mc_legacy import historical_bytes


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def src(name):
    return (AI / name).read_text(encoding="utf-8")


class Multi1RoadPriorityContracts(unittest.TestCase):
    def test_off_default_four_profiles_single_read_and_inventory(self):
        info = src("info.nut")
        settings = src("settings.nut")
        setting = re.findall(r'AddSetting\(\{\s*name = "multi1_road_priority".*?\}\);',
                             info, re.S)
        self.assertEqual(len(setting), 1)
        self.assertIn("min_value = 0, max_value = 2", setting[0])
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting[0], rf"{difficulty}_value\s*=\s*0\b")
        self.assertEqual(settings.count('AIController.GetSetting("multi1_road_priority")'), 1)
        self.assertIn("MULTI1_ROAD_PRIORITY <- 0;", src("globals_pre.nut"))
        self.assertIn("? multi1RoadPriority : 0;", settings)
        for name in ("info.nut", "settings.nut"):
            self.assertNotIn(b"multi1_road_priority", historical_bytes(name, (AI / name).read_bytes()))

    def test_off_and_diagnostic_paths_cannot_promote(self):
        code = src("projects_selection.nut")
        calls = re.findall(r'OpexMulti1RoadPromote\(', code)
        self.assertEqual(len(calls), 2)  # function declaration + unique guarded call
        self.assertIn("if (realSelection && MULTI1_ROAD_PRIORITY > 0)\n"
                      "    OpexMulti1RoadPromote(affordable, capitalBudget, MULTI1_ROAD_PRIORITY);", code)
        start = code.index("function OpexMulti1RoadPromote(")
        body = code[start:code.index("function OpexMulti1AirOverRail(", start)]
        self.assertIn('action=" + (level == 2 ? "promote" : "shadow")', body)
        self.assertIn("if (level == 2) {\n      affordable.remove(i);", body)
        self.assertEqual(body.count("affordable.remove("), 1)

    def test_scope_and_c77_priority_are_preserved(self):
        code = src("projects_selection.nut")
        block = code[code.index("function OpexMulti1RoadPromote("):
                     code.index("function OpexMulti1AirOverRail(")]
        for required in (
            "!MODE_AIR || !MODE_RAIL || !MODE_ROAD",
            "year < 1971 || year > 1973",
            'head.mode == "road"',
            "OpexProjectDefensiveAirPriority(head) != 0",
            "affordable.len() < 8 ? affordable.len() : 8",
            "road.fundScore < 0.85 * head.fundScore",
            "road.profitAnnual < 0.60 * head.profitAnnual",
            "OpexProjectFinanceCapital(road) > capitalBudget",
        ):
            self.assertIn(required, block)
        self.assertNotIn("AAAHogEx", block)
        self.assertNotIn("OpexProjectScore(", block)
        self.assertNotIn("OpexBuild", block)
        self.assertNotIn("multi1", src("persist.nut"))


if __name__ == "__main__":
    unittest.main()
