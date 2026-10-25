"""Contrat V93 : pas de plancher a 600 hab. pour un grand aeroport, fige actif par V263b."""
from pathlib import Path
import unittest
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air
from opex_projects_source import read_projects_source

ROOT = Path(__file__).resolve().parents[1]
BUILDER = read_builder_air()
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
CATALOG = (ROOT / "ai" / "OpexAI" / "catalog.nut").read_text(encoding="utf-8")
PROJECTS = read_projects_source()


def function_body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start:pos + 1]
    raise AssertionError(signature)


class V93AirportNoPopFloorTests(unittest.TestCase):
    def test_setting_defaults_off_and_count_matches_info(self):
        self.assertNotIn("V93_AIRPORT_NO_POP_FLOOR", GLOBALS)
        self.assertIn("V93_AIRPORT_MIN_POP <- 100;", GLOBALS)
        self.assertNotIn('name = "v93_airport_no_pop_floor"', INFO)
        self.assertNotIn('GetSetting("v93_airport_no_pop_floor")', SETTINGS)

    def test_large_floor_is_a_boolean_and_the_sanity_floor_is_behind_the_setting(self):
        sites = function_body(BUILDER, "function OpexAirPlansFindSites(")
        self.assertNotIn("town_pop_small", sites)
        self.assertLess(sites.index("towns[i].pop < V93_AIRPORT_MIN_POP"), sites.index("OpexAirFindSite("))
        hubs = function_body(BUILDER, "function OpexAirPlansDiscoverHubs(")
        self.assertNotIn('combo.kind == "large" && towns[i].pop < 600', hubs)
        self.assertIn("V93_AIRPORT_MIN_POP", hubs)

    def test_town_pool_ranking_is_unchanged(self):
        pool = function_body(BUILDER, "function OpexAirTownPoolLimit(")
        ranked = function_body(BUILDER, "function OpexAirSortedTowns(")
        prepare = function_body(BUILDER, "function OpexAirPlansPrepare(")
        self.assertNotIn("V93_", pool)
        self.assertNotIn("600", pool)
        self.assertIn("towns.len()", pool)
        self.assertNotIn("V93_", ranked)
        self.assertIn("town.pop", ranked)
        self.assertIn("OpexAirSortedTowns(catalog.towns)", prepare)
        self.assertIn("OpexAirTownPoolLimit(towns)", prepare)
        self.assertNotIn("V93_AIRPORT", prepare)

    def test_small_combo_is_scanned_after_a_large_plan_only_when_enabled(self):
        plans = function_body(BUILDER, "function OpexAirPlans(")
        closing = function_body(BUILDER, "function OpexAirPlansCompleteCombo(")
        self.assertIn("OpexAirPlansCompleteCombo(ctx, comboIndex, combo)", plans)
        self.assertNotIn("V93_AIRPORT_NO_POP_FLOOR", closing)
        helper = closing.index("OpexAirV93NextSmallCombo(ctx.combos, comboIndex)")
        self.assertGreater(helper, 0)
        self.assertNotIn(
            "if (bestPlan != null && bestPlan.airport.allowBig) break;",
            closing,
        )
        self.assertIn("function OpexAirV93NextSmallCombo(", BUILDER)
        pairs = function_body(BUILDER, "function OpexAirPlansNewPairs(")
        self.assertIn("OpexAirStoreRoutePlan(projects, plan, routeChoice, bestPlan)", pairs)
        self.assertIn("profit_nonpositive", pairs)
        self.assertIn("foreach (plan in airPlans)", PROJECTS)
        self.assertIn("OpexProjectFromAir(catalog, plan, airOpsPerPlan)", PROJECTS)

    def test_big_planes_still_cannot_use_a_small_airport(self):
        refresh = function_body(CATALOG, "function OpexCatalog::_refreshAir()")
        large, small = refresh.split("// 2. Combo Petit Aeroport", 1)
        self.assertIn("if (!AIAirport.IsValidAirportType(choice.type)) continue;", small)
        self.assertIn("if (planeType != AIAirport.PT_SMALL_PLANE) continue;", small)
        self.assertIn('kind = "small"', small)
        self.assertNotIn("if (planeType != AIAirport.PT_SMALL_PLANE) continue;", large)
        accepts = function_body(BUILDER, "function OpexAirAirportAcceptsPlane(")
        self.assertIn("if (planeType == AIAirport.PT_SMALL_PLANE) return true;", accepts)
        self.assertIn(
            "return airportType != AIAirport.AT_SMALL && airportType != AIAirport.AT_COMMUTER;",
            accepts,
        )


if __name__ == "__main__":
    unittest.main()
