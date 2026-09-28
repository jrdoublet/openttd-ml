"""Contrats C117 : sonde AIR passive de debit reel."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_settings

INFO = ROOT / "ai" / "OpexAI" / "info.nut"
GLOBALS = ROOT / "ai" / "OpexAI" / "globals_pre.nut"
SETTINGS = ROOT / "ai" / "OpexAI" / "settings.nut"
MAIN = ROOT / "ai" / "OpexAI" / "main.nut"
PROBES = ROOT / "ai" / "OpexAI" / "probes.nut"
TASK_AIR = ROOT / "ai" / "OpexAI" / "task_air.nut"
BUILDER_AIR = ROOT / "ai" / "OpexAI" / "builder_air.nut"
RUNNER = ROOT / "sweeps" / "run_c117_air_throughput.py"


class TestC117AirThroughput(unittest.TestCase):
    def test_default_off_and_loaded_once(self):
        defaults = parse_ai_settings(INFO)
        self.assertEqual(defaults["c117_air_throughput_probe"], 0)
        self.assertIn("C117_AIR_THROUGHPUT_PROBE <- false;", GLOBALS.read_text(encoding="utf-8"))
        self.assertIn(
            'C117_AIR_THROUGHPUT_PROBE = AIController.GetSetting("c117_air_throughput_probe") != 0;',
            SETTINGS.read_text(encoding="utf-8"),
        )

    def test_probe_is_gated_from_main_loop(self):
        src = MAIN.read_text(encoding="utf-8")
        self.assertIn(
            "if (C117_AIR_THROUGHPUT_PROBE) OpexC117AirThroughputStep(this._lines, this._catalog);",
            src,
        )

    def test_both_air_build_paths_store_probe_context(self):
        src = TASK_AIR.read_text(encoding="utf-8")
        self.assertGreaterEqual(src.count("c117Arm <-"), 2)
        self.assertGreaterEqual(src.count("c117ShadowMonthly <-"), 2)
        self.assertGreaterEqual(src.count("C117_AIR_THROUGHPUT_PROBE"), 2)

    def test_shadow_is_reused_without_enabling_postbuild_catchment_probe(self):
        src = BUILDER_AIR.read_text(encoding="utf-8")
        start = src.index("function OpexAirB9DemandShadow")
        end = src.index("function OpexAirCatchmentProbeEndpoint", start)
        block = src[start:end]
        self.assertIn("!AIR_CATCHMENT_PROBE && !C117_AIR_THROUGHPUT_PROBE", block)
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

    def test_runner_only_keeps_tail_and_latest_cumulative_output(self):
        src = RUNNER.read_text(encoding="utf-8")
        self.assertIn("final_date = date(1970, 1, 1) + timedelta(days=days)", src)
        self.assertIn("final_date - timedelta(days=31)", src)
        self.assertIn("latest_by_seed", src)
        self.assertIn('("c115_air_c100_capital_replay", 1)', src)


if __name__ == "__main__":
    unittest.main()
