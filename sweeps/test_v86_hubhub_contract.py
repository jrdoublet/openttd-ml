"""Tests de contrat pour les variantes V86 (cannibalisation hub->hub et plafond de routes)."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class V86HubHubContractTest(unittest.TestCase):
    def test_builder_air_requires_modules(self):
        builder = _read("ai/OpexAI/builder_air.nut")
        for module in ("air_trip.nut", "air_planning.nut"):
            self.assertIn(f'require("{module}");', builder)

    def test_settings_declared_in_info_nut(self):
        info = _read("ai/OpexAI/info.nut")
        self.assertNotIn('name = "air_hubhub_marginal"', info)
        # V236 : air_hub_max_routes devient la constante AIR_HUB_MAX_ROUTES = 3
        self.assertNotIn('name = "air_hub_max_routes"', info)
    def test_globals_declared_in_globals_pre_nut(self):
        globals_pre = _read("ai/OpexAI/globals_pre.nut")
        self.assertNotIn("AIR_HUBHUB_MARGINAL", globals_pre)
        self.assertIn("AIR_HUB_MAX_ROUTES <- 3;", globals_pre)
    def test_settings_loaded_in_settings_nut(self):
        settings = _read("ai/OpexAI/settings.nut")
        self.assertNotIn("air_hubhub_marginal", settings)
        self.assertNotIn("AIR_HUBHUB_MARGINAL", settings)
        self.assertNotIn('AIController.GetSetting("air_hub_max_routes")', settings)
        self.assertNotIn("AIR_HUB_MAX_ROUTES =", settings)
    def test_variante_b_route_cap_factorised_helper(self):
        trip = _read("ai/OpexAI/air_trip.nut")
        planning = _read("ai/OpexAI/air_planning.nut")
        task = _read("ai/OpexAI/task_air.nut")

        # Function definition in air_trip.nut
        self.assertIn("function OpexAirAirportMaxRoutes(airportType)", trip)
        fn_start = trip.index("function OpexAirAirportMaxRoutes(airportType)")
        fn_body = trip[fn_start:fn_start + 400]
        self.assertIn("AIAirport.AT_SMALL", fn_body)
        self.assertIn("AIAirport.AT_COMMUTER", fn_body)
        self.assertIn("AIR_HUB_MAX_ROUTES > 0", fn_body)
        self.assertIn("AIR_HUB_MAX_ROUTES < defaultCap", fn_body)

        # Site 1: OpexAirPlansDiscoverHubs in air_planning.nut
        disc_start = planning.index("function OpexAirPlansDiscoverHubs(")
        disc_end = planning.index("function OpexAirPlansHubToSite(", disc_start)
        disc_body = planning[disc_start:disc_end]
        self.assertIn("local maxRoutes = OpexAirAirportMaxRoutes(existingType);", disc_body)
        self.assertNotIn("? 4 : 12", disc_body)

        # Site 2: OpexAirBatchHubHasCapacity in task_air.nut
        cap_start = task.index("function OpexAirBatchHubHasCapacity(")
        cap_end = task.index("function OpexAirBatchPlanStillLive(", cap_start)
        cap_body = task[cap_start:cap_end]
        self.assertIn("local maxRoutes = OpexAirAirportMaxRoutes(airportType);", cap_body)
        self.assertNotIn("? 4 : 12", cap_body)

    def test_variante_a_hubhub_marginal_removed(self):
        planning = _read("ai/OpexAI/air_planning.nut")
        h2h_start = planning.index("function OpexAirPlansHubToHub(")
        h2h_end = planning.index("function OpexAirPlansFinalize(", h2h_start)
        h2h_body = planning[h2h_start:h2h_end]

        self.assertNotIn("AIR_HUBHUB_MARGINAL", h2h_body)
        self.assertNotIn("hubAvgIncome", h2h_body)

        # Non-positive profit rejected
        # Hors C113, admissionEconomics == economics.
        self.assertIn("local admissionEconomics = economics;", h2h_body)
        self.assertIn("if (economics == null || admissionEconomics == null || admissionEconomics.profitAnnual <= 0)", h2h_body)


if __name__ == "__main__":
    unittest.main()
