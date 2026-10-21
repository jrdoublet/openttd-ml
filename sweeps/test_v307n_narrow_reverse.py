"""Contrats V307 1.0 : recherche depuis le cote etroit (v303_reverse_mode 3 et 4, defaut 0).

Verifie :
- reglage borne a 4, lecture bornee a 4 ;
- choix du cote etroit : quais B moins nombreux que A (mode 3), ou tout le fret (mode 4) ;
- hors cote etroit, le chemin historique (sonde V294f comprise) est garde ;
- en cote etroit, l'inverse recoit tout le plafond, sans aller ; file videe = NOPA.
"""
import re
import unittest
from pathlib import Path

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def narrow(mode, na, nb, kind):
    """Transcription de OpexV307NarrowReverse."""
    if mode < 3:
        return False
    if nb < na:
        return True
    return mode == 4 and kind == "freight"


class TestV307NarrowReverse(unittest.TestCase):
    def setUp(self):
        self.rail = read("builder_rail.nut")
        self.task = read("task_rail.nut")

    def test_setting_bounds(self):
        block = re.search(r'name = "v303_reverse_mode",(.*?)\}\);', read("info.nut"), re.S)[1]
        self.assertIn("max_value = 4", block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{level}_value\s*=\s*0\b")
        self.assertIn("reverseMode >= 0 && reverseMode <= 4)", read("settings.nut"))

    def test_narrow_rule(self):
        body = self.rail[self.rail.index("function OpexV307NarrowReverse("):self.rail.index("function OpexV303CreateReverse(")]
        self.assertIn("plan.plansB.len() < plan.plansA.len()", body)
        self.assertIn('mode == 4 && candidate.kind == "freight"', body)
        self.assertEqual([narrow(m, 12, 1, "pax") for m in (0, 1, 2, 3, 4)], [False, False, False, True, True])
        self.assertEqual([narrow(m, 12, 12, "freight") for m in (3, 4)], [False, True])
        self.assertFalse(narrow(4, 12, 12, "pax"))

    def test_historic_path_outside_narrow(self):
        i = self.task.index("local v303Mode = V303_REVERSE_MODE;")
        seg = self.task[i:i + 400]
        self.assertIn("if (v303Mode >= 3 && !OpexV307NarrowReverse(v303Mode, plan, candidate)) v303Mode = 0;", seg)
        self.assertIn("if (v303Mode == 0) {", seg)
        self.assertIn("OpexV303CreateReverse(plan, clearanceTiles, searchWeight, candidate, v303Mode)", self.task)
        self.assertNotIn("V303_REVERSE_MODE == 2", self.task)

    def test_whole_cap_and_nopa(self):
        body = self.rail[self.rail.index("function OpexV303CreateReverse("):self.rail.index("function OpexV303LogProbe(")]
        self.assertIn("V294_RAIL_REVERSE_PROBE > 0 || mode >= 3", body)
        self.assertIn("(mode >= 3) ? plan.iterationBudget + V294_RAIL_REVERSE_PROBE", body)
        adv = self.rail[self.rail.index("function OpexV303AdvanceReverse("):]
        self.assertIn("(s.mode == 1 || narrow || s.reverseTurn || s.forwardDone)", adv)
        self.assertIn('else if (narrow && s.reverseDone) stop = (path == null) ? "NOPA" : "ABND";', adv)


if __name__ == "__main__":
    unittest.main()
