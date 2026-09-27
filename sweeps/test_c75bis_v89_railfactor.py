#!/usr/bin/env python3
"""Tests de contrat pour le correctif sonde et les trois leviers (C75 bis, V89, facteur rail)."""
from __future__ import annotations

import unittest
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class TestLeverContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.projects = _read("ai/OpexAI/projects.nut")
        cls.task_projects = _read("ai/OpexAI/task_projects.nut")
        cls.task_rail = _read("ai/OpexAI/task_rail.nut")
        cls.scheduler = _read("ai/OpexAI/scheduler.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")

    def test_c75_bis_setting_declared(self):
        self.assertIn('name = "c75_kpass_bypass"', self.info)
        start = self.info.index('name = "c75_kpass_bypass"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn("custom_value = 1", block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)

    def test_rail_finance_bias_setting_declared(self):
        self.assertIn('name = "rail_finance_bias_pct"', self.info)
        start = self.info.index('name = "rail_finance_bias_pct"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn("min_value = 90", block)
        self.assertIn("max_value = 200", block)
        self.assertIn("custom_value = 100", block)
        self.assertIn("step_size = 5", block)

    def test_v89_rail_search_throughput_setting_declared(self):
        self.assertIn('name = "v89_rail_search_throughput"', self.info)
        start = self.info.index('name = "v89_rail_search_throughput"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn("custom_value = 1", block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)

    def test_globals_declared(self):
        self.assertIn("C75_KPASS_BYPASS <- false;", self.globals)
        self.assertIn("RAIL_FINANCE_BIAS_PCT <- 100;", self.globals)
        self.assertIn("V89_RAIL_SEARCH_THROUGHPUT <- false;", self.globals)

    def test_settings_loaded(self):
        self.assertIn('C75_KPASS_BYPASS = AIController.GetSetting("c75_kpass_bypass") != 0;', self.settings)
        self.assertIn('V89_RAIL_SEARCH_THROUGHPUT = AIController.GetSetting("v89_rail_search_throughput") != 0;', self.settings)
        self.assertIn('AIController.GetSetting("rail_finance_bias_pct")', self.settings)
        self.assertIn("RAIL_FINANCE_BIAS_PCT = (railBias != null && railBias >= 90 && railBias <= 200) ? railBias : 100;", self.settings)

    def test_c75_bis_usage_site_and_invariants(self):
        # 1. Utilisation au site k_pass de task_projects.nut
        self.assertIn("C75_KPASS_BYPASS", self.task_projects)
        # 2. Au plus un bypass par passe
        self.assertIn("c75BypassConsumed", self.task_projects)
        self.assertIn("if (!c75BypassConsumed)", self.task_projects)
        # 3. Seulement les nouvelles lignes, jamais fleet
        self.assertIn("OpexC75KPassBypassIsNewLine(project)", self.task_projects)
        # 4. Trésorerie réellement disponible requise
        self.assertIn("projCap <= availCap", self.task_projects)
        # 5. Pas d'état persistant nouveau
        self.assertNotIn("c75BypassConsumed", self.persist)
        self.assertNotIn("c75_kpass_bypass", self.persist)

    def test_rail_finance_bias_usage_site(self):
        # Utilisation dans OpexProjectFinanceCapital
        self.assertIn("if (project.mode == \"rail\") biasPct = RAIL_FINANCE_BIAS_PCT;", self.projects)
        # Route toujours à 121
        self.assertIn('else if (project.mode == "road") biasPct = 121;', self.projects)
        # Non présent en dur (170) dans OpexProjectFinanceCapital
        start = self.projects.index("function OpexProjectFinanceCapital(project)")
        fn = self.projects[start:self.projects.index("function OpexProjectVehicleCount", start)]
        self.assertNotIn("biasPct = 170;", fn)
        self.assertIn("biasPct = RAIL_FINANCE_BIAS_PCT;", fn)

    def test_no_v95_guards_in_task_rail_and_task_projects(self):
        # Aucune garde V95 dans task_rail.nut ni task_projects.nut
        self.assertNotIn("V95_SCHED_IDLE_LEDGER", self.task_rail)
        self.assertNotIn("V95", self.task_rail)
        self.assertNotIn("V95_SCHED_IDLE_LEDGER", self.task_projects)
        self.assertNotIn("V95", self.task_projects)

        # Aucun hook probe P5 dans task_rail.nut
        self.assertNotIn("_p5OnRailSearchStart", self.task_rail)
        self.assertNotIn("_p5OnRailSearchEnd", self.task_rail)
        self.assertNotIn("sliceSpentOps", self.task_rail)

        # Aucun _p2LastStopReason dans task_projects.nut
        self.assertNotIn("_p2LastStopReason", self.task_projects)


if __name__ == "__main__":
    unittest.main()
