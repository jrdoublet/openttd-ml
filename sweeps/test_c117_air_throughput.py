"""Contrats C117 : sonde AIR passive de debit reel."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_settings
from diag_c117_air_throughput import enrich

INFO = ROOT / "ai" / "OpexAI" / "info.nut"
GLOBALS = ROOT / "ai" / "OpexAI" / "globals_pre.nut"
SETTINGS = ROOT / "ai" / "OpexAI" / "settings.nut"
MAIN = ROOT / "ai" / "OpexAI" / "main.nut"
PROBES = ROOT / "ai" / "OpexAI" / "probes.nut"
TASK_AIR = ROOT / "ai" / "OpexAI" / "task_air.nut"
COVERAGE = ROOT / "ai" / "OpexAI" / "air_coverage.nut"
BUILDER_AIR = ROOT / "ai" / "OpexAI" / "builder_air.nut"


class TestC117AirThroughput(unittest.TestCase):
    def test_unobserved_load_sentinel_cannot_prove_demand_limit(self):
        observation = enrich({
            "load_factor": -1, "trips": 0, "seat_legs": 0,
            "wait_a": 2, "wait_b": 4, "cap_avg": 100,
        })
        self.assertEqual(observation["limit_class"], "mixed_or_uncertain")

    def test_real_zero_load_with_flights_can_indicate_demand_limit(self):
        observation = enrich({
            "load_factor": 0, "trips": 3, "seat_legs": 300,
            "wait_a": 2, "wait_b": 4, "cap_avg": 100,
        })
        self.assertEqual(observation["limit_class"], "demand_limited")

    def test_high_observed_load_still_indicates_capacity_limit(self):
        observation = enrich({
            "load_factor": 0.95, "trips": 3, "seat_legs": 300,
            "wait_a": 30, "wait_b": 55, "cap_avg": 100,
        })
        self.assertEqual(observation["limit_class"], "capacity_limited")

    def test_non_finite_or_out_of_range_load_is_unknown(self):
        for load_factor in (float("nan"), float("inf"), 1.2):
            with self.subTest(load_factor=load_factor):
                observation = enrich({
                    "load_factor": load_factor, "trips": 3, "seat_legs": 300,
                    "wait_a": 2, "wait_b": 4, "cap_avg": 100,
                })
                self.assertEqual(observation["limit_class"], "mixed_or_uncertain")

    def test_builder_air_requires_coverage(self):
        self.assertIn('require("air_coverage.nut");', BUILDER_AIR.read_text(encoding="utf-8"))

    def test_probe_is_gated_from_main_loop(self):
        src = MAIN.read_text(encoding="utf-8")
        self.assertIn(
            "OpexC117AirThroughputStep(this._lines, this._catalog);",
            src,
        )
        self.assertIn("OpexC117AirThroughputStep(this._lines, this._catalog);", src)

    def test_shadow_is_reused_without_enabling_postbuild_catchment_probe(self):
        src = COVERAGE.read_text(encoding="utf-8")
        start = src.index("function OpexAirB9DemandShadow")
        end = src.index("function OpexAirCatchmentProbeEndpoint", start)
        block = src[start:end]
        self.assertNotIn("!AIR_CATCHMENT_PROBE && !C117_AIR_THROUGHPUT_PROBE", block)
        self.assertIn("plan.b9ShadowMonthly <- shadowMonthly;", block)
        self.assertIn("if (AIR_CATCHMENT_PROBE) OpexAirCatchmentLog", block)

    def test_delivered_load_uses_running_leg_only(self):
        src = PROBES.read_text(encoding="utf-8")
        start = src.index("function OpexC117AirThroughputStep")
        block = src[start:]
        self.assertIn("AIOrder.IsCurrentOrderPartOfOrderList(v)", block)
        self.assertIn("AIOrder.ResolveOrderPosition(v, AIOrder.ORDER_CURRENT)", block)
        self.assertIn("AIVehicle.GetState(v) == AIVehicle.VS_RUNNING", block)
        self.assertIn("unobservedTransitions", block)
        self.assertIn("legMoving", block)

    def test_probe_contains_no_vehicle_or_order_mutation(self):
        src = PROBES.read_text(encoding="utf-8")
        start = src.index("function OpexC117AirThroughputStep")
        end = src.index("function OpexC39Log", start)
        block = src[start:end]
        forbidden = (
            "BuildVehicle", "CloneVehicle", "SellVehicle", "StartStopVehicle",
            "SendVehicleToDepot", "AppendOrder", "InsertOrder", "RemoveOrder",
            "ShareOrders", "SkipToOrder",
        )
        for token in forbidden:
            self.assertNotIn(token, block)



if __name__ == "__main__":
    unittest.main()
