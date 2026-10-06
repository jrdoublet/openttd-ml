#!/usr/bin/env python3
"""Contrat statique de v107_densify_portfolio.

Le reglage vaut 0 aux quatre difficultes. A 0 le depenseur rail reste en place.
A 1 la densification rail est une entree de flotte ; la route n'est pas branchee.
Aucune partie OpenTTD n'est lancee.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _setting_block(info, name):
    start = info.index(f'name = "{name}"')
    return info[start:info.index("});", start)]


def _function_body(source, signature):
    start = source.index(signature)
    nxt = source.find("\nfunction ", start + 1)
    if nxt < 0:
        nxt = len(source)
    return source[start:nxt]


class TestV107DensifyPortfolioContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.globals_post = _read("ai/OpexAI/globals_post.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.task_rail = _read("ai/OpexAI/task_rail.nut")
        cls.task_road = _read("ai/OpexAI/task_road.nut")
        cls.task_projects = _read("ai/OpexAI/task_projects.nut")
        cls.scheduler = _read("ai/OpexAI/scheduler_tasks.nut")
        cls.orchestrator = _read("ai/OpexAI/orchestrator.nut")
        cls.projects = _read("ai/OpexAI/projects_builders.nut")
        cls.models = _read("ai/OpexAI/projects_models.nut")
        cls.update = _read("ai/OpexAI/projects_update.nut")
        cls.economy = _read("ai/OpexAI/economy.nut")
        cls.builder = _read("ai/OpexAI/builder_rail.nut")
        cls.expand = _function_body(cls.task_rail, "function OpexAI::_expandRailLines(")
        cls.fleet = _function_body(cls.projects, "function OpexProjectFromFleet(")
        cls.marginal = _function_body(cls.economy, "function OpexRailSecondTrainMarginal(")
        cls.road = _function_body(cls.task_road, "function OpexAI::_refleetRoadLines(")
        cls.dispatch_expand = _function_body(
            cls.scheduler, "function OpexAI::_dispatchExpand(task, year)"
        )

    def test_setting_declared_inert(self):
        block = _setting_block(self.info, "v107_densify_portfolio")
        self.assertIn("Road refleet is unchanged.", block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 0", block)
        self.assertNotIn("easy_value = 1", block)

    def test_global_and_single_load(self):
        self.assertIn("V107_DENSIFY_PORTFOLIO <- false;", self.globals)
        self.assertIn("RAIL_REFLEET <- true;", self.globals)
        self.assertIn("ROAD_REFLEET <- true;", self.globals_post)
        needle = 'AIController.GetSetting("v107_densify_portfolio")'
        self.assertEqual(self.settings.count(needle), 1)
        self.assertIn(
            'V107_DENSIFY_PORTFOLIO = AIController.GetSetting("v107_densify_portfolio") != 0;',
            self.settings,
        )
        self.assertNotIn("V107_DENSIFY_PORTFOLIO <-", self.settings)

    def test_rail_spend_stays_behind_the_guard(self):
        body = self.expand
        self.assertIn("function OpexAI::_expandRailLines(year, plan = null)", body)
        self.assertEqual(body.count("if (V107_DENSIFY_PORTFOLIO) continue;"), 2)
        blank = body.index("if (plan != null)")
        blank_end = body.index("return true;", blank)
        budget = body.index("this._budget.begin();")
        self.assertLess(blank, blank_end)
        self.assertLess(blank_end, budget)
        self.assertIn("this._appendRailRefleetPlan(plan);", body[blank:blank_end])
        self.assertNotIn("OpexBuildSecondTrain(", body[blank:blank_end])
        second = body.index("OpexBuildSecondTrain(")
        upgrade = body.index("OpexUpgradeRailLineToDoubleTrack(")
        first_guard = body.index("if (V107_DENSIFY_PORTFOLIO) continue;")
        second_guard = body.index("if (V107_DENSIFY_PORTFOLIO) continue;", first_guard + 1)
        self.assertLess(first_guard, second)
        self.assertLess(second_guard, upgrade)
        self.assertIn("OpexBuildSecondTrain", self.builder)

    def test_marginal_refuses_without_observed_line_profit_fallback(self):
        self.assertNotIn("lastProfit", self.marginal)
        self.assertIn("line.lastRevenue", self.marginal)
        self.assertIn(".tofloat()", self.marginal)
        self.assertIn("if (revenue1 == null || revenue2 == null || revenue1 <= 0) return null;", self.marginal)
        revenue = _function_body(self.economy, "function OpexRailRevenueAtTrainCount(")
        self.assertIn("line.monthly", revenue)
        self.assertIn("OpexRailFixedConsist", revenue)
        self.assertNotIn("lastProfit", revenue)

    def test_pricer_refuses_missing_marginal_before_line_profit(self):
        gate = self.fleet.index('if (!usedTargetMarginal && ("v107Densify" in entry))')
        fallback = self.fleet.index('if (!usedTargetMarginal) {', gate)
        block = self.fleet[gate:fallback]
        self.assertIn('entry.v107Densify != "rail"', block)
        self.assertIn('!("v107MarginalProfit" in entry)', block)
        self.assertIn("return null;", block)
        self.assertNotIn("profitIsObserved = true;", block)
        self.assertNotIn("lastProfit", block)
        self.assertLess(gate, self.fleet.index('perPlaneProfit = line.lastProfit / have;'))

    def test_injection_keeps_air_fleet_and_road_is_untouched(self):
        self.assertIn("densifyOnly = false", self.update)
        self.assertIn("OpexV107RailDensifyProject(project)", self.update)
        self.assertIn("if (FLEET_PORTFOLIO && fleetPlan != null)", self.update)
        self.assertNotIn("V107_DENSIFY_PORTFOLIO", self.road)
        self.assertIn("OpexRoadRefleet", self.road)
        factor = _function_body(self.models, "function OpexC70Factor(")
        self.assertIn('payload.v107Densify == "rail"', factor)
        self.assertIn('mode = "rail"', factor)
        self.assertIn('mode = "air"', factor)

    def test_call_sites_are_guarded_and_expand_still_spends_when_off(self):
        self.assertIn("this._expandRailLines(year);", self.dispatch_expand)
        self.assertIn("return true;", self.dispatch_expand)
        self.assertIn("V107_DENSIFY_PORTFOLIO", self.dispatch_expand)
        self.assertIn(
            "OpexInjectFleetProjects(this._projects, densifyPlan, this._abandonedPairs, budgetNow, this._lines, true);",
            self.dispatch_expand,
        )
        for source in (self.scheduler, self.task_projects, self.orchestrator):
            self.assertIn(
                "if (V107_DENSIFY_PORTFOLIO) fleetPlan = this._v107AttachRailDensify(fleetPlan);",
                source,
            )
        fleet_exec = _function_body(self.task_projects, "function OpexAI::_tryBuildFleetProject(")
        self.assertIn("V107_DENSIFY_PORTFOLIO", fleet_exec)
        self.assertIn("this._tryBuildRailDensifyProject", fleet_exec)
        self.assertIn("OpexAirAddPlane", fleet_exec)
        for forbidden in (
            "V95_SCHED_IDLE_LEDGER",
            "V95",
            "_p5OnRailSearchStart",
            "_p5OnRailSearchEnd",
            "sliceSpentOps",
        ):
            self.assertNotIn(forbidden, self.task_rail)


if __name__ == "__main__":
    unittest.main()
