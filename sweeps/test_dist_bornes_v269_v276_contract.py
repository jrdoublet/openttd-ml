"""DIST-BORNES-1 : double prefiltrage V276 vs borne fret V269.

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
    def test_v276_grid_keeps_historical_cap_when_opt_in_off(self):
        src = _squirrel("candidates_v276.nut")
        func = src.split("function OpexV276PrepareUnit(s, u)", 1)[1].split(
            "function OpexV276Evaluate", 1)[0]
        self.assertRegex(func, re.compile(r'local maxDistance\s*=\s*u\.mode\s*==\s*"road".*?:\s*bounds\.railMax', re.S))
        self.assertIn("grid.Build(destinations, maxDistance);", func)
        self.assertIn("!u.pax && DIST_BORNES_V276_FREIGHT", func)
        self.assertIn("bounds.distBornesV269Relaxed", func)
        self.assertIn("V269_RAIL_MAX_DIST > maxDistance", func)

    def test_v269_freight_final_filter_can_relax(self):
        for source_name in ("candidates.nut", "po01c_generators.nut"):
            src = _squirrel(source_name)
            with self.subTest(source=source_name):
                self.assertIn("V269_RAIL_MAX_DIST > bounds.railMax", src)
                self.assertIn("V269_RELAXED", src)
                self.assertIn("V269_RAIL_LATE_RELAX > 0", src)
        self.assertIn("V269_RAIL_MAX_DIST <- 250;", _squirrel("globals_pre.nut"))

    def test_v276_freight_also_crosses_passenger_band_guard(self):
        """The historical passenger cap remains the default branch."""
        v276 = _squirrel("candidates_v276.nut")
        unit = v276.split("function OpexV276AddUnits(units, catalog, pax)", 1)[1].split(
            "function OpexV276Start", 1)[0]
        enumerate_body = v276.split("function OpexV276Enumerate(s, u, mark, opsBudget, startTick, deadlineTick)", 1)[1].split(
            "function OpexV276", 1)[0]
        band = _squirrel("candidates.nut").split(
            "function OpexRailPaxPairInBand(bounds, distance, paxBand)", 1)[1].split(
            "/* Une origine rail", 1)[0]
        self.assertIn('pax = false, band = PAX_BAND_ALL', unit)
        self.assertIn('if (!u.pax && DIST_BORNES_V276_FREIGHT', enumerate_body)
        self.assertIn('V269_RAIL_MAX_DIST > s.catalog.bounds.railMax', enumerate_body)
        self.assertIn('distance < s.catalog.bounds.railMin || distance > V269_RAIL_MAX_DIST', enumerate_body)
        self.assertIn('else if (!OpexRailPaxPairInBand(s.catalog.bounds, distance, u.band)) continue;',
                      enumerate_body)
        self.assertIn('return distance >= bounds.railMin && distance <= bounds.railMax;', band)

    def test_widening_only_grid_would_still_drop_relaxed_freight(self):
        """Model each of the two observed predicates, without claiming engine exposure."""
        for distance in (200, 201, 249, 250, 251):
            eligible_final = _strict_distance_eligible(distance, late=True, freight=True)
            grid_fixed_only = distance <= 250  # hypothetical future one-gate fix
            rail_band_still_200 = 7 <= distance <= 200
            visible_after_both = eligible_final and grid_fixed_only and rail_band_still_200
            with self.subTest(distance=distance):
                self.assertEqual(visible_after_both, distance <= 200)

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

    def test_opt_in_four_defaults_and_deferred_request_context(self):
        info = _squirrel("info.nut")
        block = info.split('name = "dist_bornes_v276_freight"', 1)[1].split("});", 1)[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 0", block)
        self.assertIn('GetSetting("dist_bornes_v276_freight") == 1', _squirrel("settings.nut"))
        self.assertIn("DIST_BORNES_V276_FREIGHT <- false;", _squirrel("globals_pre.nut"))

        v276 = _squirrel("candidates_v276.nut")
        request = v276.split("function OpexV276Request", 1)[1].split("function OpexV276Published", 1)[0]
        start = v276.split("function OpexV276Start", 1)[1].split("function OpexV276PrepareUnit", 1)[0]
        self.assertIn("v269LateFreight = DIST_BORNES_V276_FREIGHT", request)
        self.assertIn("task.v276Request.v269LateFreight = true;", request)
        self.assertIn("if ((\"v276\" in task) && task.v276 != null)", request)
        self.assertIn("if (task.v276Request.kind != kind || task.v276Request.id != id)", request)
        self.assertIn("task.v276Request.kind = null;", request)
        self.assertIn("catalog.bounds.distBornesV269Relaxed <- request.v269LateFreight;", start)

    def test_future_grid_and_economics_agree_on_freight_201_to_250(self):
        """Synthetic boundary cases; no claim that a world exposes any such pair."""
        for opt_in in (False, True):
            for relaxed in (False, True):
                cap = 250 if opt_in and relaxed else 200
                for d in (6, 7, 200, 201, 249, 250, 251):
                    with self.subTest(opt_in=opt_in, relaxed=relaxed, distance=d):
                        from_grid = d <= cap
                        in_freight_band = 7 <= d <= cap
                        final_economics = d <= cap
                        accepted = from_grid and in_freight_band and final_economics
                        self.assertEqual(accepted, 7 <= d <= cap)

    def test_final_generator_matches_both_v269_paths(self):
        for name in ("candidates.nut", "po01c_generators.nut"):
            with self.subTest(file=name):
                source = _squirrel(name)
                self.assertIn("V269_RELAXED || (DIST_BORNES_V276_FREIGHT", source)
                self.assertIn('("distBornesV269Relaxed" in bounds) && bounds.distBornesV269Relaxed',
                              source)


if __name__ == "__main__":
    unittest.main()
