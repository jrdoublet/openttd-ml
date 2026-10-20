"""Contrats V297 : plancher absolu de ROI predit des nouvelles lignes rail.

Verifie : reglage a defaut 0 aux 4 niveaux et lu une fois ; globale declaree ; filtre garde par
le reglage, limite au mode rail, place apres le plancher relatif et avant le calcul du fundScore ;
journal agrege une fois par selection, sous DECISION_LOG et selection reelle.
"""
import re
import unittest
from pathlib import Path

from test_b5_rail_persistence import function_body

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class TestV297RailRoiFloor(unittest.TestCase):
    def setUp(self):
        self.info = read("info.nut")
        self.settings = read("settings.nut")
        self.globals_pre = read("globals_pre.nut")
        self.select = function_body(read("projects_selection.nut"), "function OpexProjectSelectAffordable(")

    def test_setting(self):
        block = re.search(r'AddSetting\(\{\s*name = "v297_rail_roi_floor",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{level}_value\s*=\s*0\b")
        self.assertEqual(self.settings.count('GetSetting("v297_rail_roi_floor")'), 1)
        self.assertIn("V297_RAIL_ROI_FLOOR <- 0;", self.globals_pre)

    def test_filter_guarded_and_placed(self):
        guard = 'if (V297_RAIL_ROI_FLOOR > 0 && project.mode == "rail" && ("roi" in project)'
        self.assertEqual(self.select.count(guard), 1)
        pos = self.select.index(guard)
        self.assertLess(self.select.index("if (project.profitAnnual < floorProfit)"), pos)
        self.assertLess(pos, self.select.index("project.fundScore <- OpexProjectScore("))

    def test_single_aggregated_log(self):
        self.assertEqual(self.select.count('OpexDecide("V297_FLOOR"'), 1)
        self.assertIn("if (v297Rejected > 0 && DECISION_LOG && realSelection)", self.select)


if __name__ == "__main__":
    unittest.main()
