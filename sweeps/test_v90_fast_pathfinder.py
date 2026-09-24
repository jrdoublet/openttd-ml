#!/usr/bin/env python3
"""Tests de contrat textuels pour V90 : A* ferroviaire rapide vendorisé.

Vérifie les contrats statiques du code Squirrel (.nut) :
1. Déclaration des réglages v90_fast_pathfinder et v90_pathfinder_check dans info.nut (défauts 1 et 0, flags booléen)
2. Déclaration des globales V90_FAST_PATHFINDER et V90_PATHFINDER_CHECK dans globals_pre.nut
3. Chargement dans settings.nut via AIController.GetSetting
4. Garde à 0 qui laisse RailPathFinder() inchangé (comportement et instanciation BaNaNaS)
5. Présence intégrale des avis de copyright, identifiants, mentions GPLv2 et notes de modification (OpexAI, 2026-09-24)
6. Noms de classes distincts des originaux (OpexBinaryHeapV90, OpexAyStarV90, OpexRailPathFinderV90)
7. Ensemble fermé en table Squirrel native dans aystar.nut au lieu d'AIList()
8. Précalculs (mapSizeX, offsets, coordonnées buts, ponts par longueur) et mémoïsation par recherche des requêtes de tuiles
9. Présence du mode de test pas à pas OpexRailPathfinderCheckerV90 et traces V90_CHECK
10. Absence totale de référence au dossier libsrc/ depuis le code source
"""

from __future__ import annotations

import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]

# Shim openttdlab si absent sur l'hôte
try:
    import openttdlab  # noqa: F401
except ImportError:
    fake_lab = types.ModuleType("openttdlab")
    fake_lab.bananas_ai = mock.MagicMock()
    fake_lab.bananas_ai_library = mock.MagicMock()
    fake_lab.local_folder = mock.MagicMock()
    fake_lab.run_experiments = mock.MagicMock()
    import sys
    sys.modules["openttdlab"] = fake_lab

import sys
sys.path.insert(0, str(ROOT / "sweeps"))
from campaign_freeze import parse_ai_settings, parse_ai_setting_specs


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


