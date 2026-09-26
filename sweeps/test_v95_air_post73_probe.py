#!/usr/bin/env python3
"""Contrats statiques V95 — sonde AIR post-1973 strictement passive."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_settings, parse_ai_setting_specs


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for idx in range(brace, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start : idx + 1]
    raise AssertionError(f"unterminated function: {signature}")


class TestV95AirPost73Probe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = read("ai/OpexAI/info.nut")
        cls.settings = read("ai/OpexAI/settings.nut")
        cls.globals = read("ai/OpexAI/globals_pre.nut")
        cls.air = read("ai/OpexAI/builder_air.nut")

    def test_setting_is_declared_loaded_and_default_off(self):
        defaults = parse_ai_settings(ROOT / "ai" / "OpexAI" / "info.nut")
        specs = parse_ai_setting_specs(ROOT / "ai" / "OpexAI" / "info.nut")
        self.assertEqual(defaults["v95_air_post73_probe"], 0)
        self.assertTrue(specs["v95_air_post73_probe"]["boolean"])
        self.assertIn("V95_AIR_POST73_PROBE <- false;", self.globals)
        self.assertIn(
            'V95_AIR_POST73_PROBE = AIController.GetSetting("v95_air_post73_probe") != 0;',
            self.settings,
        )

    def test_probe_is_annual_post_1973_and_full_rebuild_only(self):
        probe = body(self.air, "function OpexAirV95Post73Probe(")
        self.assertIn("if (!V95_AIR_POST73_PROBE || ctx.targetTownId >= 0) return;", probe)
        self.assertIn("if (year < 1973 || V95_AIR_POST73_YEAR == year) return;", probe)
        self.assertIn('combo.kind == "large"', probe)
        self.assertIn("V95_AIR_POST73_YEAR = year;", probe)

    def test_shadow_site_never_enters_cache_or_candidate_lists(self):
        probe = body(self.air, "function OpexAirV95Post73Probe(")
        self.assertIn("OpexAirFindSiteListed(", probe)
        self.assertIn("requiredSlotTown, key, false", probe)
        self.assertNotIn("ctx.sites.append", probe)
        self.assertNotIn("OpexAirStoreRoutePlan", probe)
        self.assertNotIn("AIR_SITE_CACHE", probe)

    def test_two_target_families_and_current_rejection_are_separate(self):
        probe = body(self.air, "function OpexAirV95Post73Probe(")
        self.assertIn("town.pop < OpexAirLargeAirportMinPop()", probe)
        self.assertIn("local isSecond = served && !c83OwnSecond;", probe)
        for reason in ("station_limit", "origin_served", "pop_floor"):
            self.assertIn(f'"{reason}"', probe)
        self.assertIn('"small_second"', probe)

    def test_real_town_production_and_site_coverage_are_not_conflated(self):
        probe = body(self.air, "function OpexAirV95Post73Probe(")
        self.assertIn("AITown.GetLastMonthProduction(town.id, ctx.catalog.paxCargo)", probe)
        self.assertIn("AITown.GetLastMonthProduction(town.id, ctx.catalog.mailCargo)", probe)
        self.assertIn("OpexAirAirportCatchmentProduction(site.anchor", probe)
        self.assertIn("AITown.GetHouseCount(town.id)", probe)
        self.assertIn("pax_site_est=", probe)
        self.assertIn("mail_site_est=", probe)

    def test_slot_and_competitor_fields_use_physical_slot_town(self):
        probe = body(self.air, "function OpexAirV95Post73Probe(")
        self.assertIn("local slotTown = OpexAirSlotTownId(site.anchor);", probe)
        self.assertIn("AITown.GetAllowedNoise(slotTown)", probe)
        self.assertIn("competitor_airports=", probe)
        self.assertIn("own_airports=", probe)
        self.assertIn("slots_remaining=", probe)

    def test_c68_shadow_economics_use_current_proxy_and_do_not_memoize(self):
        route = body(self.air, "function OpexAirV95BestHubRoute(")
        self.assertIn("if (OpexAirTownCentersLinked(", route)
        self.assertNotIn("C83_FIXES && OpexAirTownCentersLinked", route)
        self.assertIn("TOWN_CATCHMENT_SHARE_PCT", route)
        self.assertIn("OpexAirChooseRoutePlane(", route)
        self.assertIn("ctx.infrastructureMaintenance, 0, 1, 0, null", route)
        self.assertIn("econ.profitAnnual", route)
        probe = body(self.air, "function OpexAirV95Post73Probe(")
        for field in ("plane=", "profit=", "capital=", "roi=", "available="):
            self.assertIn(field, probe)
        self.assertIn('shadowReject = "cash";', probe)

    def test_measured_counterfactual_changes_only_new_site_demand(self):
        probe = body(self.air, "function OpexAirV95Post73Probe(")
        self.assertIn("hubMonthlyMeasured", probe)
        self.assertIn("measuredMonthly = hubMonthlyMeasured + paxSiteEst;", probe)
        self.assertIn("route.best.distance, measuredMonthly", probe)
        self.assertIn("ctx.infrastructureMaintenance, 0, 1, 0, null", probe)
        for field in ("measured_monthly=", "measured_plane=", "measured_profit=",
                      "measured_capital=", "measured_roi="):
            self.assertIn(field, probe)
        self.assertIn("hubOnlyMonthly = hubMonthlyMeasured;", probe)
        self.assertIn("route.best.distance, hubOnlyMonthly", probe)
        for field in ("hub_only_monthly=", "hub_only_plane=", "hub_only_profit="):
            self.assertIn(field, probe)
        self.assertNotIn("OpexAirStoreRoutePlan", probe)


if __name__ == "__main__":
    unittest.main()
