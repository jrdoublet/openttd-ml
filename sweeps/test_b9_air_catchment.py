"""Contrats B9/G4 : géométrie STNN et sonde AIR strictement passive."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

try:
    from bench_1v1_5y_20seeds import _station_route_index
except ImportError as exc:  # openttdlab absent hors du conteneur openttd-lab
    raise unittest.SkipTest(f"harnais indisponible hors Docker : {exc}")
from campaign_freeze import parse_ai_settings
from diag_b9_air_catchment import _in_expanded_rect, pair_builds

INFO = ROOT / "ai" / "OpexAI" / "info.nut"
GLOBALS = ROOT / "ai" / "OpexAI" / "globals_pre.nut"
SETTINGS = ROOT / "ai" / "OpexAI" / "settings.nut"
PROBES = ROOT / "ai" / "OpexAI" / "probes.nut"
BUILDER = ROOT / "ai" / "OpexAI" / "builder_air.nut"
TASK_AIR = ROOT / "ai" / "OpexAI" / "task_air.nut"
FIXTURE = ROOT / "sweeps" / "fixtures" / "c66_control_fixture_15_3.json"

class TestB9AirCatchment(unittest.TestCase):
    def test_probe_is_default_off_and_loaded_once(self):
        defaults = parse_ai_settings(INFO)
        self.assertEqual(defaults["probe_events"], 0)
        self.assertEqual(defaults["b9_air_catchment_probe"], 0)
        self.assertEqual(defaults["b9_air_demand_shadow"], 0)
        self.assertIn("AIR_CATCHMENT_PROBE <- false;", GLOBALS.read_text(encoding="utf-8"))
        self.assertIn(
            "AIR_CATCHMENT_PROBE = probeEvents || b9CatchmentProbe;",
            SETTINGS.read_text(encoding="utf-8"),
        )

    def test_runner_enables_only_dedicated_b9_probe(self):
        runner = (ROOT / "sweeps" / "run_b9_air_catchment_5x6.py").read_text(encoding="utf-8")
        self.assertIn('SETTINGS = (("b9_air_catchment_probe", 1),)', runner)
        self.assertNotIn('("probe_events", 1)', runner)

    def test_demand_shadow_is_post_decision_and_default_off(self):
        builder = BUILDER.read_text(encoding="utf-8")
        task = TASK_AIR.read_text(encoding="utf-8")
        selected = task.index("local buildPlan = buildChoice.plan;")
        shadow = task.index("OpexAirB9DemandShadow(this._catalog, buildPlan);")
        build = task.index("OpexBuildAirRoute(this._catalog, this._budget, buildPlan")
        self.assertGreater(shadow, selected)
        self.assertLess(shadow, build)
        self.assertIn("OpexAirB9DemandShadow(this._catalog, plan);", task)
        self.assertIn("if (!B9_AIR_DEMAND_SHADOW || !AIR_CATCHMENT_PROBE", builder)
        self.assertIn("AIR_DEMAND_SHADOW", builder)
        runner = (ROOT / "sweeps" / "run_b9_air_catchment_5x6.py").read_text(encoding="utf-8")
        self.assertIn('"--demand-shadow"', runner)

    def test_demand_shadow_uses_square_station_catchment_geometry(self):
        src = BUILDER.read_text(encoding="utf-8")
        start = src.index("function OpexAirB9TownUnionMonthly")
        end = src.index("function OpexAirB9DemandShadowEndpoint", start)
        shadow = src[start:end]
        self.assertIn("OpexAirB9TileInExpandedRect(", shadow)
        self.assertNotIn("AIMap.DistanceManhattan(tile, stop) <= busRadius", shadow)

    def test_probe_airport_only_uses_square_catchment_not_manhattan(self):
        src = BUILDER.read_text(encoding="utf-8")
        start = src.index("function OpexAirCatchmentProbeEndpoint")
        end = src.index('OpexAirCatchmentLog("AIR_CATCHMENT_ENDPOINT"', start)
        probe = src[start:end]
        self.assertIn("OpexAirB9TileInExpandedRect(", probe)
        self.assertIn("townCenterInAirport", probe)
        self.assertNotIn(
            "OpexAirDistanceToRect(coverageTile, airportTile, w, h) <= airportRadius",
            probe,
        )

    def test_python_geometry_distinguishes_distance_from_catchment(self):
        # 6x6 airport at (10,10), radius 5: (5,5) is in the square catchment
        # even though its Manhattan distance to the rectangle is 10.
        map_width = 64
        anchor = 10 + 10 * map_width
        corner = 5 + 5 * map_width
        self.assertEqual(
            __import__("diag_b9_air_catchment")._rect_distance(
                corner, anchor, 6, 6, map_width
            ),
            10,
        )
        self.assertTrue(_in_expanded_rect(corner, anchor, 6, 6, 5, map_width))

    def test_shadow_pairs_with_following_successful_build(self):
        shadow = {"kind": "AIR_DEMAND_SHADOW", "arm": "newpair", "shadow_monthly": 100,
                  "town_a": 2, "anchor_a": 100, "town_b": 3, "anchor_b": 200}
        endpoint_a = {"kind": "AIR_CATCHMENT_ENDPOINT", "endpoint": "A",
                      "town": 2, "airport_tile": 100}
        endpoint_b = {"kind": "AIR_CATCHMENT_ENDPOINT", "endpoint": "B",
                      "town": 3, "airport_tile": 200}
        build = {"kind": "AIR_CATCHMENT_BUILD", "arm": "newpair"}
        builds, orphan_endpoints, orphan_builds = pair_builds(
            [shadow, endpoint_a, endpoint_b, build]
        )
        self.assertEqual(orphan_endpoints, 0)
        self.assertEqual(orphan_builds, 0)
        self.assertEqual(len(builds), 1)
        self.assertIs(builds[0]["shadow"], shadow)
        self.assertEqual(builds[0]["endpoints"], [endpoint_a, endpoint_b])

    def test_shadow_does_not_pair_to_different_route(self):
        wrong = {"kind": "AIR_DEMAND_SHADOW", "arm": "hubsite", "shadow_monthly": 100,
                 "town_a": 26, "anchor_a": 61002, "town_b": 11, "anchor_b": 10913}
        right = {"kind": "AIR_DEMAND_SHADOW", "arm": "hubhub", "shadow_monthly": 90,
                 "town_a": 2, "anchor_a": 23338, "town_b": 36, "anchor_b": 40157}
        endpoint_a = {"kind": "AIR_CATCHMENT_ENDPOINT", "endpoint": "A",
                      "town": 2, "airport_tile": 23338}
        endpoint_b = {"kind": "AIR_CATCHMENT_ENDPOINT", "endpoint": "B",
                      "town": 36, "airport_tile": 40157}
        build = {"kind": "AIR_CATCHMENT_BUILD", "arm": "hubhub"}
        builds, _, _ = pair_builds([wrong, right, endpoint_a, endpoint_b, build])
        self.assertIs(builds[0]["shadow"], right)

    def test_probe_has_dedicated_logger(self):
        probes = PROBES.read_text(encoding="utf-8")
        start = probes.index("function OpexAirCatchmentLog")
        self.assertIn("if (!AIR_CATCHMENT_PROBE) return;", probes[start:start + 500])

    def test_probe_runs_after_success_and_before_reconciliation(self):
        src = BUILDER.read_text(encoding="utf-8")
        probe = src.index('OpexAirCatchmentLog("AIR_CATCHMENT_BUILD"')
        reconcile = src.index("OpexAirReconcileActualBuild(catalog, plan, result);")
        success = src.index("result.ok = true;", src.index("function OpexBuildAirRoute"))
        self.assertLess(success, probe)
        self.assertLess(probe, reconcile)
        self.assertIn("joinedMonthlyPaxA = 0", src)
        self.assertIn("joinedMonthlyPaxB = 0", src)

    def test_probe_keeps_measurement_dimensions_separate(self):
        src = BUILDER.read_text(encoding="utf-8")
        for token in (
            "airport_pax_prod=", "union_pax_prod=", "airport_mail_prod=",
            "union_mail_prod=", "base_source=", "base_monthly=",
            "reserve_stop_cost=", "actual_stop_cost=", "overlap_overcount_pax=",
            "model_joined_pax=", "model_error_pax=", "probe_ops=",
            "town_pax_month=", "town_pax_tiles=", "town_airport_pax_tiles=",
            "airport_pax_month_est=", "town_mail_month=", "town_mail_tiles=",
            "airport_mail_month_est=", "predicted_annual_profit=",
            "joined_marginal_pax_tiles=", "route_div_a=", "route_div_b=",
        ):
            self.assertIn(token, src)

    def test_station_index_exposes_airport_geometry_from_stnn(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        chunks = None
        stack = [fixture]
        while stack and chunks is None:
            current = stack.pop()
            if not isinstance(current, dict):
                continue
            if "STNN" in current:
                chunks = current
                break
            stack.extend(value for value in current.values() if isinstance(value, dict))
        self.assertIsNotNone(chunks)
        stations = _station_route_index(chunks)
        airports = [s["airport"] for s in stations.values() if s.get("airport") is not None]
        self.assertTrue(airports)
        sample = airports[0]
        for key in ("tile", "width", "height", "type"):
            self.assertIn(key, sample)
        self.assertIsInstance(sample["width"], int)
        self.assertGreater(sample["width"], 0)

    def test_air_default_planning_uses_named_proxy_not_duplicated_literal(self):
        src = BUILDER.read_text(encoding="utf-8")
        self.assertNotIn("* 22", src)
        self.assertGreaterEqual(src.count("TOWN_CATCHMENT_SHARE_PCT"), 4)
        self.assertIn(
            "local monthlyPax = ((popA + popB) * TOWN_CATCHMENT_SHARE_PCT) / 100;",
            src,
        )
        self.assertIn("town_population_proxy", src)

    def test_joined_stop_reconciliation_uses_union_marginal(self):
        src = BUILDER.read_text(encoding="utf-8")
        self.assertIn("function OpexAirJoinedMarginalProduction", src)
        self.assertIn("joinedRawMonthlyPaxA = 0", src)
        self.assertIn("result.joinedRawMonthlyPaxA = joinedA.monthlyPax;", src)
        self.assertIn("result.joinedMonthlyPaxA = OpexAirJoinedMarginalProduction(", src)
        self.assertIn(
            'local joinedMonthly = OPEX_AIR_PLAN_PAD && ("joinedMonthlyPax" in result)',
            src,
        )
        ai = BUILDER.parent
        self.assertIn("OPEX_AIR_PLAN_PAD <- false;", (ai / "globals_pre.nut").read_text(encoding="utf-8"))
        self.assertIn("OPEX_AIR_PLAN_PAD = false;", (ai / "settings.nut").read_text(encoding="utf-8"))
        reserve = src[src.index("function OpexAirReserveJoinedStops"):src.index(
            "function OpexAirAddPlane"
        )]
        self.assertIn("plan.joinedStopReserve <- 0;", reserve)
        self.assertNotIn("economics.capital +=", reserve)

if __name__ == "__main__":
    unittest.main()
