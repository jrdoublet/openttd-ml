#!/usr/bin/env python3
"""Contrats V161 : rendement net du prochain avion, sans plafonds fixes."""
from __future__ import annotations

import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def body(name: str, source: str) -> str:
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("Unterminated " + name)


def neighbour_count(index, a, b):
    total = index.get(a, 0) - (1 if a in index else 0)
    if b != a:
        total += index.get(b, 0) - (1 if b in index else 0)
    return max(0, total)


class V161MarginalTests(unittest.TestCase):
    def test_no_fixed_prior_or_average_profit_fallback(self):
        from v237_contracts import assert_retired
        assert_retired(self, ("v161_fleet_net_marginal",))
        for name in ("globals_pre.nut", "air_fleet.nut", "task_air.nut",
                     "projects_builders.nut", "projects_models.nut"):
            src = read(name)
            self.assertNotIn("V161_PRIOR_OWN", src)
            self.assertNotIn("V161_PRIOR_NEIGHBOUR", src)
            self.assertNotIn("OpexV161PerPlaneProfit(", src)
        src = body("OpexProjectFromFleet", read("projects_builders.nut"))
        self.assertNotIn("line.lastProfit / have", src)
        self.assertNotIn("line.predRevenue / planes", src)
        self.assertIn("entry.v161BaseVehicles != have", src)
        self.assertIn("entry.v161Profit != entry.v161DeltaR - entry.v161DeltaE - entry.v161DeltaA", src)

    def test_next_step_is_physical_and_fails_closed(self):
        fleet = body("OpexV161NextMarginal", read("air_fleet.nut"))
        self.assertIn("line.c121MarginalBaseVehicles == have", fleet)
        self.assertIn("line.c121MarginalSamples == 0", fleet)
        self.assertIn("if (neighbours > 0) return null;", fleet)
        self.assertIn("after.revenueAnnual - before.revenueAnnual", fleet)
        self.assertIn("after.runningAnnual - before.runningAnnual", fleet)
        self.assertIn("after.amortAnnual - before.amortAnnual", fleet)
        self.assertIn("local dP = dR - dE - dA;", fleet)
        self.assertIn('source = "physical"', fleet)
        self.assertIn('source = "c121"', fleet)
        self.assertIn("if (dR <= 0 || dP <= 0", fleet)

    def test_one_plane_and_refresh_after_purchase(self):
        resize = body("OpexAI::_resizeAirFleets", read("task_air.nut"))
        self.assertIn("OpexV161NextMarginal(line, this._catalog, have, neighbours)", resize)
        self.assertIn("line = line, want = 1, planePrice = nextMargin.price", resize)
        self.assertIn("v161DeltaR = nextMargin.revenue", resize)
        self.assertIn("v161DeltaE = nextMargin.running", resize)
        self.assertIn("v161DeltaA = nextMargin.amort", resize)
        self.assertIn("v161Engine = nextMargin.engine", resize)
        self.assertIn("C50_NON_EXPANSION_LEDGER.air.want_sum += fleetEntry.want;", resize)
        self.assertIn("if (nextMargin == null)", resize)
        self.assertIn("OpexV161NextMarginal(line, this._catalog, have,", resize)
        self.assertIn("have += grown.added;", resize)
        self.assertIn("OpexV161NeighbourCount(line, routesIndex)", resize)

    def test_portfolio_revalidates_margin_and_engine_at_purchase(self):
        execution = body("OpexAI::_tryBuildFleetProject", read("task_projects.nut"))
        self.assertIn("OpexV161NextMarginal(line, this._catalog, liveCount,", execution)
        self.assertIn("currentMargin.engine != entry.v161Engine", execution)
        self.assertIn("currentMargin.price != entry.planePrice", execution)
        self.assertIn("currentMargin.profit != entry.v161Profit", execution)
        self.assertIn("currentMargin.revenue != entry.v161DeltaR", execution)
        self.assertIn('reason = "fleet_marginal_stale"', execution)

    def test_c121_includes_neighbour_losses_in_estim(self):
        catalog = read("air_catalog_c121.nut")
        economics = read("air_economics_c121.nut")
        self.assertIn("line.c121MarginalBaseVehicles <-", catalog)
        self.assertIn("result.c121MarginalBaseVehicles <-", catalog)
        self.assertIn("result.c121MarginalRunning <-", catalog)
        self.assertIn("result.c121MarginalAmort <-", catalog)
        self.assertIn("line.c121MarginalRunning <-", catalog)
        self.assertIn("line.c121MarginalAmort <-", catalog)
        self.assertIn("next.rawCannibalLossAnnual", catalog)
        self.assertIn("actual.rawCannibalLossAnnual", catalog)
        self.assertIn("rawCannibalLossAnnual = rawCannibalLossAnnual", economics)
        # Both economic-return shapes (full fleet and optimizer) must expose
        # this field; ESTIM bit 4 reads it from both actual and next, and a
        # missing table member raises at runtime rather than evaluating to 0.
        self.assertGreaterEqual(economics.count(
            "rawCannibalLossAnnual = rawCannibalLossAnnual"), 2)
        self.assertIn("line.estimMarginalBaseVehicles <-", catalog)

    def test_marginal_line_fields_survive_default_full_save_projection(self):
        settings = read("settings.nut")
        info = read("info.nut")
        persist = read("persist.nut")
        self.assertIn('name = "save_full_state"', info)
        self.assertIn("easy_value = 1, medium_value = 1, hard_value = 1", info)
        self.assertIn('SAVE_FULL_STATE = AIController.GetSetting("save_full_state") != 0;', settings)
        projected = body("OpexSaveProjectLine", persist)
        self.assertIn("local serializableLine = clone line;", projected)
        self.assertIn('if (key in OPEX_SAVE_LINE_SKIP)', projected)
        skip = persist.split("OPEX_SAVE_LINE_SKIP <- {", 1)[1].split("};", 1)[0]
        for field in ("c121MarginalBaseVehicles", "c121MarginalRevenue", "c121MarginalRunning",
                      "c121MarginalAmort", "estimMarginalBaseVehicles", "estimMarginalRawRevenue",
                      "estimMarginalRunning", "estimMarginalAmort"):
            self.assertNotIn(field, skip)

    def test_estim_off_rebase_keeps_v161_and_rejects_unreviewed_edits(self):
        from estim_unifie_off_lots import estim_off
        preserved = {
            "air_catalog_c121.nut": "c121MarginalBaseVehicles",
            "projects_builders.nut": "v161BaseVehicles",
            "projects_models.nut": "v161NetMarginalModeled",
            "projects_selection.nut": "v161NetMarginalModeled",
        }
        for name in ("air_catalog_c121.nut", "projects_builders.nut",
                     "projects_models.nut", "projects_selection.nut"):
            with self.subTest(name=name):
                original = read(name)
                projected = estim_off(name, original)
                self.assertEqual(estim_off(name, projected), projected)
                self.assertIn(preserved[name], projected)
                self.assertNotIn("V161_PRIOR_OWN", projected)
                self.assertNotIn("V161_PRIOR_NEIGHBOUR", projected)
        # Exact frozen ON/OFF anchors must reject a change to the V161
        # realization exemption, not silently rebuild the inverse projection.
        models = read("projects_models.nut")
        with self.assertRaises(AssertionError):
            estim_off("projects_models.nut", models.replace(
                'project.v161NetMarginalModeled)', 'project.v161UnreviewedMarginal)'))

    def test_marginal_not_double_calibrated(self):
        calc = body("OpexC70Profit", read("projects_models.nut"))
        self.assertIn('("v161NetMarginalModeled" in project)', calc)
        estim = body("OpexEstimProfit", read("projects_models.nut"))
        self.assertIn('("v161NetMarginalModeled" in project)', estim)
        builder = body("OpexProjectFromFleet", read("projects_builders.nut"))
        self.assertIn("project.v161NetMarginalModeled <- true;", builder)
        self.assertIn("project.v161Source <- entry.v161Source;", builder)
        selection = read("projects_selection.nut")
        self.assertEqual(selection.count(
            '&& !(("v161NetMarginalModeled" in project) && project.v161NetMarginalModeled);'), 2)

    def test_neighbour_index(self):
        self.assertEqual(neighbour_count({10: 3, 11: 3, 12: 1}, 10, 11), 4)
        self.assertEqual(neighbour_count({10: 3, 11: 3, 12: 1}, 12, 10), 2)
        self.assertEqual(neighbour_count({10: 3}, 10, 10), 2)
        self.assertEqual(neighbour_count({}, -1, -1), 0)


if __name__ == "__main__":
    unittest.main()
