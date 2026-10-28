"""ROAD1Y: tests cibles des bandes de distance fret route (ordre, bornes, remise a -1)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def src(filename: str) -> str:
    return (AI / filename).read_text(encoding="utf-8")


def function_body(source: str, name: str) -> str:
    match = re.search(r"(?m)^\s*function\s+" + re.escape(name) + r"\s*\(", source)
    if match is None:
        raise AssertionError(f"Function {name} not found")
    following = re.search(r"(?m)^\s*function\s+\w+\s*\(", source[match.end():])
    end = match.end() + following.start() if following else len(source)
    return source[match.start():end]


class Road1yDistBandsContracts(unittest.TestCase):
    def setUp(self):
        self.globals = src("globals_pre.nut")
        self.info = src("info.nut")
        self.settings = src("settings.nut")
        self.candidates = src("candidates.nut")
        self.po01c_regen = src("po01c_regen.nut")
        self.builder_road = src("builder_road.nut")

    def test_globals_and_band_definitions(self):
        self.assertIn("ROAD1Y_DIST_BANDS <- true;", self.globals)
        self.assertIn("ROAD1Y_DIST_BAND <- -1;", self.globals)
        # Ordre exact des bandes : 64-96, puis 32-63, puis 7-31
        self.assertIn("ROAD1Y_DIST_BAND_LIMITS <- [[64, 96], [32, 63], [7, 31]];", self.globals)

    def test_settings_and_trace_limit(self):
        # Setting road1y_dist_bands default 1 on this branch
        block = re.search(r'name = "road1y_dist_bands"(.{0,430})', self.info, re.S)
        self.assertIsNotNone(block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{difficulty}_value\s*=\s*1")

        # Trace limit 96 when enabled, 48 otherwise
        self.assertIn('ROAD1Y_DIST_BANDS = AIController.GetSetting("road1y_dist_bands") == 1;', self.settings)
        self.assertIn('ROAD_MAX_TRACE_TILES = ROAD1Y_DIST_BANDS ? 96 : 48;', self.settings)
        self.assertIn('ROAD_MAX_TRACE_TILES <- ROAD1Y_DIST_BANDS ? 96 : 48;', self.builder_road)

    def test_distance_bounds_and_window(self):
        epoch_fn = function_body(self.candidates, "OpexRefreshEpochBounds")
        self.assertIn("if (ROAD1Y_DIST_BANDS && ROAD_MAX_TRACE_TILES > roadGenMax) roadGenMax = ROAD_MAX_TRACE_TILES;", epoch_fn)

        dist_window_fn = function_body(self.candidates, "OpexDistBornesWindow")
        self.assertIn("if (ROAD1Y_DIST_BANDS && ROAD1Y_DIST_BAND >= 0)", dist_window_fn)
        self.assertIn("ROAD1Y_DIST_BAND_LIMITS[ROAD1Y_DIST_BAND]", dist_window_fn)
        self.assertIn("if (ROAD1Y_DIST_BANDS && ROAD_MAX_TRACE_TILES > maxDist) maxDist = ROAD_MAX_TRACE_TILES;", dist_window_fn)

        dist_allowed_fn = function_body(self.candidates, "OpexRoadDistanceAllowed")
        self.assertIn("if (ROAD1Y_DIST_BANDS && ROAD1Y_DIST_BAND >= 0)", dist_allowed_fn)
        self.assertIn("local band = ROAD1Y_DIST_BAND_LIMITS[ROAD1Y_DIST_BAND];", dist_allowed_fn)
        self.assertIn("if (distance < bandMin) { stats.roadDistanceShort++; return false; }", dist_allowed_fn)
        self.assertIn("if (distance > band[1]) { stats.roadDistanceLong++; return false; }", dist_allowed_fn)
        self.assertIn("if (ROAD1Y_DIST_BANDS && ROAD_MAX_TRACE_TILES > roadCap) roadCap = ROAD_MAX_TRACE_TILES;", dist_allowed_fn)

    def test_candidates_bands_loop_reset_and_targeted_isolation(self):
        sync_fn = function_body(self.candidates, "OpexBuildRoadCandidates")
        # Seule la generation globale (targetKind == null && targetId < 0) execute les bandes
        self.assertIn("if (ROAD1Y_DIST_BANDS && targetKind == null && targetId < 0)", sync_fn)
        # Boucle sur les bandes avec try / catch de remise a -1
        self.assertIn("for (local band = 0; band < ROAD1Y_DIST_BAND_LIMITS.len(); band++)", sync_fn)
        self.assertIn("ROAD1Y_DIST_BAND = band;", sync_fn)
        self.assertIn("ROAD1Y_DIST_BAND = -1;", sync_fn)
        self.assertIn("if (all.len() > before) break;", sync_fn)
        # Catch garantit remise a -1 en cas d'exception
        self.assertIn("catch (e) {\n      ROAD1Y_DIST_BAND = -1;\n      throw e;\n    }", sync_fn)
        # Le chemin else (regeneration ciblee ou bandes desactivees) assure ROAD1Y_DIST_BAND = -1
        self.assertIn("else {\n    ROAD1Y_DIST_BAND = -1;", sync_fn)

    def test_po01c_bands_loop_reset_and_yield_safety(self):
        async_fn = function_body(self.po01c_regen, "OpexPO01CGenerateMode")
        self.assertIn("if (ROAD1Y_DIST_BANDS)", async_fn)
        self.assertIn("for (local band = 0; band < ROAD1Y_DIST_BAND_LIMITS.len(); band++)", async_fn)
        self.assertRegex(async_fn, r"ROAD1Y_DIST_BAND = -1;\s*yield null;")
        self.assertRegex(async_fn, r"ROAD1Y_DIST_BAND = -1;\s*if \(all\.len\(\) > before\) break;")
        self.assertRegex(async_fn, r"catch \(e\) \{\s*ROAD1Y_DIST_BAND = -1;\s*throw e;\s*\}")
        self.assertRegex(async_fn, r"else \{\s*ROAD1Y_DIST_BAND = -1;")

    def test_band_selection_simulation(self):
        """Simulation Python de la logique des bandes : premiere non vide retenue."""
        band_limits = [[64, 96], [32, 63], [7, 31]]

        def filter_candidates(distances):
            all_cands = []
            for band_idx, (b_min, b_max) in enumerate(band_limits):
                before = len(all_cands)
                matching = [d for d in distances if b_min <= d <= b_max]
                all_cands.extend(matching)
                if len(all_cands) > before:
                    return band_idx, all_cands
            return -1, all_cands

        # Cas 1 : candidat dans la bande 64-96 => bande 0 retenue, les autres ignorees
        band_idx, selected = filter_candidates([80, 45, 20])
        self.assertEqual(band_idx, 0)
        self.assertEqual(selected, [80])

        # Cas 2 : aucun candidat dans 64-96, candidat dans 32-63 => bande 1 retenue
        band_idx, selected = filter_candidates([45, 20])
        self.assertEqual(band_idx, 1)
        self.assertEqual(selected, [45])

        # Cas 3 : aucun candidat dans 64-96 ni 32-63, candidat dans 7-31 => bande 2 retenue
        band_idx, selected = filter_candidates([20, 10])
        self.assertEqual(band_idx, 2)
        self.assertEqual(selected, [20, 10])

        # Cas 4 : aucun candidat dans aucune bande
        band_idx, selected = filter_candidates([5, 100])
        self.assertEqual(band_idx, -1)
        self.assertEqual(selected, [])


if __name__ == "__main__":
    unittest.main()
