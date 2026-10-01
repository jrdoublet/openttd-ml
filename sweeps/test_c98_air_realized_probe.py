import unittest
from pathlib import Path
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air


ROOT = Path(__file__).resolve().parents[1]
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
REPORT = (ROOT / "ai" / "OpexAI" / "task_report.nut").read_text(encoding="utf-8")
AIR = read_builder_air()


class C98AirRealizedProbeTests(unittest.TestCase):
    def test_setting_is_passive_by_default(self):
        self.assertIn("C98_AIR_REALIZED_PROBE <- false;", GLOBALS)
        start = INFO.index('name = "c98_air_realized_probe"')
        snippet = INFO[start:start + 420]
        self.assertIn("easy_value = 0", snippet)
        self.assertIn("medium_value = 0", snippet)
        self.assertIn("hard_value = 0", snippet)
        self.assertIn("custom_value = 0", snippet)
        self.assertIn(
            'C98_AIR_REALIZED_PROBE = AIController.GetSetting("c98_air_realized_probe") != 0;',
            SETTINGS,
        )

    def test_probe_is_nested_under_existing_decision_log_gate(self):
        revenue = REPORT.index('OpexDecide("LINE_REVENUE"')
        probe = REPORT.index('if (C98_AIR_REALIZED_PROBE && lMode == "air") {')
        outer = REPORT.rfind("if (DECISION_LOG) {", 0, revenue)
        self.assertGreaterEqual(outer, 0)
        self.assertLess(outer, revenue)
        self.assertLess(revenue, probe)
        self.assertNotIn("C98_AIR_REALIZED_PROBE", AIR)

    def test_probe_logs_prediction_and_realized_economics(self):
        for field in (
            "pred_p=", "real_p=", "pred_r=", "real_r=", "pred_run=", "real_run=",
            "pred_amort=", "pred_n=", "real_n=", "pred_carried=", "pred_days=", "monthly_pax=",
        ):
            self.assertIn(field, REPORT)

    def test_probe_logs_engine_rating_and_utilization_signals(self):
        for field in (
            "engine=", "engine_name=", "distance=", "pred_capacity=", "pred_rating=",
            "rating_a=", "rating_b=", "pax_load=", "pax_cap=", "mail_load=", "mail_cap=",
            "moving=", "depot=", "speed_sum=", "speed_n=", "engine_speed=",
            "engine_capacity=", "engine_price=", "engine_running=", "plane_speed_div=",
            "arm=", "station_a=", "station_b=", "live_routes_a=", "live_routes_b=",
            "pax_wait_a=", "pax_wait_b=", "mail_wait_a=", "mail_wait_b=",
        ):
            self.assertIn(field, REPORT)

    def test_probe_only_persists_extra_line_metadata_when_enabled(self):
        task_air = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")
        self.assertIn("C84_AIR_TARGET_FLEET || C121_AIR_ECONOMICS || V92_AIR_SERVICE_CHOICE || C98_AIR_REALIZED_PROBE", task_air)
        self.assertIn("if (C98_AIR_REALIZED_PROBE) {", task_air)
        self.assertIn(".c98Arm <-", task_air)

    def test_profit_source_is_vehicle_api_not_estimate(self):
        self.assertIn("local prof = AIVehicle.GetProfitLastYear(v);", REPORT)
        self.assertIn("runCost += AIVehicle.GetRunningCost(v);", REPORT)
        self.assertIn("local realRevenue = profit + runCost;", REPORT)

    def test_cadence_is_not_falsely_claimed_as_observed(self):
        self.assertIn("NoAI n'expose pas le nombre annuel de", REPORT)
        self.assertIn("pred_trips_pm=", REPORT)
        self.assertIn("moving/load sont donc des indices d'utilisation", REPORT)


if __name__ == "__main__":
    unittest.main()
