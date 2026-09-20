from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from bench_v2 import air_equipment_diagnostic_stats
from campaign_freeze import parse_ai_settings

AIR = ROOT / "ai" / "OpexAI" / "builder_air.nut"
CANDIDATES = ROOT / "ai" / "OpexAI" / "candidates.nut"
CATALOG = ROOT / "ai" / "OpexAI" / "catalog.nut"
INFO = ROOT / "ai" / "OpexAI" / "info.nut"
SETTINGS = ROOT / "ai" / "OpexAI" / "settings.nut"


class TestAirBestEquipment(unittest.TestCase):
    def test_c68_stays_default_and_new_switches_are_experimental(self):
        defaults = parse_ai_settings(INFO)
        self.assertEqual(defaults["air_route_plane_selection"], 1)
        self.assertEqual(defaults["air_equipment_regret_probe"], 0)
        self.assertEqual(defaults["air_best_equipment"], 0)
        self.assertEqual(defaults["air_capital_frontier"], 0)
        self.assertEqual(defaults["air_capital_frontier_probe"], 0)
        settings = SETTINGS.read_text(encoding="utf-8")
        self.assertIn('AIController.GetSetting("air_equipment_regret_probe")', settings)
        self.assertIn('AIController.GetSetting("air_best_equipment")', settings)
        self.assertIn('AIController.GetSetting("air_capital_frontier")', settings)
        self.assertIn('AIController.GetSetting("air_capital_frontier_probe")', settings)

    def test_best_equipment_reuses_demand_and_economics(self):
        src = AIR.read_text(encoding="utf-8")
        self.assertIn("function OpexAirBestEquipment", src)
        self.assertIn("function OpexAirDemandContext", src)
        self.assertIn("if (demandContext.perPlane)", src)
        self.assertIn("OpexAirPlanDemand(siteA, siteB, plane, catalog, lines)", src)
        self.assertIn("OpexAirEconomics(catalog, airport, plane, distance, monthlyDemand", src)
        self.assertIn("economics.profitAnnual > bestEconomics.profitAnnual", src)
        self.assertIn("economics.roi > bestEconomics.roi", src)
        self.assertIn("function OpexAirEquipmentContext", src)
        self.assertIn("local context = OpexAirEquipmentContext(catalog, airport, siteA, siteB);", src)
        self.assertIn("context.typeA, plane.planeType", src)
        self.assertIn("plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance", src)

    def test_all_three_air_arms_use_unified_engine_when_enabled(self):
        src = AIR.read_text(encoding="utf-8")
        self.assertEqual(src.count("OpexAirPossibilityRouteChoices(catalog, lines, activePossibility,"), 3)
        cached = src[
            src.index("function OpexAirPossibilityRouteChoices"):
            src.index("function OpexAirMakePossibility")
        ]
        self.assertIn("local choices = OpexAirRouteChoices(catalog, possibility.airport,", cached)
        self.assertIn("return [OpexAirBestEquipment(catalog, airport, siteA, siteB, distance, lines,", src)
        self.assertIn("if (AIR_CAPITAL_FRONTIER)", src)
        self.assertIn("return OpexAirEquipmentFrontier(catalog, airport, siteA, siteB, distance, lines,", src)
        for token in ("sites[a], sites[b]", "hub, site", "hub1, hub2"):
            self.assertIn(token, src)
        self.assertIn("OpexAirAnyPlaneFitsAirportTypes", src)
        self.assertIn("if (!AIR_BEST_EQUIPMENT && plane.maxOrderDistance > 0", src)

    def test_best_equipment_enumerates_airports_without_combo_plane_decision(self):
        src = AIR.read_text(encoding="utf-8")
        catalog = CATALOG.read_text(encoding="utf-8")
        self.assertIn("airAirportChoices = null", catalog)
        self.assertIn("this.airAirportChoices.append(ap);", catalog)
        self.assertIn('("airAirportChoices" in catalog) && catalog.airAirportChoices != null', src)
        self.assertIn("combos.append({ kind = airportChoice.kind, airport = airportChoice });", src)
        self.assertIn("OpexAirLegacyProxyPlane", src)
        self.assertIn("if (!AIR_BEST_EQUIPMENT && bestPlan != null && bestPlan.airport.allowBig) break;", src)
        self.assertNotIn("if (bestPlan != null && bestPlan.airport.allowBig) break;", src)

    def test_c68_keeps_legacy_bounds_and_best_equipment_uses_envelope(self):
        src = AIR.read_text(encoding="utf-8")
        bounds = CANDIDATES.read_text(encoding="utf-8")
        catalog = CATALOG.read_text(encoding="utf-8")
        for token in ("PAIR_SEEN=", "PAIR_REJECT_CATALOG_RANGE=", "PAIR_RESCUABLE_BY_OTHER_PLANE=",
                      "DEMAND_SELECTED_DIFF=", "BOUND_ADDED="):
            self.assertIn(token, src)
        self.assertIn("function OpexComputeAirBoundsEnvelope", bounds)
        self.assertIn("AIR_BOUND_REGRET BOUND_CURRENT", bounds)
        self.assertIn("BOUND_ENVELOPE airMin=", bounds)
        self.assertIn("catalog.airBoundsLegacy", bounds)
        self.assertIn("local useEnvelope = AIR_BEST_EQUIPMENT && envelope.choices > 0", bounds)
        self.assertIn("local railAir = useEnvelope ? envelope.railAirOverlapMin : legacyRailAir", bounds)
        self.assertIn("local airMax = useEnvelope ? envelope.airMax : legacyAirMax", bounds)
        self.assertIn("OpexAirPairInLegacyBand", src)
        self.assertIn("AIR_EQUIPMENT_REGRET_PROBE || AIR_BEST_EQUIPMENT", catalog)

    def test_bench_parser_decodes_air_diagnostic_signs(self):
        chunks = {"SIGN": {
            1: {"name": "AR0|10|2|1|3|2"},
            2: {"name": "AR1|4|3|5|6|70"},
            3: {"name": "AR2|7|80"},
            4: {"name": "AR3|9"},
            5: {"name": "AR4|11|4|120"},
            6: {"name": "AB|80|60|200|240"},
            7: {"name": "AP|T=1000|S=400|E=500|TK=2"},
            8: {"name": "AO|1000|500"},
        }}
        stats = air_equipment_diagnostic_stats(chunks)
        self.assertEqual(stats["air_pair_seen"], 10)
        self.assertEqual(stats["air_proxy_range_rescued"], 2)
        self.assertEqual(stats["air_demand_cap_changed"], 6)
        self.assertEqual(stats["air_saved_projects"], 7)
        self.assertEqual(stats["air_saved_selected"], 1)
        self.assertEqual(stats["air_bound_added_pairs"], 11)
        self.assertEqual(stats["air_bound_min_lowered"], 1)
        self.assertEqual(stats["air_bound_max_raised"], 1)
        self.assertEqual(stats["air_plan_total_opcodes"], 1000)
        self.assertEqual(stats["air_plan_eval_opcodes"], 500)


if __name__ == "__main__":
    unittest.main()