class TestV90FastPathfinderContract(unittest.TestCase):
    def test_settings_declared_in_info_nut(self):
        info = _read("ai/OpexAI/info.nut")
        for setting_name, value in (("v90_fast_pathfinder", 1), ("v90_pathfinder_check", 0)):
            self.assertIn(f'name = "{setting_name}"', info)
            start = info.index(f'name = "{setting_name}"')
            block = info[start:info.index("});", start)]
            self.assertIn("flags = AICONFIG_BOOLEAN", block)
            self.assertIn(f"custom_value = {value}", block)
            self.assertIn(f"easy_value = {value}", block)
            self.assertIn(f"medium_value = {value}", block)
            self.assertIn(f"hard_value = {value}", block)

    def test_globals_declared_in_globals_pre_nut(self):
        globals_pre = _read("ai/OpexAI/globals_pre.nut")
        self.assertIn("V90_FAST_PATHFINDER <- true;", globals_pre)
        self.assertIn("V90_PATHFINDER_CHECK <- false;", globals_pre)

    def test_settings_loaded_in_settings_nut(self):
        settings = _read("ai/OpexAI/settings.nut")
        self.assertIn('V90_FAST_PATHFINDER = AIController.GetSetting("v90_fast_pathfinder") != 0;', settings)
        self.assertIn('V90_PATHFINDER_CHECK = AIController.GetSetting("v90_pathfinder_check") != 0;', settings)

    def test_campaign_freeze_includes_v90_settings(self):
        defaults = parse_ai_settings(ROOT / "ai" / "OpexAI" / "info.nut")
        specs = parse_ai_setting_specs(ROOT / "ai" / "OpexAI" / "info.nut")
        self.assertIn("v90_fast_pathfinder", defaults)
        self.assertEqual(defaults["v90_fast_pathfinder"], 1)
        self.assertTrue(specs["v90_fast_pathfinder"]["boolean"])
        self.assertIn("v90_pathfinder_check", defaults)
        self.assertEqual(defaults["v90_pathfinder_check"], 0)
        self.assertTrue(specs["v90_pathfinder_check"]["boolean"])

    def test_guard_zero_preserves_rail_pathfinder(self):
        builder = _read("ai/OpexAI/builder_rail.nut")
        # Vérifie que dans OpexCreateRailPathfinder et OpexAdvanceSegmentedSearch,
        # le repli quand V90_FAST_PATHFINDER est à 0 instancie RailPathFinder()
        self.assertIn("pathfinder = RailPathFinder();", builder)
        self.assertIn("if (V90_FAST_PATHFINDER)", builder)
        self.assertIn("pathfinder = OpexRailPathFinderV90();", builder)

    def test_vendorized_files_exist_and_required(self):
        main = _read("ai/OpexAI/main.nut")
        self.assertIn('require("pathfinder_v90/binary_heap.nut");', main)
        self.assertIn('require("pathfinder_v90/aystar.nut");', main)
        self.assertIn('require("pathfinder_v90/rail.nut");', main)

        self.assertTrue((ROOT / "ai/OpexAI/pathfinder_v90/binary_heap.nut").is_file())
        self.assertTrue((ROOT / "ai/OpexAI/pathfinder_v90/aystar.nut").is_file())
        self.assertTrue((ROOT / "ai/OpexAI/pathfinder_v90/rail.nut").is_file())

    def test_licensing_and_modification_notes(self):
        files = [
            "ai/OpexAI/pathfinder_v90/binary_heap.nut",
            "ai/OpexAI/pathfinder_v90/aystar.nut",
            "ai/OpexAI/pathfinder_v90/rail.nut",
        ]
        for f in files:
            content = _read(f)
            # Note de modification
            self.assertIn("Modification note:", content, f"Note de modification manquante dans {f}")
            self.assertIn("OpexAI", content, f"Auteur OpexAI manquant dans {f}")
            self.assertIn("2026-09-24", content, f"Date manquante dans {f}")
            self.assertIn("GPLv2", content, f"Mention GPLv2 manquante dans {f}")
            # En-tête d'origine préservé
            self.assertIn("$Id: main.nut", content, f"Header Id d'origine manquant dans {f}")

    def test_distinct_class_names(self):
        heap = _read("ai/OpexAI/pathfinder_v90/binary_heap.nut")
        self.assertIn("class OpexBinaryHeapV90", heap)

        aystar = _read("ai/OpexAI/pathfinder_v90/aystar.nut")
        self.assertIn("class OpexAyStarV90", aystar)
        self.assertIn("class OpexAyStarV90.Path", aystar)
        self.assertIn("_queue_class = OpexBinaryHeapV90;", aystar)

        rail = _read("ai/OpexAI/pathfinder_v90/rail.nut")
        self.assertIn("class OpexRailPathFinderV90", rail)
        self.assertIn("class OpexRailPathFinderV90.Cost", rail)
        self.assertIn("_aystar_class = OpexAyStarV90;", rail)

    def test_closed_set_is_table_not_ailist(self):
        aystar = _read("ai/OpexAI/pathfinder_v90/aystar.nut")
        self.assertIn("this._closed = {};", aystar)
        self.assertNotIn("this._closed = AIList()", aystar)
        self.assertIn("if (cur_tile in this._closed)", aystar)
        self.assertIn("(node[0] in this._closed)", aystar)

    def test_optimizations_in_rail_pathfinder(self):
        rail = _read("ai/OpexAI/pathfinder_v90/rail.nut")
        # Précalculs constantes
        self.assertIn("this._mapSizeX = AIMap.GetMapSizeX();", rail)
        self.assertIn("this._offsets = [", rail)
        self.assertIn("this._goalCoords = [];", rail)
        self.assertIn("this._bestBridgeForLength = {};", rail)

        # Caches mémoïsés par recherche
        self.assertIn("this._cache_slope = {};", rail)
        self.assertIn("this._cache_coast = {};", rail)
        self.assertIn("this._cache_bridge = {};", rail)
        self.assertIn("this._cache_tunnel = {};", rail)
        self.assertIn("this._cache_rail = {};", rail)
        self.assertIn("this._cache_buildable = {};", rail)

        # Requêtes de tuiles utilisant le cache
        self.assertIn("function OpexRailPathFinderV90::_GetSlope(tile)", rail)
        self.assertIn("function OpexRailPathFinderV90::_IsBuildable(tile)", rail)
        self.assertIn("function OpexRailPathFinderV90::_IsCoast(tile)", rail)
        self.assertIn("function OpexRailPathFinderV90::_IsBridge(tile)", rail)
        self.assertIn("function OpexRailPathFinderV90::_IsTunnel(tile)", rail)
        self.assertIn("function OpexRailPathFinderV90::_HasRail(tile)", rail)

    def test_checker_class_and_traces(self):
        rail = _read("ai/OpexAI/pathfinder_v90/rail.nut")
        self.assertIn("class OpexRailPathfinderCheckerV90", rail)
        self.assertIn('OpexC56TaskLog("V90_CHECK"', rail)
        self.assertIn("same_path=", rail)
        self.assertIn("same_iters=", rail)

    def test_no_reference_to_libsrc_in_ai_code(self):
        ai_dir = ROOT / "ai" / "OpexAI"
        for nut_path in ai_dir.rglob("*.nut"):
            content = nut_path.read_text(encoding="utf-8")
            self.assertNotIn("libsrc", content, f"Référence à libsrc trouvée dans {nut_path}")


if __name__ == "__main__":
    unittest.main()
