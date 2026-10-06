#!/usr/bin/env python3
"""Tests de contrat pour C80 Étape 1 : porte d'éligibilité rail passive (c80_rail_stock_gate)."""
from __future__ import annotations

import unittest
from pathlib import Path
import re
from opex_projects_source import read_projects_source

ROOT = Path(__file__).resolve().parents[1]


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class TestC80RailStockGateContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.main = _read("ai/OpexAI/main.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.projects = read_projects_source()
        cls.task_projects = _read("ai/OpexAI/task_projects.nut")
        cls.task_rail = _read("ai/OpexAI/task_rail.nut")

    def test_setting_declared_in_info_nut(self):
        self.assertIn('name = "c80_rail_stock_gate"', self.info)
        start = self.info.index('name = "c80_rail_stock_gate"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("custom_value = 0", block)
        self.assertIn("easy_value = 0", block)
        self.assertIn("medium_value = 0", block)
        self.assertIn("hard_value = 0", block)

    def test_global_declared_in_globals_pre_nut(self):
        self.assertIn("C80_RAIL_STOCK_GATE <- false;", self.globals)

    def test_setting_loaded_in_settings_nut(self):
        self.assertIn(
            'C80_RAIL_STOCK_GATE = AIController.GetSetting("c80_rail_stock_gate") != 0;',
            self.settings,
        )

    def test_member_declared_and_initialized_in_main_nut(self):
        self.assertIn("_railReadyStock = null;", self.main)
        self.assertIn("this._railReadyStock = {};", self.main)

    def test_transient_reconstructed_in_persist_nut(self):
        self.assertIn("this._railReadyStock = {};", self.persist)

    def test_projects_gate_in_projects_nut(self):
        self.assertIn("function OpexRailProjectHasReadyRoute(project, railReadyStock)", self.projects)
        self.assertIn("C80_RAIL_STOCK_GATE", self.projects)
        self.assertIn("if (!OpexRailProjectHasReadyRoute(project, railReadyStock)) continue;", self.projects)

    def test_task_projects_passes_rail_ready_stock(self):
        self.assertIn("this._railReadyStock", self.task_projects)

    def test_task_rail_no_start_rail_search_under_gate(self):
        # 1. Rejet propre "no_ready_route" sans appel de _startRailSearch
        self.assertIn('reason = "no_ready_route"', self.task_rail)
        self.assertIn('return { outcome = "rejected", discards = passDiscards };', self.task_rail)
        # 2. Vérification que C80_RAIL_STOCK_GATE est présent avant chaque appel à this._startRailSearch
        call_sites = [m.start() for m in re.finditer(r"this\._startRailSearch", self.task_rail)]
        self.assertEqual(len(call_sites), 3, "Il doit y avoir exactement 3 sites d'appel à this._startRailSearch")
        for idx in call_sites:
            preceding_context = self.task_rail[max(0, idx - 2000):idx]
            self.assertIn("C80_RAIL_STOCK_GATE", preceding_context, f"Site _startRailSearch à l'offset {idx} doit être gardé par C80_RAIL_STOCK_GATE")


if __name__ == "__main__":
    unittest.main()
