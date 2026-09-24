#!/usr/bin/env python3
"""Tests de contrat textuels pour V91 : heuristique pondérée A* rail (weighted A*).

Vérifie les contrats statiques du code Squirrel (.nut) :
1. Déclaration du réglage v91_astar_weight_pct dans info.nut (défaut 120 depuis le 2026-09-24, min 100, max 300, pas 10 ou 25, flags 0).
2. Déclaration de la globale V91_ASTAR_WEIGHT_PCT <- 120; dans globals_pre.nut.
3. Chargement dans settings.nut via AIController.GetSetting("v91_astar_weight_pct").
4. Présence dans parse_ai_settings et parse_ai_setting_specs de campaign_freeze.
5. Application du poids uniquement dans OpexRailPathFinderV90 (pas dans BaNaNaS ni d'autres pathfinders).
6. À 100, aucun calcul supplémentaire dans le chemin chaud : sélection de _Estimate inchangée, sans arithmétique de poids.
7. Mode test checker OpexRailPathfinderCheckerV90 : émission de V90_CHECK finish_weighted avec iters, len, cost et ratios, sans faux écarts pas à pas.
8. Extension de l'instrumentation C56_TASK_TRACE RAIL_SEARCH_END dans task_rail.nut avec iters, result (found/none/cap), len et weight.
9. Note de modification GPLv2 complétée avec date 2026-09-24 et mention V91.
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


class TestV91AstarWeightContract(unittest.TestCase):
    def test_setting_declared_in_info_nut(self):
        info = _read("ai/OpexAI/info.nut")
        self.assertIn('name = "v91_astar_weight_pct"', info)
        start = info.index('name = "v91_astar_weight_pct"')
        block = info[start:info.index("});", start)]
        self.assertIn("min_value = 100", block)
        self.assertIn("max_value = 300", block)
        self.assertIn("custom_value = 120", block)
        self.assertIn("easy_value = 120", block)
        self.assertIn("medium_value = 120", block)
        self.assertIn("hard_value = 120", block)
        self.assertIn("flags = 0", block)
        self.assertTrue("step_size = 10" in block or "step_size = 25" in block)

    def test_global_declared_in_globals_pre_nut(self):
        globals_pre = _read("ai/OpexAI/globals_pre.nut")
        self.assertIn("V91_ASTAR_WEIGHT_PCT <- 120;", globals_pre)

    def test_setting_loaded_in_settings_nut(self):
        settings = _read("ai/OpexAI/settings.nut")
        self.assertIn('AIController.GetSetting("v91_astar_weight_pct")', settings)
        self.assertIn("V91_ASTAR_WEIGHT_PCT =", settings)

    def test_campaign_freeze_specs_and_defaults(self):
        defaults = parse_ai_settings(ROOT / "ai" / "OpexAI" / "info.nut")
        specs = parse_ai_setting_specs(ROOT / "ai" / "OpexAI" / "info.nut")
        self.assertIn("v91_astar_weight_pct", defaults)
        self.assertEqual(defaults["v91_astar_weight_pct"], 120)
        spec = specs["v91_astar_weight_pct"]
        self.assertEqual(spec["min_value"], 100)
        self.assertEqual(spec["max_value"], 300)
        self.assertIn(spec["step_size"], (10, 25))
        self.assertFalse(spec["boolean"])

    def test_weight_applied_only_in_v90_class(self):
        rail = _read("ai/OpexAI/pathfinder_v90/rail.nut")
        self.assertIn("class OpexRailPathFinderV90", rail)
        self.assertIn("_EstimateWeighted", rail)
        self.assertIn("V91_ASTAR_WEIGHT_PCT", rail)

        # Vérifie que le code BaNaNaS original n'est pas modifié
        ai_dir = ROOT / "ai" / "OpexAI"
        for nut_path in ai_dir.glob("*.nut"):
            content = nut_path.read_text(encoding="utf-8")
            # Aucun appel de multiplication de poids dans builder_rail ou main
            if nut_path.name != "settings.nut":
                self.assertNotIn("V91_ASTAR_WEIGHT_PCT *", content)

    def test_weight_100_no_extra_hot_path_calculation(self):
        rail = _read("ai/OpexAI/pathfinder_v90/rail.nut")
        # À la construction, sélectionne _Estimate ou _EstimateWeighted
        self.assertIn("(this._weight > 100) ? this._EstimateWeighted : this._Estimate", rail)

        # Dans _Estimate (utilisé pour weight == 100), aucun calcul de poids ni condition de poids
        est_start = rail.index("function OpexRailPathFinderV90::_Estimate(")
        est_end = rail.index("function OpexRailPathFinderV90::_EstimateWeighted(")
        est_code = rail[est_start:est_end]
        self.assertNotIn("_weight", est_code)
        self.assertNotIn("V91", est_code)
        self.assertNotIn("/ 100", est_code)

        # Dans _EstimateWeighted (utilisé seulement pour weight > 100), le calcul est présent
        est_w_start = est_end
        est_w_end = rail.index("function OpexRailPathFinderV90::_Neighbours(")
        est_w_code = rail[est_w_start:est_w_end]
        self.assertIn("self._weight", est_w_code)
        self.assertIn("/ 100", est_w_code)

    def test_checker_finish_weighted_trace(self):
        rail = _read("ai/OpexAI/pathfinder_v90/rail.nut")
        self.assertIn("class OpexRailPathfinderCheckerV90", rail)
        self.assertIn('OpexC56TaskLog("V90_CHECK", "finish_weighted"', rail)
        self.assertIn("iters_orig=", rail)
        self.assertIn("iters_weighted=", rail)
        self.assertIn("len_orig=", rail)
        self.assertIn("len_weighted=", rail)
        self.assertIn("cost_orig=", rail)
        self.assertIn("cost_weighted=", rail)
        self.assertIn("ratio_iters=", rail)
        self.assertIn("ratio_len=", rail)
        self.assertIn("ratio_cost=", rail)

    def test_c56_task_trace_rail_search_end_extended(self):
        task_rail = _read("ai/OpexAI/task_rail.nut")
        self.assertIn('OpexC56TaskLog("RAIL_SEARCH_END"', task_rail)
        self.assertIn("result=", task_rail)
        self.assertIn("iters=", task_rail)
        self.assertIn("len=", task_rail)
        self.assertIn("weight=", task_rail)

    def test_gpl_license_and_modification_notes(self):
        rail = _read("ai/OpexAI/pathfinder_v90/rail.nut")
        self.assertIn("Modification note:", rail)
        self.assertIn("V91", rail)
        self.assertIn("2026-09-24", rail)
        self.assertIn("GPLv2", rail)


if __name__ == "__main__":
    unittest.main()
