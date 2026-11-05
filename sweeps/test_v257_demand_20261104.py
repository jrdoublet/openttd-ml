"""V257 demand default enabled: wiring, forecast, depot consistency, byte-exact OFF."""
import hashlib
import sys
import unittest
from pathlib import Path

SWEEPS = Path(__file__).resolve().parent
sys.path.insert(0, str(SWEEPS))
from v257_demand_off import off_source  # noqa: E402

AI = SWEEPS.parent / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf8")


class V257Demand(unittest.TestCase):
    def test_setting_is_enabled_by_default_at_all_difficulties(self):
        block = read("info.nut").split('name = "v257_demand"', 1)[1].split('});', 1)[0]
        self.assertIn("min_value = 0, max_value = 1", block)
        self.assertIn("easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1", block)
        self.assertIn("(default 1 since 2026-11-05, user decision)", block)
        self.assertEqual(read("globals_pre.nut").count("V257_DEMAND <- false;"), 1)
        self.assertEqual(read("settings.nut").count('GetSetting("v257_demand")'), 1)

    def test_forecast_uses_production_and_predicts_loading_rating(self):
        code = read("task_v257.nut")
        function = code.split("function OpexV257UncensoredMonthly(", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("AIIndustry.GetLastMonthProduction(industry, line.cargo)", function)
        self.assertIn("AIStation.GetStationID(AIVehicle.GetLocation(vehicle)) == sourceStation", function)
        self.assertIn("predictedRating < 75", function)
        self.assertIn("production.tofloat() * predictedRating / (100.0 * vehicles.len())", function)
        self.assertNotIn("annualDelivered", function)
        self.assertEqual(code.count("if (V257_DEMAND) monthly = OpexV257UncensoredMonthly("), 2)

    def test_tie_break_prefers_capacity_only_on(self):
        code = read("task_v257.nut")
        self.assertIn("V257_DEMAND ? (number * wagon.capacity > best.wagons * best.wagon.capacity", code)
        self.assertIn(": plan.price < best.price))) best = plan;", code)

    def test_off_projection_is_byte_exact_and_idempotent(self):
        for name in ("globals_pre.nut", "settings.nut", "info.nut", "task_v257.nut"):
            with self.subTest(name=name):
                current = read(name)
                projected = off_source(name, current)
                self.assertEqual(off_source(name, projected), projected)
                if name == "task_v257.nut":
                    # The file is otherwise unchanged by this layer except RAIL-FILL.
                    from rail_fill_off import off_source as fill_off
                    from subprocess import check_output
                    baseline = check_output(["git", "show", "HEAD:ai/OpexAI/task_v257.nut"], cwd=AI.parent.parent).decode("utf8")
                    # HEAD peut désormais contenir V257-DEMAND après sa promotion.
                    self.assertEqual(fill_off(name, projected), fill_off(name, off_source(name, baseline)))

    def test_partial_projection_fails_closed(self):
        source = read("task_v257.nut").replace("predictedRating < 75", "predictedRating < 74")
        with self.assertRaises(AssertionError):
            off_source("task_v257.nut", source)


if __name__ == "__main__":
    unittest.main()
