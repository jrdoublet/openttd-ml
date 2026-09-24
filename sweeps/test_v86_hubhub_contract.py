"""Tests de contrat pour les variantes V86 (cannibalisation hub->hub et plafond de routes)."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class V86HubHubContractTest(unittest.TestCase):
    def test_settings_declared_in_info_nut(self):
        info = _read("ai/OpexAI/info.nut")

        # air_hubhub_marginal
        self.assertIn('name = "air_hubhub_marginal"', info)
        marginal_block = info[info.index('name = "air_hubhub_marginal"'):]
        marginal_block = marginal_block[:marginal_block.index("});")]
        self.assertIn("flags = AICONFIG_BOOLEAN", marginal_block)
        self.assertIn("custom_value = 0", marginal_block)

        # air_hub_max_routes
        self.assertIn('name = "air_hub_max_routes"', info)
        cap_block = info[info.index('name = "air_hub_max_routes"'):]
        cap_block = cap_block[:cap_block.index("});")]
        self.assertIn("min_value = 0", cap_block)
        self.assertIn("max_value = 12", cap_block)
        self.assertIn("step_size = 1", cap_block)
        self.assertIn("flags = 0", cap_block)
        self.assertIn("custom_value = 0", cap_block)

    def test_globals_declared_in_globals_pre_nut(self):
        globals_pre = _read("ai/OpexAI/globals_pre.nut")
        self.assertIn("AIR_HUBHUB_MARGINAL <- false;", globals_pre)
        self.assertIn("AIR_HUB_MAX_ROUTES <- 0;", globals_pre)

    def test_settings_loaded_in_settings_nut(self):
        settings = _read("ai/OpexAI/settings.nut")
        self.assertIn('AIR_HUBHUB_MARGINAL = AIController.GetSetting("air_hubhub_marginal") != 0;', settings)
        self.assertIn('AIController.GetSetting("air_hub_max_routes")', settings)
        self.assertIn("AIR_HUB_MAX_ROUTES =", settings)

    def test_variante_b_route_cap_factorised_helper(self):
        builder = _read("ai/OpexAI/builder_air.nut")
        task = _read("ai/OpexAI/task_air.nut")

        # Function definition in builder_air.nut
        self.assertIn("function OpexAirAirportMaxRoutes(airportType)", builder)
        fn_start = builder.index("function OpexAirAirportMaxRoutes(airportType)")
        fn_body = builder[fn_start:fn_start + 400]
        self.assertIn("AIAirport.AT_SMALL", fn_body)
        self.assertIn("AIAirport.AT_COMMUTER", fn_body)
        self.assertIn("AIR_HUB_MAX_ROUTES > 0", fn_body)
        self.assertIn("AIR_HUB_MAX_ROUTES < defaultCap", fn_body)

        # Site 1: OpexAirPlansDiscoverHubs in builder_air.nut
        disc_start = builder.index("function OpexAirPlansDiscoverHubs(")
        disc_end = builder.index("function OpexAirPlansHubToSite(", disc_start)
        disc_body = builder[disc_start:disc_end]
        self.assertIn("local maxRoutes = OpexAirAirportMaxRoutes(existingType);", disc_body)
        self.assertNotIn("? 4 : 12", disc_body)

        # Site 2: OpexAirBatchHubHasCapacity in task_air.nut
        cap_start = task.index("function OpexAirBatchHubHasCapacity(")
        cap_end = task.index("function OpexAirBatchPlanStillLive(", cap_start)
        cap_body = task[cap_start:cap_end]
        self.assertIn("local maxRoutes = OpexAirAirportMaxRoutes(airportType);", cap_body)
        self.assertNotIn("? 4 : 12", cap_body)

    def test_variante_a_hubhub_marginal_deduction_and_precalc(self):
        builder = _read("ai/OpexAI/builder_air.nut")
        h2h_start = builder.index("function OpexAirPlansHubToHub(")
        h2h_end = builder.index("function OpexAirPlansFinalize(", h2h_start)
        h2h_body = builder[h2h_start:h2h_end]

        # Guarded by AIR_HUBHUB_MARGINAL
        self.assertIn("if (AIR_HUBHUB_MARGINAL)", h2h_body)
        self.assertIn("if (AIR_HUBHUB_MARGINAL && economics != null && economics.profitAnnual > 0)", h2h_body)

        # Precalculation happens BEFORE the hub pair loops
        precalc_pos = h2h_body.index("if (AIR_HUBHUB_MARGINAL)")
        loop_i_pos = h2h_body.index("for (local i = 0; i < hubs.len(); i++)")
        self.assertLess(precalc_pos, loop_i_pos)

        # Revenue model: uses AICargo.GetCargoIncome on distance and time, mail bonus, calibration
        self.assertIn("AICargo.GetCargoIncome(catalog.paxCargo, dist, incomeDays)", h2h_body)
        self.assertIn("AICargo.GetCargoIncome(catalog.mailCargo, dist, incomeDays)", h2h_body)
        self.assertIn("AIR_PAX_REVENUE_CALIBRATION_PCT", h2h_body)

        # Identifies stations from stationA/stationB tiles
        self.assertIn("AIStation.GetStationID", h2h_body)

        # Loss formula: 12 * pax * avgIncome
        self.assertIn("economics.carried.tofloat() * monthly1", h2h_body)
        self.assertIn("economics.carried.tofloat() * monthly2", h2h_body)
        self.assertIn("12.0 * (pax1 * hubAvgIncome[i] + pax2 * hubAvgIncome[j])", h2h_body)

        # Deducted from profitAnnual and ROI recalculated
        self.assertIn("economics = clone economics;", h2h_body)
        self.assertIn("economics.profitAnnual -= lossAnnual;", h2h_body)
        self.assertIn("economics.roi = totalCapital > 0 ? (economics.profitAnnual * 1000) / totalCapital : 0;", h2h_body)

        # Non-positive profit rejected
        self.assertIn("if (economics == null || economics.profitAnnual <= 0)", h2h_body)

        # Hypothesis documented in comments
        self.assertIn("CargoDist", h2h_body)
        self.assertIn("note de gare", h2h_body)


if __name__ == "__main__":
    unittest.main()
