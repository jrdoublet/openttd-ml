#!/usr/bin/env python3
"""Tests de contrat pour C80 Étape 2 : worker RailSearchStock autonome N=1 sur reliquat (c80_rail_stock_worker)."""
from __future__ import annotations

import unittest
from pathlib import Path
import re
from diag_c80_projects_gap import extract, analyze_events

ROOT = Path(__file__).resolve().parents[1]


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class TestC80RailStockWorkerContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.main = _read("ai/OpexAI/main.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.projects = _read("ai/OpexAI/projects.nut")
        cls.task_projects = _read("ai/OpexAI/task_projects.nut")
        cls.task_rail = _read("ai/OpexAI/task_rail.nut")
        cls.orchestrator = _read("ai/OpexAI/orchestrator.nut")
        cls.scheduler = _read("ai/OpexAI/scheduler.nut")

    def test_setting_declared_in_info_nut(self):
        self.assertIn('name = "c80_rail_stock_worker"', self.info)
        start = self.info.index('name = "c80_rail_stock_worker"')
        block = self.info[start:self.info.index("});", start)]
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("custom_value = 0", block)
        self.assertIn("easy_value = 0", block)
        self.assertIn("medium_value = 0", block)
        self.assertIn("hard_value = 0", block)

    def test_global_declared_in_globals_pre_nut(self):
        self.assertIn("C80_RAIL_STOCK_WORKER <- false;", self.globals)

    def test_setting_loaded_with_gate_dependency_in_settings_nut(self):
        self.assertIn(
            'C80_RAIL_STOCK_WORKER = C80_RAIL_STOCK_GATE && (AIController.GetSetting("c80_rail_stock_worker") != 0);',
            self.settings,
        )

    def test_member_declared_and_initialized_in_main_nut(self):
        self.assertIn("_railStockCooldown = null;", self.main)
        self.assertIn("this._railStockCooldown = {};", self.main)

    def test_transient_reconstructed_in_persist_nut(self):
        self.assertIn("this._railStockCooldown = {};", self.persist)
        self.assertIn('worker.kind == "rail_stock"', self.persist)

    def test_worker_registered_in_orchestrator_nut(self):
        self.assertIn('OpexRegisterWorker("rail_stock", OpexWorkerRailStockStep, OpexWorkerRailStockCancel);', self.orchestrator)
        self.assertIn('function OpexWorkerRailStockStep(worker, opsBudget, deadlineTick)', self.orchestrator)
        self.assertIn('function OpexWorkerRailStockCancel(worker)', self.orchestrator)

    def test_orchestrator_tick_handles_rail_stock(self):
        self.assertIn('ai._checkRailStockExpiry();', self.orchestrator)
        self.assertIn('this._activeWorker.kind == "rail_stock"', self.orchestrator)
        self.assertIn('ai._tryStartRailStockWorker();', self.orchestrator)

    def test_stock_capacity_n1_enforced(self):
        self.assertIn("this._railReadyStock.len() >= 1", self.task_rail)
        self.assertIn("this._railReadyStock.len() < 1", self.task_projects)

    def test_duration_180_days_enforced(self):
        # 1. Péremption stock 180 j
        self.assertIn("age > 180", self.task_rail)
        # 2. Timeout recherche 180 j
        self.assertIn("curDate - startDate > 180", self.orchestrator)

    def test_revalidation_mandatory_before_build(self):
        self.assertIn("function OpexAI::_revalidateRailStockPlan(candidate, plan)", self.task_rail)
        self.assertIn("this._revalidateRailStockPlan(candidate, entry.plan)", self.task_rail)

    def test_v89_throughput_interaction_documented_and_guarded(self):
        # Le worker absorbe le reliquat et V89 cède sous C80_RAIL_STOCK_WORKER
        self.assertIn("if (C80_RAIL_STOCK_WORKER) V89_RAIL_SEARCH_THROUGHPUT = false;", self.settings)
        # Et le worker possède sa boucle interne sur reliquat
        self.assertIn("minThreshold = (ai._v89EstimatedSliceOps > 1500) ? ai._v89EstimatedSliceOps : 1500;", self.orchestrator)

    def test_no_pending_under_gate_and_no_search_in_progress_when_plan_ready(self):
        # Quand un plan prêt existe, _railSearch != null ne bloque plus
        self.assertIn('RAIL_SEARCH_RESUMABLE && this._railSearch != null && !(("railPlan" in candidate) && candidate.railPlan != null)', self.task_rail)
        # Sous la porte, _startRailSearch n'est pas appelé depuis _tryBuildRailProject
        call_sites = [m.start() for m in re.finditer(r"this\._startRailSearch", self.task_rail)]
        self.assertEqual(len(call_sites), 3, "Il doit y avoir exactement 3 sites d'appel à this._startRailSearch")
        for idx in call_sites:
            preceding_context = self.task_rail[max(0, idx - 2000):idx]
            self.assertIn("C80_RAIL_STOCK_GATE", preceding_context)

    def test_traces_declared(self):
        required_traces = [
            "RAIL_STOCK_START",
            "RAIL_STOCK_DEPOSIT",
            "RAIL_STOCK_TIMEOUT",
            "RAIL_STOCK_EXPIRE",
            "RAIL_STOCK_CONSUME",
            "RAIL_STOCK_REVALIDATE_FAIL",
            "RAIL_STOCK_SELECT",
        ]
        for trace in required_traces:
            self.assertIn(f'"{trace}"', self.task_rail + self.task_projects + self.projects)

    def test_stock_contains_complete_project_and_selection_replays_each_pass(self):
        self.assertIn("project = readyProject", self.task_rail)
        self.assertIn("OpexProjectFromCandidate(candidate)", self.task_rail)
        self.assertIn("kept.push(entry.project)", self.projects)
        assembly = self.projects[self.projects.index('OpexC56TaskLog("STAGE_ENTER", "c56_stage_assembly"'):]
        self.assertNotRegex(assembly, r"foreach \(candidate in rail\.candidates\) \{\s*if \(C80_RAIL_STOCK_WORKER\)")
        self.assertIn("OpexReselectProjects(projects, capitalBudget, ai._abandonedPairs, ai._lines, ai._railReadyStock)", self.projects)
        self.assertIn("::OpexPromoteLiveDefensiveAir = ::OpexPromoteLiveDefensiveAirStock", self.main)
        self.assertIn("this._projects.railStockAI <- this", self.task_projects)
        self.assertIn("railStockFusionOpcodes", self.projects)
        self.assertIn("this._railReadyStock[pairKey].project != project", self.task_rail)

    def test_diagnostic_counts_ready_funded_built_and_merge_cost(self):
        events = extract("\n".join([
            "OPEX 1970-1-1 C56_TASK RAIL_STOCK_DEPOSIT src=1 dst=2",
            "OPEX 1970-1-2 C56_TASK RAIL_STOCK_SELECT ready=1 funded=1 merge_ops=47",
            "OPEX 1970-1-3 C56_TASK RAIL_STOCK_CONSUME src=1 dst=2 delay_days=2",
        ]))
        metrics = analyze_events(events)
        self.assertEqual(metrics["stock_ready_passes"], 1)
        self.assertEqual(metrics["stock_funded_passes"], 1)
        self.assertEqual(metrics["stock_built"], 1)
        self.assertEqual(metrics["stock_merge_ops"], [47])


if __name__ == "__main__":
    unittest.main()
