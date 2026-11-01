"""ROAD1Y-G : contrat de road1y_long_v3 (trace 192, bandes fret inchangees).

Le defaut 1 allonge le trace a 192 tuiles en route seule, sans toucher
ROAD1Y_DIST_BAND_LIMITS (chemin de road1y_long_band=0). La valeur 0 laisse
le trace a 128. La valeur 1 n'allonge que le trace, apres le choix de
bandes, et seulement si les bandes sont actives et long_band vaut 0.
Hors route seule, la garde force 0 et ROAD_MAX_TRACE_TILES=48.
Aucun champ Save/Load : le reglage est relu a chaque chargement.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from test_v261_forum_behaviours import body, source


ORIGINAL_BANDS = [[64, 128], [32, 63], [7, 31]]
LONG_BAND_1 = [[129, 192], [64, 128], [32, 63], [7, 31]]
LONG_BAND_2 = [[96, 192], [48, 95], [7, 47]]


def apply_long_v3(dist_bands, long_band, long_v3):
    """Miroir de OpexLoadSettings pour le couple long_band / long_v3."""
    if long_band < 0 or long_band > 2:
        long_band = 0
    trace = 128 if dist_bands else 48
    if long_band == 1:
        bands = [list(item) for item in LONG_BAND_1]
        trace = 192
    elif long_band == 2:
        bands = [list(item) for item in LONG_BAND_2]
        trace = 192
    else:
        bands = [list(item) for item in ORIGINAL_BANDS]
    if long_v3 != 1:
        long_v3 = 0
    if long_v3 == 1 and dist_bands and long_band == 0:
        trace = 192
    return bands, trace, long_v3


def first_nonempty_band(bands, distances):
    """La premiere bande non vide l'emporte, comme candidates.nut."""
    for index, (low, high) in enumerate(bands):
        kept = [distance for distance in distances if low <= distance <= high]
        if kept:
            return index, kept
    return -1, []


