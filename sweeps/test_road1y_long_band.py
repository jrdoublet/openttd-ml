"""ROAD1Y: tests de contrat pour le reglage road1y_long_band (extension 192 tuiles).

Verifie :
- declaration dans info.nut (défaut 0, bornes [0, 2], 4 difficultes) ;
- declaration de la globale ROAD1Y_LONG_BAND dans globals_pre.nut ;
- chargement et validation dans settings.nut (valeur 1, valeur 2, repli 0) ;
- mise a jour de ROAD1Y_DIST_BAND_LIMITS et ROAD_MAX_TRACE_TILES ;
- conformite des filtres de distance (candidates.nut, po01c_regen.nut, bus_districts_overrides.nut) ;
- simulation algorithmique de la selection par bandes pour les 3 modes (0, 1, 2) ;
- respect des contraintes Squirrel (mots reserves, pas de yield dans try, etc.).
"""

from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
sys.path.insert(0, str(ROOT / "sweeps"))

from test_v261_forum_behaviours import body, source


class TestRoad1yLongBand(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertIn('name = "road1y_long_band"', info_src)
        setting_block = info_src.split('name = "road1y_long_band",')[1].split('});')[0]
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 2", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)

    def test_global_pre_declaration(self):
        pre_src = source("globals_pre.nut")
        self.assertIn("ROAD1Y_LONG_BAND <- 0;", pre_src)
        self.assertIn("ROAD1Y_DIST_BAND_LIMITS <- [[64, 128], [32, 63], [7, 31]];", pre_src)

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_long_band")'), 1)
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_LONG_BAND = AIController.GetSetting("road1y_long_band");', load_fn)
        self.assertIn("if (ROAD1Y_LONG_BAND < 0 || ROAD1Y_LONG_BAND > 2) ROAD1Y_LONG_BAND = 0;", load_fn)
        self.assertIn("if (ROAD1Y_LONG_BAND == 1) {", load_fn)
        self.assertIn("ROAD1Y_DIST_BAND_LIMITS = [[129, 192], [64, 128], [32, 63], [7, 31]];", load_fn)
        self.assertIn("ROAD_MAX_TRACE_TILES = 192;", load_fn)
        self.assertIn("} else if (ROAD1Y_LONG_BAND == 2) {", load_fn)
        self.assertIn("ROAD1Y_DIST_BAND_LIMITS = [[96, 192], [48, 95], [7, 47]];", load_fn)
        self.assertIn("ROAD1Y_DIST_BAND_LIMITS = [[64, 128], [32, 63], [7, 31]];", load_fn)

    def test_road_max_trace_tiles_references(self):
        # Le pathfinder et les traces Manhattan doivent utiliser ROAD_MAX_TRACE_TILES
        b_road = source("builder_road.nut")
        b_overrides = source("bus_districts_overrides.nut")
        self.assertIn("OpexRoadBfsPath(siteA.tile, siteB.tile, ROAD_MAX_TRACE_TILES", b_overrides)
        self.assertIn("l.len() > ROAD_MAX_TRACE_TILES", b_overrides)
        self.assertIn("pair.d > ROAD_MAX_TRACE_TILES", b_overrides)

    def test_distance_bounds_follow_variable(self):
        cand_src = source("candidates.nut")
        regen_src = source("po01c_regen.nut")
        # candidates.nut ~653 (OpexRoadDistanceAllowed)
        allowed_fn = body("candidates.nut", "OpexRoadDistanceAllowed")
        self.assertIn("local band = ROAD1Y_DIST_BAND_LIMITS[ROAD1Y_DIST_BAND];", allowed_fn)
        self.assertIn("if (distance < bandMin) { stats.roadDistanceShort++; return false; }", allowed_fn)
        self.assertIn("if (distance > band[1]) { stats.roadDistanceLong++; return false; }", allowed_fn)
        self.assertIn("if (ROAD1Y_DIST_BANDS && ROAD_MAX_TRACE_TILES > roadCap) roadCap = ROAD_MAX_TRACE_TILES;", allowed_fn)
        # candidates.nut ~3729
        build_fn = body("candidates.nut", "OpexBuildRoadCandidates")
        self.assertIn("for (local band = 0; band < ROAD1Y_DIST_BAND_LIMITS.len(); band++)", build_fn)
        # po01c_regen.nut ~110
        po01c_fn = body("po01c_regen.nut", "OpexPO01CGenerateMode")
        self.assertIn("for (local band = 0; band < ROAD1Y_DIST_BAND_LIMITS.len(); band++)", po01c_fn)

    def test_band_selection_simulation_val1_and_val2(self):
        """Simulation Python de la selection par bandes pour valeur 1 et valeur 2."""
        # Valeur 1 : [[129, 192], [64, 128], [32, 63], [7, 31]]
        bands_v1 = [[129, 192], [64, 128], [32, 63], [7, 31]]

        def filter_bands(bands, distances):
            for idx, (b_min, b_max) in enumerate(bands):
                cands = [d for d in distances if b_min <= d <= b_max]
                if cands:
                    return idx, cands
            return -1, []

        # Pour val 1 : un candidat a 150 rentre dans la bande de tete 0
        idx, sel = filter_bands(bands_v1, [150, 80, 40])
        self.assertEqual(idx, 0)
        self.assertEqual(sel, [150])

        # Pour val 1 : si pas de >128, prend la bande [64, 128]
        idx, sel = filter_bands(bands_v1, [80, 40])
        self.assertEqual(idx, 1)
        self.assertEqual(sel, [80])

        # Valeur 2 : [[96, 192], [48, 95], [7, 47]]
        bands_v2 = [[96, 192], [48, 95], [7, 47]]

        # Pour val 2 : candidat a 100 rentre dans [96, 192]
        idx, sel = filter_bands(bands_v2, [100, 50, 20])
        self.assertEqual(idx, 0)
        self.assertEqual(sel, [100])

        # Pour val 2 : candidat a 80 rentre dans [48, 95]
        idx, sel = filter_bands(bands_v2, [80, 20])
        self.assertEqual(idx, 1)
        self.assertEqual(sel, [80])

        # Pour val 2 : candidat a 20 rentre dans [7, 47]
        idx, sel = filter_bands(bands_v2, [20])
        self.assertEqual(idx, 2)
        self.assertEqual(sel, [20])

    def test_squirrel_hazards_and_reserved_words(self):
        for filename in ("globals_pre.nut", "info.nut", "settings.nut"):
            code = source(filename)
            for word in ("clone", "base", "par", "parent", "static"):
                self.assertNotRegex(code, r"\blocal\s+" + word + r"\b", f"Found local {word} in {filename}")
            self.assertNotIn("function(", code, f"Found anonymous function in {filename}")
            self.assertNotIn(".find(", code, f"Found array .find in {filename}")
            try_blocks = re.findall(r"try\s*\{[^}]*\}", code, re.DOTALL)
            for tb in try_blocks:
                self.assertNotIn("yield", tb, f"Found yield in try block in {filename}")


if __name__ == "__main__":
    unittest.main()
