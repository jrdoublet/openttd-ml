"""DIST-BORNES-1 : risque de prefiltrage V276 vs borne fret V269.

Prouve l'ecart logique potentiel avec une grille ideale; ne pretend pas
mesurer l'exposition effective sur 1024² ni le fonctionnement d'OpenTTD.
"""

import re
import unittest
from pathlib import Path

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _squirrel(name):
    return (AI / name).read_text(encoding="utf-8")


def _strict_distance_eligible(distance, *, rail_max=200, late=False, freight=False, v269_max=250):
    cap = v269_max if freight and late and v269_max > rail_max else rail_max
    return distance <= cap


class DistanceBoundContracts(unittest.TestCase):
    def test_v276_grid_is_prepared_with_railmax(self):
        src = _squirrel("candidates_v276.nut")
        func = src.split("function OpexV276PrepareUnit(s, u)", 1)[1].split(
            "function OpexV276Evaluate", 1)[0]
        self.assertRegex(func, re.compile(r'local maxDistance\s*=\s*u\.mode\s*==\s*"road".*?:\s*bounds\.railMax', re.S))
        self.assertIn("grid.Build(destinations, maxDistance);", func)

    def test_v269_freight_final_filter_can_relax(self):
        for source_name in ("candidates.nut", "po01c_generators.nut"):
            src = _squirrel(source_name)
            with self.subTest(source=source_name):
                self.assertIn("V269_RAIL_MAX_DIST > bounds.railMax", src)
                self.assertIn("V269_RELAXED", src)
                self.assertIn("V269_RAIL_LATE_RELAX > 0", src)
        self.assertIn("V269_RAIL_MAX_DIST <- 250;", _squirrel("globals_pre.nut"))

    def test_synthetic_frontier_show_potential_missing_freight_pairs(self):
        distances = (199, 200, 201, 249, 250, 251)
        ideal_grid = {d for d in distances if d <= 200}
        final_freight = {d for d in distances if _strict_distance_eligible(d, freight=True, late=True)}
        final_pax = {d for d in distances if _strict_distance_eligible(d, freight=False, late=True)}
        self.assertEqual(final_freight - ideal_grid, {201, 249, 250})
        self.assertEqual(final_pax - ideal_grid, set())
        self.assertNotIn(251, final_freight)

    def test_without_relaxation_no_mismatch(self):
        for freight in (True, False):
            for d in (200, 201, 249, 250, 251):
                with self.subTest(freight=freight, distance=d):
                    self.assertEqual(_strict_distance_eligible(d, freight=freight), d <= 200)


if __name__ == "__main__":
    unittest.main()
