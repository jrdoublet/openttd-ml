"""Regression tests for review residuals fixed on 2026-09-16."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class ReviewResidualContractsTest(unittest.TestCase):
    def test_air_share_orders_failure_never_starts_unordered_plane(self):
        src = _read("ai/OpexAI/builder_air.nut")

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
        self.assertIn("OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, built);", failure)
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
