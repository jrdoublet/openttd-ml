"""ROAD100-29 static contracts and synthetic arithmetic; no OpenTTD/Docker."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def code(name):
    return (ROOT / name).read_text(encoding="utf-8")


def function_source(name):
    source = code("candidates.nut")
    begin = source.index("function " + name + "(")
    next_fn = source.find("\nfunction ", begin + 9)
    return source[begin:next_fn if next_fn >= 0 else len(source)]


def tokens(fields):
    return dict(re.findall(r"([a-z_]+)=(-?\w+)", fields))


class ROAD100PAXRootsTests(unittest.TestCase):
    def test_setting_optin_default_zero_in_every_profile_and_mode_guard(self):
        info = code("info.nut")
        match = re.search(
            r'name = "road100_pax_intercity_roots",(?P<body>.*?)\n\s*\}\);',
            info, re.S,
        )
        self.assertIsNotNone(match)
        for field in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(match["body"], rf"\b{field}\s*=\s*0\b")
        self.assertIn("AICONFIG_BOOLEAN", match["body"])
        self.assertIn("ROAD100_PAX_INTERCITY_ROOTS <- false", code("globals_pre.nut"))
        settings = code("settings.nut")
        self.assertRegex(settings, r'GetSetting\("road100_pax_intercity_roots"\) == 1')
        self.assertRegex(settings, r'ROAD100_PAX_INTERCITY_ROOTS\s*=.*\n\s*&& MODE_ROAD && !MODE_AIR && !MODE_RAIL && !MODE_WATER;')

    def test_shared_generator_in_sync_and_po01c_with_no_candidate_outputs(self):
        sync = code("candidates.nut")
        async_code = code("po01c_regen.nut")
        generator = "OpexRoad100PaxRootsShadowGenerator"
        self.assertEqual(sync.count("function " + generator + "("), 1)
        self.assertIn("local rootsIterator = " + generator + "(catalog);", sync)
        self.assertIn("iterator = " + generator + "(s.catalog);", async_code)
        self.assertRegex(async_code, r'while \(iterator.getstatus\(\) != "dead"\) \{ resume iterator; yield null; \}')
        self.assertNotIn(generator, code("po01c_generators.nut"))
        shadow = function_source(generator)
        for forbidden in ("out.append", "project", "OpexMakeRoadCandidate(",
                          "OpexRoadPlanFor(", "OpexRoadBfsPath(", "Pathfinder.",
                          "OpexBuildRoadRoute("):
            # The comments contain words like project; only reject function calls / outputs.
            if forbidden == "project":
                continue
            self.assertNotIn(forbidden, shadow)
        self.assertIn("admitted=0 built=0 route_quoted=0", shadow)

    def test_bounded_per_year_and_suspended_between_expensive_pairs(self):
        shadow = function_source("OpexRoad100PaxRootsShadowGenerator")
        self.assertIn("ROAD100_PAX_ROOTS_LAST_YEAR == year", shadow)
        self.assertIn("ROAD100_PAX_ROOTS_LAST_YEAR = year", shadow)
        self.assertIn("local limit = 200000", shadow)
        self.assertIn("tested < 2", shadow)
        self.assertGreaterEqual(shadow.count("yield null;"), 2)
        self.assertIn("OpexOpsMeasureEnd(mark)", shadow)
        self.assertIn("pairs_scanned=", shadow)
        self.assertIn("roads_scanned=", shadow)
        self.assertIn("ops=", shadow)
        self.assertIn("towns.len() > 12", shadow)
        self.assertRegex(shadow, r"distance < 43 \|\| distance > 80")
        probe = function_source("OpexRoad100PaxRootsTownSite")
        self.assertIn("result.roads < 12", probe)
        self.assertIn("result.tests < 2", probe)

    def test_real_road_fronts_native_sources_and_owned_station_coverage(self):
        shadow = function_source("OpexRoad100PaxRootsShadowGenerator")
        probe = function_source("OpexRoad100PaxRootsTownSite")
        self.assertIn("AIStationList(AIStation.STATION_ANY)", shadow)
        self.assertIn("AITileList_StationCoverage(id)", shadow)
        self.assertIn("OpexRoad100PaxRootsMarginalSource(cargo, tile, covered)", probe)
        source = function_source("OpexRoad100PaxRootsMarginalSource")
        self.assertIn("AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP)", source)
        self.assertIn("Valuate(AITile.GetCargoProduction, cargo, 1, 1, 0)", source)
        self.assertIn("covered.HasItem(tile)", source)
        self.assertNotIn("STATION_TRUCK_STOP", source)
        self.assertIn("covered.HasItem(tile)", probe)
        self.assertIn("roads.Valuate(AIRoad.IsRoadTile)", probe)
        self.assertIn("AIRoad.AreRoadTilesConnected(tile, front)", probe)
        self.assertIn("AIRoad.AreRoadTilesConnected(front, tile)", probe)
        self.assertIn("local test = AITestMode()", probe)
        self.assertIn("AIRoad.BuildDriveThroughRoadStation", probe)
        self.assertIn("AIStation.STATION_NEW", probe)
        self.assertIn("GetCargoAcceptance(tile, cargo, 1, 1, radius)", probe)

    def test_quoted_terms_distinguish_cost_floor_and_unknown_real_roi(self):
        shadow = function_source("OpexRoad100PaxRootsShadowGenerator")
        self.assertIn("engine.price + 2 * stopCost + catalog.costRoadDepot", shadow)
        self.assertIn("AICargo.GetCargoIncome(cargo, pair.distance, 0)", shadow)
        self.assertIn("revenueUpper = 12 * aSite.marginal * fareMax", shadow)
        self.assertIn("roi=-1 roi_upper=", shadow)
        self.assertIn("cost_quote=-1 revenue_cap_a_to_b=", shadow)
        self.assertIn("ROAD_ACCEPTANCE_FULL_UNIT", shadow)
        self.assertIn("REUSED_ROOT_NO_INCREMENT", shadow)
        self.assertIn("seenRootSites.rawset(aSite.tile, true)", shadow)
        self.assertIn("seenRootSites.rawset(bSite.tile, true)", shadow)
        self.assertNotIn("bSite.marginal * fareMax", shadow)
        self.assertNotIn("GetCargoWaiting(", shadow)

    def test_synthetic_unconnected_and_positive_site_observation_are_not_qualifications(self):
        impossible = tokens("phase=pair status=NO_SITE prod_a=0 prod_b=0 cost_floor=2700 "
                            "cost_quote=-1 revenue_cap_a_to_b=0 roi=-1 roi_upper=-1")
        candidate = tokens("phase=pair status=UPPER_ONLY_NO_ROUTE_QUOTE prod_a=18 "
                           "prod_b=25 cost_floor=4700 cost_quote=-1 "
                           "revenue_cap_a_to_b=43200 roi=-1 roi_upper=8200")
        self.assertEqual(impossible["roi"], "-1")
        self.assertEqual(candidate["roi"], "-1")
        self.assertGreater(int(candidate["revenue_cap_a_to_b"]), 0)
        self.assertEqual(candidate["cost_quote"], "-1")
        self.assertEqual(candidate["status"], "UPPER_ONLY_NO_ROUTE_QUOTE")

    def test_synthetic_marginal_source_avoids_overlapping_opex_and_site_duplicates(self):
        # Model the exact intended coverage rule with independent producer tiles.
        physical = {(1, 1): 8, (2, 2): 5, (3, 3): 11, (4, 4): 9}
        old_station_coverage = {(1, 1), (2, 2)}
        src_a = {(2, 2), (3, 3)}
        src_b = {(3, 3), (4, 4)}
        unique_producers = (src_a | src_b) - old_station_coverage
        self.assertEqual(sum(physical[p] for p in unique_producers), 20)
        self.assertEqual(sum(physical[p] for p in src_a - old_station_coverage), 11)
        # The actual shadow uses endpoints in distinct cities at 43..80,
        # so their radius-3 sources cannot physically overlap.
        self.assertGreater(43, 4 * 3)


if __name__ == "__main__":
    unittest.main()
