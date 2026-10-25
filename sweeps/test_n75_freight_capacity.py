"""N75-CAP : contrats de saturee persistante, finance et rechargement.

Ces tests statiques ne compilent pas Squirrel : smoke moteur obligatoire.
"""
import re
import unittest
from pathlib import Path

from test_b5_rail_persistence import function_body

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class N75FreightCapacityContracts(unittest.TestCase):
    def test_flag_is_off_for_every_difficulty_and_only_read_once(self):
        info = source("info.nut")
        settings = re.search(
            r'AddSetting\(\{\s*name = "n75_freight_capacity",(.*?)\}\);',
            info, re.S
        ).group(1)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(settings, rf"{level}_value\s*=\s*0\b")
        self.assertIn("min_value = 0, max_value = 1", settings)
        self.assertEqual(source("settings.nut").count('GetSetting("n75_freight_capacity")'), 1)
        self.assertIn("N75_FREIGHT_CAPACITY <- 0;", source("globals_pre.nut"))
        self.assertIn('require("task_n75_freight.nut")', source("main.nut"))
        self.assertIn("V284_RAIL_GROWTH > 0 || N75_FREIGHT_CAPACITY > 0", source("task_rail.nut"))
        self.assertIn("year >= OPEX_START_YEAR + V284_RAIL_GROWTH", source("task_rail.nut"))

    def test_three_spaced_samples_and_date_guard(self):
        observe = function_body(source("task_n75_freight.nut"), "function OpexN75FreightObserve(")
        for required in (
            "AIDate.GetYear(date) < OPEX_START_YEAR + 2",
            "waiting < requiredWaiting",
            "date - observation.last >= 60",
            "observation.count >= 3 && date - observation.first >= 120",
            "observation.vehicle != vehicle",
            "observation.wagons != wagons",
            "date - observation.last > 120",
        ):
            self.assertIn(required, observe)
        select = function_body(source("task_v284.nut"), "function OpexV284Select(")
        self.assertIn("waiting, 2 * capacity, date", select)
        self.assertIn(
            "if (V284_RAIL_GROWTH > 0 && year >= OPEX_START_YEAR + V284_RAIL_GROWTH",
            select,
        )
        self.assertIn("year < OPEX_START_YEAR + 2", select)
        # N75 ne doit pas declencher la selection V284 habituelle en 1972.
        self.assertEqual(select.count("best = candidate;"), 1)
        self.assertIn("N75_FREIGHT_CAPACITY > 0 && !atLimit", select)
        self.assertIn("best.add = true", select)
        self.assertIn('action=pick kind=train', select)

    def test_no_traction_geometry_slot_or_finance_bypass(self):
        select = function_body(source("task_v284.nut"), "function OpexV284Select(")
        for required in (
            "OpexV284Equipment(persistent.line",
            "OpexN75FreightMargin(persistent.line",
            "OpexRailVehicleSlotAvailable()",
            "OpexV284LoopPlan(persistent.line",
            "preparedLoop != null",
            "state.pending = {",
        ):
            self.assertIn(required, select)
        self.assertLess(select.index("OpexV284LoopPlan(persistent.line"),
                        select.index("best.add = true"))
        margin = function_body(source("task_n75_freight.nut"), "function OpexN75FreightMargin(")
        for required in (
            "line.lastRevenue.tofloat() * 0.5",
            "replacement.price + wagons * wagon.price",
            "replacement.runningCost + wagons * wagon.runningCost",
            "annualMargin.tofloat() * 3 < gross",
            "OpexAvailableCapital() < gross + 50000",
        ):
            self.assertIn(required, margin)
        tick = function_body(source("task_v284.nut"), "function OpexV284Tick(")
        self.assertIn("requiredWaiting = 2 * AIVehicle.GetCapacity(oldVehicle, line.cargo)", tick)
        self.assertIn("OpexN75FreightMargin(line, oldVehicle", tick)
        self.assertLess(tick.index("!n75Recheck"), tick.index("OpexV284BuildLoop"))
        self.assertLess(tick.index("OpexV284BuildLoop"), tick.index("OpexBuildTrains"))
        self.assertLess(tick.index("OpexBuildTrains"), tick.index("OpexV284Adopt"))

    def test_save_load_and_runtime_are_shared_with_v284(self):
        persist = source("persist.nut")
        self.assertIn("saveObj.n75Freight <- this._n75Freight", persist)
        self.assertIn('"n75Freight" in data', persist)
        self.assertIn('typeof data.n75Freight.samples == "table"', persist)
        self.assertLess(persist.index("this._lines = liveLines"),
                        persist.index("OpexV284Reconcile(this)"))
        self.assertLess(persist.index("data.n75Freight"), persist.index("function OpexAI::_reconcileAfterLoad("))
        self.assertIn("OpexV284Busy(this)", source("orchestrator.nut"))
        self.assertIn("OpexV284Reconcile(this)", persist)
        self.assertIn("OpexV284RollbackLoop", source("task_v284.nut"))

    def test_no_unsafe_squirrel_keywords_or_closures(self):
        code = source("task_n75_freight.nut")
        self.assertNotRegex(code, r"\blocal\s+(clone|base|parent|static|yield)\b")
        self.assertNotRegex(code, r"=\s*function\s*\(")
        self.assertNotIn(".find(", code)


if __name__ == "__main__":
    unittest.main()
