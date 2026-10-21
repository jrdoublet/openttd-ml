"""Contrats V307 : sonde de mesure des longs traces rail, bloquante, defaut 0.

Verifie :
- reglage v307_long_probe a defaut 0 aux 4 niveaux, lu une seule fois, globale declaree ;
- appel dans Start() garde par V307_LONG_PROBE > 0 et partie neuve, avant la boucle principale ;
- module charge, sans closure, .find() ni mot reserve comme identifiant ;
- les trois bras (base, coarse, guided) journalisent sous V307_ARM ; le cout est repricé sans guide ;
- tranches de distance et heuristique octile admissible (transcriptions Python).
"""
import re
import unittest
from pathlib import Path

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def bin_of(dist):
    """Transcription de OpexV307Bin."""
    if 120 <= dist < 180:
        return 0
    if 180 <= dist < 250:
        return 1
    if 250 <= dist < 350:
        return 2
    return -1


def step_cost(a, b, diag, side=8):
    """Transcription de OpexV307StepCost (dixiemes de tuile)."""
    length = side * 14 if diag else side * 10
    if b["n"] == 0:
        return -1
    dh = abs(b["h"] // b["n"] - a["h"] // a["n"]) if a["n"] > 0 else 0
    return length + (length * (3 * b["water"] + 2 * b["obst"])) // 5 + dh * 40


def octile(ddx, ddy, side=8):
    return side * (10 * max(ddx, ddy) + 4 * min(ddx, ddy))


class TestV307LongProbe(unittest.TestCase):
    def setUp(self):
        self.info = read("info.nut")
        self.probe = read("probe_v307.nut")
        self.main = read("main.nut")

    def test_setting_default_zero_and_loaded_once(self):
        block = re.search(r'name = "v307_long_probe",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{level}_value\s*=\s*0\b")
        self.assertIn("max_value = 9", block.group(1))
        self.assertEqual(read("settings.nut").count('GetSetting("v307_long_probe")'), 1)
        self.assertIn("V307_LONG_PROBE <- 0;", read("globals_pre.nut"))

    def test_start_hook_guarded(self):
        self.assertIn('require("probe_v307.nut");', self.main)
        hook = "if (V307_LONG_PROBE > 0 && !this._loadedFromSave) OpexV307LongProbe(V307_LONG_PROBE);"
        self.assertEqual(self.main.count(hook), 1)
        self.assertLess(self.main.index(hook), self.main.index("if (PROBE_LOOP_OPS) this._mainLoopProfiled();"))

    def test_module_squirrel_traps(self):
        self.assertNotIn("function(", self.probe)
        self.assertNotIn(".find(", self.probe)
        for word in ("parent", "clone", "base", "pass"):
            self.assertIsNone(re.search(rf"\blocal\s+{word}\b", self.probe), word)

    def test_arms_logged_and_repriced_unguided(self):
        for arm in ('"base"', "arm=coarse", '"guided"'):
            self.assertIn(arm, self.probe)
        body = self.probe[self.probe.index("function OpexV307PathCost("):self.probe.index("function OpexV307Search(")]
        self.assertNotIn("_guideTiles", body)
        self.assertIn("pf._Cost(node, tile, 0, pf)", body)
        self.assertIn("cap_ok=", self.probe)

    def test_bins(self):
        self.assertEqual([bin_of(d) for d in (119, 120, 179, 180, 249, 250, 349, 350)], [-1, 0, 0, 1, 1, 2, 2, -1])

    def test_heuristic_admissible(self):
        flat = {"n": 5, "h": 10, "water": 0, "obst": 0}
        self.assertEqual(step_cost(flat, flat, False), 80)
        self.assertEqual(step_cost(flat, flat, True), 112)
        # Octile <= cout minimal de tout chemin de blocs plats.
        for ddx in range(0, 6):
            for ddy in range(0, 6):
                diag, straight = min(ddx, ddy), abs(ddx - ddy)
                self.assertLessEqual(octile(ddx, ddy), diag * 112 + straight * 80)
        self.assertEqual(step_cost(flat, {"n": 0, "h": 0, "water": 0, "obst": 0}, False), -1)
        wet = {"n": 5, "h": 10, "water": 5, "obst": 0}
        self.assertEqual(step_cost(flat, wet, False), 80 + 80 * 15 // 5)


if __name__ == "__main__":
    unittest.main()
