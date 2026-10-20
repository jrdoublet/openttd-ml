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
        guard = 'if (v297Floor > 0 && project.mode == "rail" && ("roi" in project)'
        self.assertEqual(self.select.count(guard), 1)
        pos = self.select.index(guard)
        self.assertLess(self.select.index("if (project.profitAnnual < floorProfit)"), pos)
        self.assertLess(pos, self.select.index("project.fundScore <- OpexProjectScore("))

    def test_single_aggregated_log(self):
        self.assertEqual(self.select.count('OpexDecide("V297_FLOOR"'), 1)
        self.assertIn("if (v297Rejected > 0 && DECISION_LOG && realSelection)", self.select)


    def test_v297b_relax(self):
        """V297b : defaut 0, plancher effectif par appel, une seule relance au plancher divise par deux."""
        block = re.search(r'AddSetting\(\{\s*name = "v297_relax_stations",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{level}_value\s*=\s*0\b")
        self.assertEqual(self.settings.count('GetSetting("v297_relax_stations")'), 1)
        self.assertIn("V297_RELAX_STATIONS <- 0;", self.globals_pre)
        self.assertIn("if (v297Floor < 0) v297Floor = V297_RAIL_ROI_FLOOR;", self.select)
        # Relance unique : seulement depuis le plancher configure, jamais depuis le plancher reduit.
        self.assertIn("if (V297_RELAX_STATIONS > 0 && v297Rejected > 0 && v297Floor == V297_RAIL_ROI_FLOOR)",
                      self.select)
        self.assertIn('if (p.mode != "fleet") { v297HasLine = true; break; }', self.select)
        self.assertIn("AIStationList(AIStation.STATION_TRAIN).Count()", self.select)
        self.assertEqual(self.select.count("return OpexProjectSelectAffordable(v297RawAlternatives"), 1)
        self.assertIn("v297Floor / 2);", self.select)
        # Les alternatives brutes (avant dimensionnement) sont gardees pour la relance.
        self.assertLess(self.select.index("local v297RawAlternatives = alternatives;"),
                        self.select.index("alternatives = fittedAlternatives;"))


if __name__ == "__main__":
    unittest.main()
