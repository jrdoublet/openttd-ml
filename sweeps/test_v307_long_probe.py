"""Contrats V307 : sonde de mesure des longs traces rail, bloquante, defaut 0.

Verifie :
- reglage v307_long_probe a defaut 0 aux 4 niveaux, lu une seule fois, globale declaree ;
- crochet dans les deux boucles, une seule execution, a l'annee de depart + v307_probe_year, jamais apres chargement ;
- paires villes et fret ;
- module charge, sans closure, .find() ni mot reserve comme identifiant ;
- les trois bras (base, coarse, guided) journalisent sous V307_ARM ; le cout est repricé sans guide ;
- tranches de distance et heuristique octile admissible (transcriptions Python).
"""
import re
import tempfile
import unittest
from pathlib import Path

from sweeps.diag_v307_long_paths import autopsy_table, collect, dominant_endpoint_cause, endpoint_table

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

    def test_loop_hooks_guarded(self):
        self.assertIn('require("probe_v307.nut");', self.main)
        hook = "if (V307_LONG_PROBE > 0) OpexV307MaybeRun(this._loadedFromSave);"
        # Les deux boucles (normale et profilee sous probes) portent le crochet.
        self.assertEqual(self.main.count(hook), 1)
        self.assertEqual(read("probes.nut").count(hook), 1)
        body = self.probe[self.probe.index("function OpexV307MaybeRun("):self.probe.index("function OpexV307LongProbe(")]
        self.assertIn("if (V307_DONE || loadedFromSave) return;", body)
        self.assertIn("OPEX_START_YEAR + V307_PROBE_YEAR", body)
        self.assertLess(body.index("V307_DONE = true;"), body.index("OpexV307LongProbe("))

    def test_probe_year_setting(self):
        block = re.search(r'name = "v307_probe_year",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{level}_value\s*=\s*0\b")
        self.assertEqual(read("settings.nut").count('GetSetting("v307_probe_year")'), 1)
        g = read("globals_pre.nut")
        self.assertIn("V307_PROBE_YEAR <- 0;", g)
        self.assertIn("V307_DONE <- false;", g)

    def test_freight_pairs(self):
        self.assertIn("pairs.extend(OpexV307FreightPairs(perBin));", self.probe)
        body = self.probe[self.probe.index("function OpexV307FreightPairs("):self.probe.index("function OpexV307Block(")]
        self.assertIn("CC_PASSENGERS", body)
        self.assertIn("CC_MAIL", body)
        self.assertIn('kind = "freight"', body)

    def test_autopsy_guarded(self):
        self.assertNotIn('name = "v307_abnd_autopsy"', self.info)
        self.assertIn("V307_ABND_AUTOPSY <- false;", read("globals_pre.nut"))
        self.assertIn('V307_ABND_AUTOPSY = OpexProbeEnabled(268435456);', read("settings.nut"))
        rail = read("task_rail.nut")
        hook = 'if (V307_ABND_AUTOPSY && slice.stop == "ABND" && state.kind == "primary") OpexV307Autopsy(state);'
        self.assertEqual(rail.count(hook), 1)
        # Sous DECISION_LOG, juste apres le journal RAIL_SEARCH resumable.
        i = rail.index(hook)
        self.assertIn('OpexDecide("RAIL_SEARCH", "type=resumable outcome="', rail[i - 300:i])
        body = self.probe[self.probe.index("function OpexV307Autopsy("):]
        self.assertIn("dir=fwd", body)
        self.assertIn("dir=rev", body)

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

    def test_endpoint_hooks_only_on_failures(self):
        body = self.probe[self.probe.index("function OpexV307Log("):self.probe.index("function OpexV307RailType(")]
        self.assertIn('V307_ABND_AUTOPSY && (r.stop == "ABND" || r.stop == "NOPA")', body)
        self.assertIn('V307_ABND_AUTOPSY && !coarse.ok', self.probe)
        self.assertIn('OpexV307EndpointPair("event=autopsy arm=autopsy " + head', self.probe)
        self.assertIn('OpexV307EndpointPair(head, pair.ta, pair.tb, plansA, plansB)', body)
        self.assertEqual(self.probe.count('"V307_ENDPOINT"'), 1)
        self.assertEqual(read("info.nut").count('name = "v307_abnd_autopsy"'), 0)
        self.assertEqual(self.probe.count(".Valuate("), 3)  # Sonde historique seulement.

    def test_endpoint_geometry_and_exclusive_classes(self):
        body = self.probe[self.probe.index("function OpexV307EndpointTileClass("):
                          self.probe.index("function OpexV307EndpointPair(")]
        for symbol in ("AICompany.IsMine(AITile.GetOwner(tile))", "AIRail.IsRailTile(tile)",
                       "AITile.IsWaterTile(tile)", "AITile.IsHouseTile(tile)",
                       "AITile.GetSlope(tile)", "AITile.IsBuildable(tile)"):
            self.assertIn(symbol, body)
        self.assertIn("for (local ox = -3; ox <= 3; ox++)", body)
        self.assertIn("for (local oy = -3; oy <= 3; oy++)", body)
        self.assertIn("OpexV307Octant(dx, dy)", body)
        self.assertIn("scoutMask & (255 ^ octMask)", body)
        for f in ("plans=", "maxdist=", "oct_mask=", "oct_n=", "scout_mask=", "other_n=",
                  "_sum=", "_min="):
            self.assertIn(f, body)

    def test_endpoint_reader_pairs_and_cause(self):
        text = (
            "[0] [I] OPEX 1977-09-12 V307_ENDPOINT event=autopsy arm=autopsy src=101 "
            "dst=202 kind=freight side=A plans=12 maxdist=4 oct_n=2 other_n=2 "
            "own_sum=50 rival_sum=0 water_sum=1 house_sum=9 slope_sum=5 free_sum=450 other_sum=0\n"
            "[0] [I] OPEX 1977-09-12 V307_ENDPOINT event=autopsy arm=autopsy src=101 "
            "dst=202 kind=freight side=B plans=1 maxdist=1 oct_n=1 other_n=5 "
            "own_sum=24 rival_sum=2 water_sum=0 house_sum=4 slope_sum=3 free_sum=16 other_sum=0\n"
            "[0] [I] OPEX 1977-09-12 V307_ENDPOINT event=arm arm=guided src=303 "
            "dst=404 kind=pax side=A plans=12 maxdist=2 oct_n=2 other_n=0 "
            "own_sum=0 rival_sum=0 water_sum=98 house_sum=6 slope_sum=8 free_sum=200 other_sum=0\n"
            "[0] [I] OPEX 1977-09-12 V307_ENDPOINT event=arm arm=guided src=303 "
            "dst=404 kind=pax side=B plans=12 maxdist=2 oct_n=2 other_n=0 "
            "own_sum=0 rival_sum=0 water_sum=0 house_sum=10 slope_sum=30 free_sum=200 other_sum=0\n"
        )
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            (directory / "seed42_demo.log").write_text(text, encoding="utf-8")
            _, _, _, endpoints = collect([directory])
        self.assertEqual(len(endpoints), 4)
        self.assertEqual(endpoints[0]["seed"], 42)
        self.assertEqual(dominant_endpoint_cause(endpoints[1]), "own")
        report = endpoint_table(endpoints)
        self.assertEqual(report["n_failures"], 2)
        self.assertEqual(report["other_free_sides"], 2)
        self.assertEqual(report["other_free_pct"], 50.0)
        self.assertEqual(report["other_free_any"], 1)
        self.assertEqual(report["other_free_B"], 1)
        self.assertEqual({r["cause"] for r in report["rows"]}, {"own", "water", "slope"})

    def test_autopsy_can_cross_new_year(self):
        events = [
            {"dir": "fwd", "out": "CAP", "year": 1975, "src": 100, "dst": 200,
             "campaign": "test", "seed": 42, "spent": 20000, "join": "B", "iters": 20000, "days": 95, "dist": 110},
            {"dir": "rev", "out": "OK", "year": 1976, "src": 100, "dst": 200,
             "campaign": "test", "seed": 42, "spent": 20000, "join": "B", "iters": 1600, "days": 8, "dist": 110},
        ]
        result = autopsy_table(events)
        self.assertEqual(result["searches"], 1)
        self.assertEqual(result["fwd_x_rev"], {"('CAP', 'OK')": 1})


if __name__ == "__main__":
    unittest.main()
