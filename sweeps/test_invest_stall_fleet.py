"""INVEST-STALL v2 fleet contracts (static; NoAI Squirrel smoke remains required).

Only the three files owned by the fleet worker are edited here. Integration
hooks in main/task_rail/persist/orchestrator are owned by the prime agent.
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def source(filename):
    return (AI / filename).read_text(encoding="utf-8")


def function(filename, signature):
    code = source(filename)
    start = code.index("function " + signature + "(")
    end = code.find("\nfunction ", start + 1)
    return code[start:end if end >= 0 else len(code)]


class InvestStallFleetContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fleet = source("invest_stall_fleet.nut")
        cls.v284 = source("task_v284.nut")

    def test_off_and_1974_gate_are_before_any_state_change(self):
        select = function("invest_stall_fleet.nut", "OpexInvestStallFleetSelect")
        self.assertIn("if (!INVEST_STALL || year < OPEX_START_YEAR + 4", select)
        self.assertIn("!OpexInvestStallReady()", select)
        self.assertIn("!SAVE_FULL_STATE", select)
        self.assertLess(select.index("if (!INVEST_STALL"), select.index("state.rawset("))
        self.assertIn("INVEST_STALL <- false;", source("globals_pre.nut"))
        self.assertIn('AIController.GetSetting("invest_stall") == 1;', source("settings.nut"))
        settings = source("info.nut").split('name = "invest_stall"', 1)[1][:500]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 0", settings)

    def test_uses_common_source_shortfall_gate(self):
        select = function("invest_stall_fleet.nut", "OpexInvestStallFleetSelect")
        gap = function("invest_stall.nut", "OpexInvestStallSourceGap")
        self.assertIn("OpexInvestStallSourceGap(owner, line)", select)
        self.assertIn("if (!gap.ok)", select)
        self.assertIn("GetLastMonthProduction", gap)
        self.assertIn("GetLastMonthTransportedPercentage", gap)
        self.assertIn("pct >= 75 && rating >= 75", gap)
        self.assertIn("production.tofloat() <= total", gap)

    def test_replacement_only_one_wagon_under_platform_limit(self):
        select = function("invest_stall_fleet.nut", "OpexInvestStallFleetSelect")
        for required in (
            "line.vehicles.len() != 1", "line.trains != 1",
            "OpexV163Wagons2(line) > 0",
            "AIVehicle.GetNumWagons(vehicle) - 1",
            "GetWagonEngineType(vehicle, w) != wagonId",
            "AIRail.IsRailDepotTile(line.depot)",
            "OpexRailNominalMaxWagons(limit)",
            "AIVehicle.GetLength(vehicle) + 8 > limit * 16",
            "oldWagons + 1, false",
            "add = false, loopPlan = null",
            "wagons = best.oldWagons + 1",
        ):
            with self.subTest(required=required):
                self.assertIn(required, select)
        self.assertNotIn("OpexV284LoopPlan", select)
        self.assertNotIn("OpexV284BuildLoop", select)
        self.assertNotIn("OpexBuildSecondTrain", self.fleet)
        self.assertNotIn("CloneVehicle", self.fleet)

    def test_at_limit_does_not_enter_single_track_v284_train_loop(self):
        select = function("invest_stall_fleet.nut", "OpexInvestStallFleetSelect")
        start = select.index("if (atLimit) {")
        end = select.index("local margin = extension", start)
        guard = select[start:end]
        self.assertIn("OpexInvestStallPlatformPlan(owner, line", guard)
        self.assertIn("if (extension == null)", guard)
        self.assertIn("reason=at_limit_train_uncertified", guard)
        self.assertIn("OpexInvestStallFleetTrainCertified(line)", guard)
        self.assertIn("continue;", guard)
        # Until a physically verifiable two-train transaction exists, fail closed.
        certificate = function("invest_stall_fleet.nut", "OpexInvestStallFleetTrainCertified")
        self.assertIn("return false;", certificate)

    def test_profit_is_net_and_uses_aggregate_origin_capacity(self):
        margin = function("invest_stall_fleet.nut", "OpexInvestStallFleetMargin")
        for required in (
            "gap.production.tofloat() * gap.rating / 100.0 - gap.capacity",
            "newCapacity - oldCapacity", "if (extra > free) extra = free",
            "if (extra <= 0.0) return null",
            "AICargo.GetCargoIncome",
            "newSpeed < oldSpeed",
            "12.0 * extra * income - running - price / newLoco.ageYears",
            "OpexAvailableCapital() < price + 50000",
            "if (profit <= 0",
        ):
            with self.subTest(required=required):
                self.assertIn(required, margin)
        select = function("invest_stall_fleet.nut", "OpexInvestStallFleetSelect")
        self.assertLess(select.index("OpexInvestStallFleetMargin(line, vehicle"),
                        select.index("state.pending = {"))
        self.assertIn("margin.score > best.margin.score", select)

    def test_transaction_revalidates_before_build_and_is_reconcilable(self):
        tick = function("task_v284.nut", "OpexV284Tick")
        self.assertIn("OpexInvestStallSourceGap(owner, line)", tick)
        self.assertIn("OpexInvestStallFleetMargin(line, oldVehicle", tick)
        self.assertIn('OpexV284Cancel(owner, pending, "invest_stall_recheck")', tick)
        self.assertLess(tick.index('OpexV284Cancel(owner, pending, "invest_stall_recheck")'),
                        tick.index("OpexBuildTrains("))
        self.assertIn("pending.before = []", tick)
        self.assertIn("pending.phase = \"building\"", tick)
        self.assertIn("OpexV284Adopt(owner, line, pending)", tick)
        self.assertIn("OpexV284Adopt(owner, line, pending)",
                      function("task_v284.nut", "OpexV284Reconcile"))
        self.assertIn('pending.phase = "rollback"', tick)
        self.assertIn("&& !INVEST_STALL", tick)

    def test_no_duplicate_done_after_save_load(self):
        adopt = function("task_v284.nut", "OpexV284Adopt")
        self.assertIn('"investStallDoneLogged" in pending', adopt)
        self.assertIn('pending.investStallDoneLogged <- true;', adopt)
        self.assertIn('OpexInvestStallFleetLog("done"', adopt)
        select = function("invest_stall_fleet.nut", "OpexInvestStallFleetSelect")
        for required in (
            "investStall = true", "state.pending = {",
            'state.rawset("investStallNextDate", now + 30)',
            "state.investStallDates.rawset(line.lineId, now + 90)",
            "newVehicle = -1", 'phase = "approach"',
            "speedMilli = ", "oldSpeedMilli = ",
        ):
            with self.subTest(required=required):
                self.assertIn(required, select)
        # Integration hooks are needed to keep pending across Save/Load when
        # V284_RAIL_GROWTH and V233_LONG_GOOD are both disabled.
        persist = source("persist.nut")
        self.assertIn("INVEST_STALL", persist.split("saveObj.v284Growth", 1)[0][-140:])
        self.assertIn("INVEST_STALL", persist.split("OpexV284Reconcile(this)", 1)[0][-140:])

    def test_event_contract_and_require_hook(self):
        for event in ("screen", "pick", "done", "skip"):
            with self.subTest(event=event):
                self.assertIn('OpexInvestStallFleetLog("' + event + '"',
                              self.fleet + self.v284)
        self.assertIn('OpexDecide("INVEST_STALL", "event=" + event',
                      function("invest_stall_fleet.nut", "OpexInvestStallFleetLog"))
        self.assertIn('require("invest_stall_fleet.nut");', source("main.nut"))
        expand = function("task_rail.nut", "OpexAI::_expandRailLines")
        self.assertIn("OpexInvestStallFleetSelect(this, year)", expand)
        self.assertLess(expand.index("OpexInvestStallFleetSelect(this, year)"),
                        expand.index("OpexV284Select(this, year)"))

    def test_squirrel_source_has_no_forbidden_new_forms(self):
        for filename in ("invest_stall_fleet.nut",):
            code = source(filename)
            self.assertNotRegex(code, r"\bfunction\s*\(")
            self.assertNotIn(".find(", code)
            self.assertNotRegex(code, r"\blocal\s+(?:clone|base|parent|static|delegate|resume|yield)\b")
            self.assertNotIn("AITestMode()", code)
            self.assertNotIn("AIAccounting()", code)


if __name__ == "__main__":
    unittest.main()
