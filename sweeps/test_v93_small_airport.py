"""Contrat V93 : pas de plancher a 600 hab. pour un grand aeroport, defaut 0."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
CATALOG = (ROOT / "ai" / "OpexAI" / "catalog.nut").read_text(encoding="utf-8")
PROJECTS = (ROOT / "ai" / "OpexAI" / "projects.nut").read_text(encoding="utf-8")


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
        self.assertIn("V93_AIRPORT_NO_POP_FLOOR <- false;", GLOBALS)
        self.assertIn("V93_AIRPORT_MIN_POP <- 100;", GLOBALS)
        self.assertNotIn("V93_SMALL_AIRPORT_TOWNS", GLOBALS)
        self.assertNotIn("V93_SMALL_AIRPORT_MIN_POP", GLOBALS)
        self.assertEqual(INFO.count("AddSetting("), 82)
        start = INFO.index('name = "v93_airport_no_pop_floor"')
        block = INFO[start:INFO.index("});", start)]
        for token in (
            "min_value = 0",
            "max_value = 1",
            "easy_value = 0",
            "medium_value = 0",
            "hard_value = 0",
            "custom_value = 0",
        ):
            self.assertIn(token, block)
        self.assertNotIn("v93_airport_min_pop", INFO)
        self.assertNotIn("v93_small_airport_towns", INFO)
        self.assertIn(
            'V93_AIRPORT_NO_POP_FLOOR = AIController.GetSetting("v93_airport_no_pop_floor") != 0;',
            SETTINGS,
        )
        self.assertNotIn("v93_small_airport_towns", SETTINGS)

    def test_large_floor_is_a_boolean_and_the_sanity_floor_is_behind_the_setting(self):
        sites = function_body(BUILDER, "function OpexAirPlansFindSites(")
        origin = sites.index("outcome=origin_served")
        large = sites.index(
            '!V93_AIRPORT_NO_POP_FLOOR && combo.kind == "large" && towns[i].pop < 600'
        )
        floor = sites.index(
            "V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < V93_AIRPORT_MIN_POP"
        )
        find = sites.index("OpexAirFindSite(")
        flag = sites.index("outcome=site v93=1 pop=")
        plain = sites.index('outcome=site");')
        self.assertLess(origin, large)
        self.assertLess(large, floor)
        self.assertLess(floor, find)
        self.assertLess(find, flag)
        self.assertLess(flag, plain)
        self.assertIn("outcome=town_pop_small", sites)
        self.assertIn("outcome=town_pop_v93", sites)
        self.assertNotIn('else if (combo.kind == "large" && towns[i].pop < 600)', sites)
        self.assertNotIn("V93_SMALL_AIRPORT", sites)

        hubs = function_body(BUILDER, "function OpexAirPlansDiscoverHubs(")
        self.assertLess(
            hubs.index(
                '!V93_AIRPORT_NO_POP_FLOOR && combo.kind == "large" && towns[i].pop < 600'
            ),
            hubs.index("V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < V93_AIRPORT_MIN_POP"),
        )
        self.assertLess(
            hubs.index("V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < V93_AIRPORT_MIN_POP"),
            hubs.index('combo.kind == "small" && towns[i].pop >= 2500'),
        )
        self.assertIn("outcome=site v93=1 pop=", hubs)
        self.assertNotIn('if (combo.kind == "large" && towns[i].pop < 600) continue', hubs)

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
        guard = plans.index("if (!V93_AIRPORT_NO_POP_FLOOR) break;")
        helper = plans.index("OpexAirV93NextSmallCombo(ctx.combos, comboIndex)")
        self.assertLess(guard, helper)
        self.assertNotIn(
            "if (bestPlan != null && bestPlan.airport.allowBig) break;",
            plans,
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
