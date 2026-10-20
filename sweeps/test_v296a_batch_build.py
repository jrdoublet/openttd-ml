"""Contrats V296a : pose de voie groupee (une commande BuildRail par alignement).

Verifie :
- reglage v296_rail_batch_build a defaut 0 aux 4 niveaux, lu une seule fois ;
- globales V296_RAIL_BATCH_BUILD et V296A_MISMATCH declarees dans globals_pre.nut ;
- au defaut, OpexBuildTrack ne groupe rien (garde sur la globale) et la pose unitaire reste en place ;
- pas de groupement sous la signalisation V199 de double voie ;
- trace groupe verifie tuile par tuile, defait par la meme commande en cas d'ecart ;
- echec du groupement : repli unitaire et saut de l'alignement (pas de re-essai quadratique) ;
- chaque sortie de OpexBuildTrack journalise V296A ;
- simulation Python de OpexV296aRunEnd sur des traces droits, diagonaux et coudes.
"""
import re
import unittest
from pathlib import Path

from test_b5_rail_persistence import function_body

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def run_end(tiles, i, rail=frozenset(), mapx=256):
    """Transcription de OpexV296aRunEnd (indices de tuile, carte de largeur mapx)."""
    def manh(a, b):
        return abs(a % mapx - b % mapx) + abs(a // mapx - b // mapx)
    n = len(tiles)
    if i + 1 > n - 2:
        return i
    s1 = tiles[i] - tiles[i - 1]
    s2 = tiles[i + 1] - tiles[i]
    if s2 == -s1:
        return i
    if manh(tiles[i - 1], tiles[i]) != 1 or manh(tiles[i], tiles[i + 1]) != 1:
        return i
    if tiles[i] in rail:
        return i
    straight = s1 == s2
    last = i
    for k in range(i + 1, n - 1):
        expect = s1 if (straight or (k - i) % 2 == 1) else s2
        if tiles[k + 1] - tiles[k] != expect:
            break
        if tiles[k] in rail:
            break
        last = k
    return last


def walk(start, steps, mapx=256):
    tiles = [start]
    for s in steps:
        tiles.append(tiles[-1] + s)
    return tiles


class TestV296aBatchBuild(unittest.TestCase):
    def setUp(self):
        self.info = read("info.nut")
        self.settings = read("settings.nut")
        self.globals_pre = read("globals_pre.nut")
        self.builder = read("builder_rail.nut")
        self.track = function_body(self.builder, "function OpexBuildTrack(")

    def test_setting_default_zero_and_loaded_once(self):
        block = re.search(r'AddSetting\(\{\s*name = "v296_rail_batch_build",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{level}_value\s*=\s*0\b")
        self.assertEqual(self.settings.count('GetSetting("v296_rail_batch_build")'), 1)
        self.assertIn("V296_RAIL_BATCH_BUILD <- 0;", self.globals_pre)
        self.assertIn("V296A_MISMATCH <- false;", self.globals_pre)

    def test_default_path_unchanged(self):
        self.assertRegex(self.track, r"local batch = \(V296_RAIL_BATCH_BUILD && !V296A_MISMATCH && "
                                     r"!\(V199_ROBUST_BUILD && isDouble\)\)")
        self.assertIn("if (batch != null && i > batch.skipUntil)", self.track)
        self.assertIn("ok = AIRail.BuildRail(prev, cur, next);", self.track)

    def test_batch_verified_and_undone(self):
        self.assertIn("AIRail.BuildRail(prev, cur, to)", self.track)
        self.assertIn("AIRail.AreTilesConnected(tiles[k - 1], tiles[k], tiles[k + 1])", self.track)
        self.assertIn("AIRail.RemoveRail(prev, cur, to);", self.track)
        self.assertIn("V296A_MISMATCH = true;", self.track)
        self.assertIn("batch.skipUntil = last;", self.track)

    def test_every_exit_logs(self):
        returns = self.track.count("return failed;")
        self.assertEqual(returns, 3)
        self.assertEqual(len(re.findall(r"OpexV296aLog\(batch\);\s*return failed;", self.track)), returns)

    def test_no_closure_nor_find(self):
        body = function_body(self.builder, "function OpexV296aRunEnd(")
        self.assertNotIn("function(", body)
        self.assertNotIn(".find(", body)

    def test_run_end_simulation(self):
        X, Y = 1, 256
        start = 100 * 256 + 100
        straight = walk(start, [X] * 10)
        # tiles[0] et tiles[-1] ne sont jamais poses : de 1, l'alignement va jusqu'a len-2.
        self.assertEqual(run_end(straight, 1), len(straight) - 2)
        diag = walk(start, [X, Y] * 6)
        self.assertEqual(run_end(diag, 1), len(diag) - 2)
        # Coude : droit puis diagonale ; le droit s'arrete a la tuile d'avant le coude.
        bend = walk(start, [X] * 5 + [Y, X, Y, X, Y, X])
        end = run_end(bend, 1)
        self.assertEqual(end, 4)
        self.assertEqual(bend[end + 1] - bend[end], X)
        # Tuile deja en rail : coupe l'alignement.
        self.assertEqual(run_end(straight, 1, rail={straight[4]}), 3)
        self.assertEqual(run_end(straight, 1, rail={straight[1]}), 1)
        # Aller-retour et saut de pont : pas d'alignement.
        self.assertEqual(run_end([start, start + X, start, start + X], 1), 1)
        jump = [start, start + X, start + 5 * X, start + 6 * X, start + 7 * X]
        self.assertEqual(run_end(jump, 1), 1)
        # Diagonale : chaque pas du groupe alterne bien s1, s2.
        e = run_end(diag, 1)
        for k in range(1, e + 1):
            self.assertNotEqual(diag[k + 1] - diag[k], diag[k] - diag[k - 1])


if __name__ == "__main__":
    unittest.main()
