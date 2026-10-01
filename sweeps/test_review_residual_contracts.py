"""Regression tests for review residuals fixed on 2026-09-16."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air
from opex_projects_source import read_projects_source


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class ReviewResidualContractsTest(unittest.TestCase):
    def test_c77_targeted_rail_carries_fallback_cargo_into_next_mode(self):
        src = read_projects_source()
        start = src.index("function OpexGenerateModeProjects(")
        end = src.index("function OpexRegenerateModeProjects(", start)
        body = src[start:end]
        fallback = body.index("generated.freightCargo = freightCargo;")
        carry = body.index("projects.freightCargo = freightCargo;", fallback)
        stop = body.index("break;", carry)
        self.assertLess(fallback, carry)
        self.assertLess(carry, stop)

    def test_rail_depot_probe_precedes_demolition(self):
        src = _read("ai/OpexAI/builder_rail.nut")
        start = src.index("function OpexBuildDepot(")
        end = src.index("/* Une tentative ratee", start)
        body = src[start:end]
        probe = body.index("local testMode = AITestMode();")
        test_build = body.index("AIRail.BuildRailDepot(candidate, anchor)", probe)
        demolish = body.index("AITile.DemolishTile(candidate)", test_build)
        live_build = body.index("AIRail.BuildRailDepot(candidate, anchor)", demolish)
        self.assertLess(probe, test_build)
        self.assertLess(test_build, demolish)
        self.assertLess(demolish, live_build)

    def test_rail_order_failure_captures_immediate_error(self):
        src = _read("ai/OpexAI/builder_rail.nut")
        start = src.index("function OpexBuildTrains(")
        end = src.index("function OpexBuildLine(", start)
        body = src[start:end]
        order_a = body.index("local okA = AIOrder.AppendOrder")
        first_failure = body.index("if (!okA) {", order_a)
        order_b = body.index("local okB = AIOrder.AppendOrder", first_failure)
        second_failure = body.index("if (!okB || AIOrder.GetOrderCount(train) != 2)", order_b)
        self.assertLess(order_a, first_failure)
        self.assertLess(first_failure, order_b)
        self.assertIn("error = AIError.GetLastError()", body[first_failure:order_b])
        self.assertIn("error = !okB ? AIError.GetLastError() : 0", body[second_failure:second_failure + 260])

    def test_air_reused_hub_failure_does_not_read_stale_aierror(self):
        src = read_builder_air()
        start = src.index("function OpexBuildAirRoute(")
        body = src[start:]
        fail_a = body[body.index("if (airportA == null) {"):body.index("if (reuseB) {")]
        fail_b_start = body.index("if (airportB == null) {")
        fail_b = body[fail_b_start:body.index("local stationA =", fail_b_start)]
        for block, reuse, saved in (
            (fail_a, "reuseA", "airportErrorA"),
            (fail_b, "reuseB", "airportErrorB"),
        ):
            guarded = block.index(f"if (!{reuse}) {{")
            error = block.index(f"result.error = {saved};")
            self.assertLess(guarded, error)
            self.assertNotIn("AIError.GetLastError()", block)
            self.assertNotIn("AIError.GetLastErrorString()", block)

        build_a = body[body.index("local okA = levelA.ok && AIAirport.BuildAirport"):body.index("if (airportA == null) {")]
        build_b = body[body.index("local okB = levelB.ok && AIAirport.BuildAirport"):body.index("result.opcodes += budget.end", body.index("local okB = levelB.ok && AIAirport.BuildAirport"))]
        self.assertIn("airportErrorA = AIError.GetLastError();", build_a)
        self.assertIn("airportErrorB = AIError.GetLastError();", build_b)

    def test_air_share_orders_failure_never_starts_unordered_plane(self):
        src = read_builder_air()

        add_start = src.index("function OpexAirAddPlane(")
        add_end = src.index("function OpexAirRefleetCrashedPlane(", add_start)
        add = src[add_start:add_end]
        add_fail = add.index("if (!AIOrder.ShareOrders(extra, template)) {")
        add_start_vehicle = add.index("AIVehicle.StartStopVehicle(extra)")
        self.assertLess(add_fail, add_start_vehicle)
        self.assertIn("AIVehicle.SellVehicle(extra)", add[add_fail:add_start_vehicle])
        self.assertIn('result.reason = "ORDER"; return result;', add[add_fail:add_start_vehicle])

        route_start = src.index("function OpexBuildAirRoute(")
        route = src[route_start:]
        fleet_start = route.index("local built = [plane];")
        start_loop = route.index("foreach (aircraft in built)", fleet_start)
        fleet = route[fleet_start:start_loop]
        share_fail = fleet.index("if (AIVehicle.IsValidVehicle(extra) && !AIOrder.ShareOrders(extra, plane)) {")
        failure = fleet[share_fail:]
        self.assertIn("built.append(extra);", failure)
        self.assertRegex(failure, r"OpexAirRollback\(reuseA \? null : airportA, reuseB \? null : airportB, built,\s*"
                      r"OpexAirPairKey\(plan.siteA, plan.siteB\)\);")
        self.assertIn('result.reason = "ORDFAIL";', failure)
        self.assertIn("return result;", failure)

    def test_rail_vehicle_limit_fails_before_path_search_and_spend(self):
        builder = _read("ai/OpexAI/builder_rail.nut")
        task = _read("ai/OpexAI/task_rail.nut")
        helper_start = builder.index("function OpexRailVehicleSlotAvailable()")
        helper_end = builder.index("/* Execute la construction", helper_start)
        helper = builder[helper_start:helper_end]
        self.assertIn('"vehicle.max_trains"', helper)
        self.assertIn("AIGameSettings.GetValue(setting)", helper)
        self.assertIn("AIGroup.GetNumVehicles(AIGroup.GROUP_ALL, AIVehicle.VT_RAIL)", helper)
        self.assertIn("return used < cap;", helper)

        execute_start = builder.index("function OpexExecuteRailPlan(")
        execute_end = builder.index("function OpexBuildLine(", execute_start)
        execute = builder[execute_start:execute_end]
        guard = execute.index("if (!OpexRailVehicleSlotAvailable())")
        self.assertLess(guard, execute.index("local costs = AIAccounting();"))
        self.assertLess(guard, execute.index("budget.begin();"))
        self.assertIn('result.reason = "NOTRAIN";', execute[guard:guard + 250])

        attempt_start = task.index("function OpexAI::_tryBuildRailProject(")
        attempt_end = task.index("function OpexAI::_expandRailLines(", attempt_start)
        attempt = task[attempt_start:attempt_end]
        task_guard = attempt.index("if (!OpexRailVehicleSlotAvailable())")
        self.assertLess(task_guard, attempt.index("local need = candidate.capital"))
        self.assertLess(task_guard, attempt.index("this._startRailSearch("))
        self.assertIn('reason = "vehicle_limit"', attempt[task_guard:task_guard + 500])

    def test_rail_vehicle_limit_fails_before_spend(self):
        task = _read("ai/OpexAI/task_rail.nut")
        builder = _read("ai/OpexAI/builder_rail.nut")

        self.assertIn("if (!OpexRailVehicleSlotAvailable()) {", task)
        self.assertIn('reason = "vehicle_limit"', task)
        self.assertIn('local setting = "vehicle.max_trains";', builder)
        self.assertIn("AIGroup.GetNumVehicles(AIGroup.GROUP_ALL, AIVehicle.VT_RAIL)", builder)

        execute = builder[builder.index("function OpexExecuteRailPlan("):]
        guard = execute.index("if (!OpexRailVehicleSlotAvailable())")
        accounting = execute.index("local costs = AIAccounting()")
        first_station = execute.index("AIRail.BuildRailStation")
        self.assertLess(guard, accounting)
        self.assertLess(guard, first_station)
        self.assertIn('result.reason = "NOTRAIN";', execute[guard:accounting])

    def test_rail_flushes_discards_and_eu_covers_refleet(self):
        src = _read("ai/OpexAI/task_rail.nut")
        first_flush = src.index('OpexDecide("PROJECT_DISCARD"')
        first_choice = src.index('OpexDecide("PROJECT_CHOSEN"', first_flush)
        self.assertIn("passDiscards = [];", src[first_flush:first_choice])

        second_flush = src.index('OpexDecide("PROJECT_DISCARD"', first_choice)
        second_choice = src.index('OpexDecide("PROJECT_CHOSEN"', second_flush)
        self.assertIn("passDiscards = [];", src[second_flush:second_choice])
        self.assertIn("if (RAIL_EXPAND || RAIL_REFLEET) {", src)

    def test_life_scrap_checks_sell_vehicle_success(self):
        src = _read("ai/OpexAI/task_report.nut")
        start = src.index("function OpexAI::_scrapDeadLines(")
        end = src.index("function OpexAI::_scrapRetiredVehicles(", start)
        body = src[start:end]
        guard = body.index("if (AIVehicle.IsStoppedInDepot(v) && AIVehicle.SellVehicle(v)) {")
        streak = body.index("delete this._unprofitableStreaks[v];", guard)
        fallback = body.index("remaining.append(v);", streak)
        self.assertLess(guard, streak)
        self.assertLess(streak, fallback)

    def test_rail_start_failure_aborts_and_restops_trains(self):
        src = _read("ai/OpexAI/builder_rail.nut")
        # OpexBuildTrains
        bt_start = src.index("function OpexBuildTrains(")
        bt_end = src.index("function OpexTryBuildSignal(", bt_start)
        bt_body = src[bt_start:bt_end]
        bt_guard = bt_body.index("if (!AIVehicle.StartStopVehicle(train)) {")
        self.assertIn('failure = "START"', bt_body[bt_guard:])
        self.assertIn("AIVehicle.StartStopVehicle(train)", bt_body[bt_guard:])

        # OpexExecuteRailPlan
        exec_start = src.index("function OpexExecuteRailPlan(")
        exec_end = src.index("function OpexBuildLine(", exec_start)
        exec_body = src[exec_start:exec_end]
        exec_guard = exec_body.index("if (!AIVehicle.StartStopVehicle(train)) {")
        self.assertIn("trains.failed = true;", exec_body[exec_guard:])
        self.assertIn('trains.failure = "START";', exec_body[exec_guard:])
        self.assertIn("OpexRollback(tiles, planA, planB, depot, trains.rollbackVehicles);", exec_body[exec_guard:])

    def test_rail_second_train_cleans_rollback_vehicles_on_failure(self):
        src = _read("ai/OpexAI/builder_rail.nut")
        start = src.index("function OpexBuildSecondTrain(")
        body = src[start:]
        build_call = body.index("local newTrains = OpexBuildTrains(")
        fail_check = body.index("if (newTrains.failed || newTrains.built == 0) {", build_call)
        rollback = body.index("OpexRollback(null, null, null, null, newTrains.rollbackVehicles);", fail_check)
        self.assertLess(build_call, fail_check)
        self.assertLess(fail_check, rollback)

    def test_road_rollback_and_start_failure_contract(self):
        src = _read("ai/OpexAI/builder_road.nut")
        # OpexRoadRollback
        rb_start = src.index("function OpexRoadRollback(")
        rb_end = src.index("function OpexRoadTryJoinStop(", rb_start)
        rb_body = src[rb_start:rb_end]
        self.assertIn("local allSold = true;", rb_body)
        self.assertIn("if (!AIVehicle.SellVehicle(v)) allSold = false;", rb_body)
        self.assertIn("AIVehicle.SendVehicleToDepot(v);", rb_body)
        self.assertIn("if (!allSold) return;", rb_body)

        # OpexBuildRoadRoute
        route_start = src.index("function OpexBuildRoadRoute(")
        route_end = src.index("function OpexRoadRefleet(", route_start)
        route_body = src[route_start:route_end]
        start_check = route_body.index("if (!AIVehicle.StartStopVehicle(v)) {")
        rollback_call = route_body.index("OpexRoadRollback(stopA, stopB, depot, built, added);", start_check)
        self.assertIn("AIVehicle.StartStopVehicle(v)", route_body[start_check:rollback_call])

    def test_sign_truncates_name_to_31_chars(self):
        src = _read("ai/OpexAI/probes.nut")
        start = src.index("function OpexSign(")
        end = src.index("function OpexDecide(", start)
        body = src[start:end]
        truncate = body.index("if (name != null && name.len() > 31) name = name.slice(0, 31);")
        build_sign = body.index("AISign.BuildSign(anchor, name);", truncate)
        self.assertLess(truncate, build_sign)

    def test_ig_parser_does_not_claim_a_knapsack_truncation(self):
        path = ROOT / "sweeps" / "opex_full_campaign.py"
        spec = importlib.util.spec_from_file_location("opex_full_campaign_review_test", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        rows, decisions = module.parse_project_portfolios(["IG|70|12|8|1|1|0"])
        self.assertEqual(decisions, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["selection_not_exact"], 1)
        self.assertIsNone(rows[0]["knapsack_truncated"])

    def test_legacy_3y_bench_uses_h3_decoder_for_n_vehicles(self):
        src = _read("sweeps/bench_1v1_3y_10seeds.py")
        self.assertIn("from physical_counters import decode_vehicles", src)
        self.assertIn('veh_dec = decode_vehicles(chunks.get("VEHS"), target_owner=0)', src)
        self.assertIn('"n_vehicles": veh_dec["primary_vehicles_count"] if veh_dec["chunk_valid"] else None', src)
        self.assertNotIn('"n_vehicles": vehs["n_units"]', src)

        from sweeps import bench_1v1_3y_10seeds as bench

        fixture = json.loads(
            (ROOT / "sweeps" / "fixtures" / "c66_control_fixture_15_3.json").read_text(encoding="utf-8")
        )
        record = bench.keep({
            "chunks": fixture["chunks"],
            "experiment": {"bench_arm": "OpexAI", "seed": 42},
            "date": fixture["metadata"]["date"],
        })[0]
        self.assertTrue(record["vehs_chunk_valid"])
        self.assertEqual(record["n_vehicles"], 21)

        invalid = bench.keep({
            "chunks": {"PLYR": {}, "VEHS": None, "STNN": {}},
            "experiment": {"bench_arm": "OpexAI", "seed": 1},
            "date": "1970-12-01",
        })[0]
        self.assertFalse(invalid["vehs_chunk_valid"])
        self.assertIsNone(invalid["n_vehicles"])


if __name__ == "__main__":
    unittest.main()