class TestRoad1yLongV3(unittest.TestCase):
    def test_setting_declaration_defaults_to_one(self):
        info = source("info.nut")
        self.assertEqual(info.count('name = "road1y_long_v3"'), 1)
        block = info.split('name = "road1y_long_v3",')[1].split("});")[0]
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1", block)
        self.assertIn("flags = 0", block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{difficulty}_value = 1", block)
        self.assertNotIn("AICONFIG_BOOLEAN", block)

    def test_global_and_single_load(self):
        self.assertIn("ROAD1Y_LONG_V3 <- 0;", source("globals_pre.nut"))
        settings = source("settings.nut")
        self.assertEqual(settings.count('GetSetting("road1y_long_v3")'), 1)
        load = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_LONG_V3 = AIController.GetSetting("road1y_long_v3");', load)
        self.assertIn("if (ROAD1Y_LONG_V3 != 1) ROAD1Y_LONG_V3 = 0;", load)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_LONG_V3 = 0;", load)
        self.assertLess(
            load.index("if (!road1yRoadOnly) ROAD1Y_LONG_V3 = 0;"),
            load.index("if (ROAD1Y_LONG_V3 == 1 && ROAD1Y_DIST_BANDS && ROAD1Y_LONG_BAND == 0)"),
        )
        guard = "if (ROAD1Y_LONG_V3 == 1 && ROAD1Y_DIST_BANDS && ROAD1Y_LONG_BAND == 0)"
        self.assertIn(guard, load)
        self.assertLess(load.index("} else if (ROAD1Y_LONG_BAND == 2)"), load.index(guard))
        self.assertLess(
            load.index("ROAD1Y_DIST_BAND_LIMITS = [[64, 128], [32, 63], [7, 31]];"),
            load.index(guard),
        )
        guarded = load.split(guard, 1)[1]
        self.assertIn("ROAD_MAX_TRACE_TILES = 192;", guarded)
        self.assertNotIn("ROAD1Y_DIST_BAND_LIMITS", guarded.split("ROAD100_WAIT_FLEET", 1)[0])
        # Le require des overrides reste apres ce chargement, sans seconde lecture.
        loader = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertNotIn("road1y_long_v3", loader)
        self.assertLess(
            loader.index('require("bus_districts.nut")'),
            loader.index('require("bus_districts_overrides.nut")'),
        )
        main = source("main.nut")
        self.assertLess(main.index("OpexLoadSettings();"), main.index("OpexLoadBusDistrictSettings();"))

    def test_default_zero_matches_long_band_zero_and_value_one_keeps_bands(self):
        self.assertEqual(apply_long_v3(True, 0, 0), (ORIGINAL_BANDS, 128, 0))
        self.assertEqual(apply_long_v3(True, 0, 1), (ORIGINAL_BANDS, 192, 1))
        self.assertEqual(apply_long_v3(True, 0, 7), (ORIGINAL_BANDS, 128, 0))
        self.assertEqual(apply_long_v3(False, 0, 1), (ORIGINAL_BANDS, 48, 1))
        self.assertEqual(apply_long_v3(True, 1, 1), (LONG_BAND_1, 192, 1))
        self.assertEqual(apply_long_v3(True, 2, 1), (LONG_BAND_2, 192, 1))
        self.assertEqual(apply_long_v3(True, 2, 0), (LONG_BAND_2, 192, 0))

    def test_freight_head_band_still_wins_while_pax_cap_reaches_192(self):
        distances = [40, 70, 100, 150]
        bands, trace, _value = apply_long_v3(True, 0, 1)
        index, kept = first_nonempty_band(bands, distances)
        self.assertEqual(index, 0)
        self.assertEqual(kept, [70, 100])
        self.assertNotIn(150, kept)
        self.assertEqual(trace, 192)
        pax_allowed = [distance for distance in distances if distance <= trace]
        self.assertIn(150, pax_allowed)
        # long_band=2, le cas mesure, prend 100 et 150 et saute 70.
        preempted, skipped = first_nonempty_band(LONG_BAND_2, distances)
        self.assertEqual(preempted, 0)
        self.assertEqual(skipped, [100, 150])
        self.assertNotIn(70, skipped)

    def test_callers_and_persistence(self):
        joined = "\n".join(source(name) for name in (
            "globals_pre.nut", "info.nut", "settings.nut", "persist.nut",
            "candidates.nut", "po01c_regen.nut", "bus_districts_overrides.nut",
            "builder_road.nut", "opcode_exact.nut",
        ))
        self.assertEqual(joined.count('GetSetting("road1y_long_v3")'), 1)
        self.assertNotIn("road1y_long_v3", source("persist.nut"))
        self.assertNotIn("ROAD1Y_LONG_V3", source("persist.nut"))
        self.assertNotIn("road1y_long_v3", source("bus_districts_overrides.nut"))
        # Le plafond de trace lu par le plan PAX et le fret en L existe deja.
        for name, function in (
            ("bus_districts_overrides.nut", "OpexRoadPlanPaxVoirie"),
            ("opcode_exact.nut", "OpexRoadPlanForActive"),
            ("candidates.nut", "OpexRoadDistanceAllowed"),
            ("candidates.nut", "OpexBuildRoadCandidates"),
            ("po01c_regen.nut", "OpexPO01CGenerateMode"),
            ("builder_road.nut", "OpexRoadBfsPath"),
            ("builder_road.nut", "OpexRoadTrace"),
        ):
            self.assertIn("function " + function, source(name), function)
        pax = body("bus_districts_overrides.nut", "OpexRoadPlanPaxVoirie")
        self.assertIn("OpexRoadBfsPath(siteA.tile, siteB.tile, ROAD_MAX_TRACE_TILES", pax)
        build = body("candidates.nut", "OpexBuildRoadCandidates")
        self.assertIn("if (all.len() > before) break;", build)
        self.assertLess(build.index("if (all.len() > before) break;"),
                        build.index("OpexRoad100SoloPaxCandidates"))
        self.assertIn(
            "ROAD_MAX_TRACE_TILES <- ROAD1Y_DIST_BANDS ? 128 : 48;",
            source("builder_road.nut"),
        )

    def test_squirrel_hazards_in_touched_files(self):
        for filename in ("globals_pre.nut", "info.nut", "settings.nut"):
            code = source(filename)
            for word in ("clone", "base", "par", "parent", "static", "delegate",
                         "vargc", "vargv", "resume", "yield", "constructor", "instanceof"):
                self.assertNotRegex(
                    code, r"\blocal\s+" + word + r"\b", f"local {word} in {filename}")
            self.assertNotIn("function(", code, filename)
            self.assertNotIn(".find(", code, filename)
            for block in re.findall(r"try\s*\{[^}]*\}", code, re.DOTALL):
                self.assertNotIn("yield", block, filename)


if __name__ == "__main__":
    unittest.main()
