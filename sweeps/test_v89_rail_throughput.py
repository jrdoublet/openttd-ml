#!/usr/bin/env python3
"""Tests de contrat textuels pour V89 : débit de recherche A* rail opportuniste.

Vérifie les contrats statiques du code Squirrel (.nut) :
1. Déclaration du réglage v89_rail_search_throughput dans info.nut (défaut 0, flags booléen)
2. Déclaration de la globale V89_RAIL_SEARCH_THROUGHPUT dans globals_pre.nut
3. Chargement dans settings.nut via AIController.GetSetting
4. Déclaration des champs et méthodes sur OpexAI dans main.nut
5. Garde à 0 garantissant la préservation intégrale du chemin historique
6. Échéance locale par tranche (RAIL_MICRO_DEADLINE / BUILD_TICK_MARGIN, pas d'échéance globale réfutée)
7. Instrumentation passive sous probe_events (RAIL_SLICE, RAIL_SEARCH_START, RAIL_SEARCH_END, RAIL_COMMISSION, RAIL_ANNUAL)
8. Intégration dans le gel de campagne (campaign_freeze).
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


class TestC89RailThroughputContract(unittest.TestCase):
    def test_setting_declared_in_info_nut(self):
        info = _read("ai/OpexAI/info.nut")
        self.assertIn('name = "v89_rail_search_throughput"', info)

        start = info.index('name = "v89_rail_search_throughput"')
        block = info[start:info.index("});", start)]
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("custom_value = 1", block)
        self.assertIn("easy_value = 1", block)
        self.assertIn("medium_value = 1", block)
        self.assertIn("hard_value = 1", block)

    def test_global_declared_in_globals_pre_nut(self):
        globals_pre = _read("ai/OpexAI/globals_pre.nut")
        self.assertIn("V89_RAIL_SEARCH_THROUGHPUT <- false;", globals_pre)

    def test_setting_loaded_in_settings_nut(self):
        settings = _read("ai/OpexAI/settings.nut")
        self.assertIn(
            'V89_RAIL_SEARCH_THROUGHPUT = AIController.GetSetting("v89_rail_search_throughput") != 0;',
            settings,
        )

    def test_main_nut_fields_and_methods(self):
        main = _read("ai/OpexAI/main.nut")
        self.assertIn("_v89EstimatedSliceOps = 2000;", main)
        self.assertIn("_v89LastDay = -1;", main)
        self.assertIn("_v89YearIters = 0;", main)
        self.assertIn("_v89YearSlices = 0;", main)
        self.assertIn("_v89SearchDaysThisYear = 0;", main)

        self.assertIn("function _advanceRailSearchThroughput(maxSlices = -1);", main)
        self.assertIn("function _v89TrackSearchDays(now);", main)
        self.assertIn("function _logC89AnnualRail(year);", main)

    def test_guard_zero_leaves_historical_path_intact(self):
        scheduler = _read("ai/OpexAI/scheduler.nut")
        orchestrator = _read("ai/OpexAI/orchestrator.nut")
        main = _read("ai/OpexAI/main.nut")
        tasks = _read("ai/OpexAI/scheduler_tasks.nut")
        projects = _read("ai/OpexAI/task_projects.nut")
        town = _read("ai/OpexAI/task_town.nut")

        # 1. _advanceRailSearchThroughput starts with guard
        self.assertIn("function OpexAI::_advanceRailSearchThroughput(maxSlices = -1)", scheduler)
        adv_start = scheduler.index("function OpexAI::_advanceRailSearchThroughput(maxSlices = -1)")
        adv_body = scheduler[adv_start:adv_start + 300]
        self.assertIn("if (!V89_RAIL_SEARCH_THROUGHPUT) return 0;", adv_body)
        self.assertIn('if (this._railSearch == null || this._railSearch.phase != "search") return 0;', adv_body)

        # 2. In scheduler.nut _runNextTask, historical slice is unconditionally called first
        self.assertIn("this._advanceRailSearchSliceWithLedgers();", scheduler)
        self.assertIn(
            "if (V89_RAIL_SEARCH_THROUGHPUT) {\n      this._advanceRailSearchThroughput();\n    }",
            scheduler,
        )

        # 3. In orchestrator.nut worker step, throughput is guarded
        self.assertIn(
            "if (V89_RAIL_SEARCH_THROUGHPUT) {\n    ai._advanceRailSearchThroughput();\n  }",
            orchestrator,
        )

        # 4. In main.nut Start loop, throughput is guarded
        self.assertIn("if (V89_RAIL_SEARCH_THROUGHPUT) this._advanceRailSearchThroughput();", main)

        # 5. In scheduler_tasks.nut catalog, throughput calls are guarded
        self.assertIn("if (V89_RAIL_SEARCH_THROUGHPUT) this._advanceRailSearchThroughput();", tasks)

        # 6. In task_projects.nut _tryBuildProjects, throughput calls are guarded
        self.assertIn("if (V89_RAIL_SEARCH_THROUGHPUT) this._advanceRailSearchThroughput();", projects)

        # 7. In task_town.nut _tryTownGrowth, throughput call is guarded
        self.assertIn("if (V89_RAIL_SEARCH_THROUGHPUT) this._advanceRailSearchThroughput();", town)

    def test_deadline_per_slice_preserved(self):
        rail = _read("ai/OpexAI/task_rail.nut")
        scheduler = _read("ai/OpexAI/scheduler.nut")

        # In _continueRailSearch, each slice gets a fresh deadlineTick
        self.assertIn("local deadlineTick = state.safetyDeadline;", rail)
        self.assertIn("if (RAIL_MICRO_DEADLINE) {", rail)
        self.assertIn("deadlineTick = AIController.GetTick() + RAIL_SEARCH_SLICE / 3 + BUILD_TICK_MARGIN;", rail)

        # _advanceRailSearchThroughput does not impose a global deadline, it calls _advanceRailSearchSliceWithLedgers
        adv_start = scheduler.index("function OpexAI::_advanceRailSearchThroughput(maxSlices = -1)")
        adv_body = scheduler[adv_start:adv_start + 700]
        self.assertIn("this._advanceRailSearchSliceWithLedgers();", adv_body)
        self.assertNotIn("safetyDeadline", adv_body)

    def test_passive_instrumentation_under_probe_events(self):
        rail = _read("ai/OpexAI/task_rail.nut")
        scheduler = _read("ai/OpexAI/scheduler.nut")
        tasks = _read("ai/OpexAI/scheduler_tasks.nut")

        # 1. Tranche A* avancée et cumul (RAIL_SLICE)
        self.assertIn('OpexC56TaskLog("RAIL_SLICE",', rail)
        self.assertIn("slice_iters=", rail)
        self.assertIn("spent=", rail)
        self.assertIn("budget=", rail)
        self.assertIn("done=", rail)
        self.assertIn("stop=", rail)

        # 2. Début de recherche primaire (RAIL_SEARCH_START)
        self.assertIn('OpexC56TaskLog("RAIL_SEARCH_START", "primary",', rail)
        self.assertIn("candidate.v89SelectedDate <- curDate;", rail)
        self.assertIn("candidate.v89SelectedTick <- curTick;", rail)

        # 3. Fin de recherche primaire (RAIL_SEARCH_END)
        self.assertIn('OpexC56TaskLog("RAIL_SEARCH_END", "primary",', rail)
        self.assertIn("v89SearchEndDate", rail)
        self.assertIn("v89SearchEndTick", rail)
        self.assertIn("outcome=", rail)
        self.assertIn("days=", rail)
        self.assertIn("ticks=", rail)

        # 4. Délai sélection -> mise en service à la construction (RAIL_COMMISSION)
        self.assertIn('OpexC56TaskLog("RAIL_COMMISSION", "primary",', rail)
        self.assertIn("delay_days=", rail)
        self.assertIn("search_to_service_days=", rail)

        # 5. Bilan annuel (RAIL_ANNUAL)
        self.assertIn("function OpexAI::_logC89AnnualRail(year)", scheduler)
        self.assertIn('OpexC56TaskLog("RAIL_ANNUAL", "rail",', scheduler)
        self.assertIn("year_iters=", scheduler)
        self.assertIn("year_slices=", scheduler)
        self.assertIn("search_days=", scheduler)
        self.assertIn("active_search=", scheduler)
        self.assertIn("this._logC89AnnualRail(year);", tasks)

    def test_campaign_freeze_integration(self):
        info_path = ROOT / "ai" / "OpexAI" / "info.nut"
        defaults = parse_ai_settings(info_path)
        specs = parse_ai_setting_specs(info_path)

        self.assertIn("v89_rail_search_throughput", defaults)
        self.assertEqual(defaults["v89_rail_search_throughput"], 1)
        self.assertTrue(specs["v89_rail_search_throughput"]["boolean"])
        self.assertIn("v89_rail_search_throughput", defaults)


if __name__ == "__main__":
    unittest.main()
