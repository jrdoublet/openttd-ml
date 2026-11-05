"""Development contracts only: platform transactions still need NoAI simulation."""

import hashlib
import json
import re
import unittest

from invest_stall_platform_off import FIXTURE, off_source
from invest_stall_merged_off import MERGED
from invest_stall_diagnostic_off import off_source as diagnostic_off
from rail_long_v3_multi_off import upgrade_reservation_off
from test_invest_stall_fleet import source, function


class InvestStallPlatformContracts(unittest.TestCase):
    def test_new_layer_restores_all_four_predevelopment_sources_exactly(self):
        for name, entry in json.loads(FIXTURE.read_text(encoding="utf8"))["files"].items():
            with self.subTest(name=name):
                live = upgrade_reservation_off(name, diagnostic_off(name, source(name)))
                bridge = MERGED.get("platform", {}).get(name)
                expected_live = bridge["on_sha256"] if bridge is not None else entry["after_sha256"]
                expected_prior = bridge["off_sha256"] if bridge is not None else entry["before_sha256"]
                self.assertEqual(hashlib.sha256(live.encode()).hexdigest(), expected_live)
                prior = off_source(name, live)
                self.assertEqual(hashlib.sha256(prior.encode()).hexdigest(), expected_prior)
                self.assertEqual(off_source(name, prior), prior)

    def test_projection_rejects_modified_or_duplicated_new_guards(self):
        code = source("task_v284.nut")
        for corrupt in (
            code.replace("!investStall && waitingNow", "investStall && waitingNow"),
            code + "\nlocal investStall = true;\n",
        ):
            with self.assertRaises(AssertionError):
                off_source("task_v284.nut", corrupt)

    def test_selection_keeps_wagon_first_and_never_requests_a_second_train(self):
        select = function("invest_stall_fleet.nut", "OpexInvestStallFleetSelect")
        self.assertLess(select.index("if (atLimit)"), select.index("OpexInvestStallPlatformPlan("))
        self.assertIn("extension != null ? extension.margin", select)
        self.assertIn("if (best.extension != null)", select)
        self.assertIn("investStall = true", select)
        self.assertIn("add = false, loopPlan = null", select)
        self.assertNotIn("RAIL_LONG_V2 =", select)
        self.assertNotIn("OpexRailLongV2Select(", select)

    def test_seven_then_six_respects_game_and_actual_platform_limits(self):
        plan = function("invest_stall_fleet.nut", "OpexInvestStallPlatformPlan")
        for clause in (
            'min(7, min(AIGameSettings.GetValue("station.station_spread")',
            'AIGameSettings.GetValue("vehicle.max_train_length")',
            "target >= 6 && target > line.platformLength; target--",
            "oldWagons + 1 > OpexRailNominalMaxWagons(target)",
            "AIVehicle.GetLength(vehicle) + 8 > target * 16",
            "OpexRailLongV2ExtendPlan(line.platformA",
            "OpexRailLongV2ExtendPlan(line.platformB",
            "if (overlaps) continue;",
        ):
            self.assertIn(clause, plan)

    def test_quotes_include_both_platforms_and_full_replacement(self):
        plan = function("invest_stall_fleet.nut", "OpexInvestStallPlatformPlan")
        self.assertIn("OpexRailLongV2Quote(planA, planB, line.depot)", plan)
        margin = function("invest_stall_fleet.nut", "OpexInvestStallPlatformMargin")
        self.assertIn("OpexInvestStallFleetMargin(", margin)
        self.assertIn("margin.profit - construction / loco.ageYears", margin)
        self.assertIn("margin.cost + construction", margin)
        self.assertIn("profit <= 0 || OpexAvailableCapital() < cost + 50000", margin)

    def test_platforms_exclude_all_other_transactions(self):
        free = function("invest_stall_fleet.nut", "OpexInvestStallPlatformSlotFree")
        for guard in ("OpexRailLongV2TransactionsFree(owner)", "_railLongV3UpgradePending == null",
                      "_activeWorker == null", "!owner._po01cPending", "V233L_STATE.pending != null"):
            self.assertIn(guard, free)
        common = function("task_rail_long_v2.nut", "OpexRailLongV2TransactionsFree")
        for guard in ("_railSearch == null", "_railExpansion == null", "_v257Pending == null",
                      "_v271Pending == null", "!OpexV284Busy(owner)"):
            self.assertIn(guard, common)
        expand = function("task_rail.nut", "OpexAI::_expandRailLines")
        self.assertLess(expand.index("_railLongV2Pending.investStall) return"),
                        expand.index("OpexRailPairReview(this)"))

    def test_save_load_retains_provenance_without_float_fields(self):
        begin = function("task_rail_long_v2.nut", "OpexRailLongV2Begin")
        self.assertLess(begin.index("state.rawset(key, value)"), begin.index("owner._railLongV2Pending = state"))
        for field in ("beforeA = []", "intentA = false", "intentB = false", 'phase = "ready"',
                      "oldA = planA.original", "targetA = planA.target", "quotedCost = quote"):
            self.assertIn(field, begin)
        persist = source("persist.nut")
        self.assertIn("if (RAIL_LONG_V2 || this._railLongV2Pending != null)", persist)
        self.assertIn("saveObj.railLongV2Upgrade <- this._railLongV2Pending", persist)
        self.assertIn('this._railLongV2Pending = data.railLongV2Upgrade', persist)
        self.assertIn("OpexRailLongV2Reconcile(this)", persist)

    def test_disabled_investment_rolls_back_without_disabling_historical_rail_long(self):
        for name in ("OpexRailLongV2Step", "OpexRailLongV2Reconcile"):
            code = function("task_rail_long_v2.nut", name)
            self.assertIn("investStall ? !INVEST_STALL : !RAIL_LONG_V2", code)
        reconcile = function("task_rail_long_v2.nut", "OpexRailLongV2Reconcile")
        self.assertIn('state.reason = "invest_stall_invalid_intent"', reconcile)
        self.assertIn('state.phase = "rollback"', reconcile)
        step = function("task_rail_long_v2.nut", "OpexRailLongV2Step")
        self.assertIn("if (!investStall) {", step)
        self.assertIn('line.rawset("railLongV2", true)', step)
        self.assertNotIn("OpexV284Select", step)

    def test_rechecks_precede_mutations_and_only_unbuilt_tiles_are_quoted(self):
        step = function("task_rail_long_v2.nut", "OpexRailLongV2Step")
        self.assertLess(step.index("OpexInvestStallPlatformRecheck(owner, line, state)"),
                        step.index("OpexRailLongV2BuildPart(state"))
        check = function("invest_stall_fleet.nut", "OpexInvestStallPlatformRecheck")
        for guard in ("OpexInvestStallSourceGap(owner, line)", "OpexInvestStallPlatformMargin(",
                      "OpexRailLongV2PlanMatches(line.platformA, state.oldA)",
                      "OpexRailLongV2PlanMatches(line.platformB, state.oldB)",
                      "left.tiles = []", "right.tiles = []", "max(state.quotedCost, spent + quote)",
                      "GetWagonEngineType(state.vehicle, w) != state.wagon"):
            self.assertIn(guard, check)

    def test_shared_safety_primitives_and_historical_selector_are_unchanged(self):
        live = source("task_rail_long_v2.nut")
        prior = off_source("task_rail_long_v2.nut", live)
        for name in ("OpexRailLongV2Select", "OpexRailLongV2ExtendPlan", "OpexRailLongV2Quote",
                     "OpexRailLongV2LineSafe", "OpexRailLongV2RollbackPart", "OpexRailLongV2CommitReady"):
            start = prior.index("function " + name + "(")
            end = prior.find("\nfunction ", start + 1)
            original = prior[start:end if end >= 0 else len(prior)]
            current = function("task_rail_long_v2.nut", name)
            # The helper includes the comment introducing the next function.
            self.assertEqual(current[:current.rindex("\n}") + 2],
                             original[:original.rindex("\n}") + 2])

    def test_low_stock_exception_is_scoped_and_economically_rechecked(self):
        tick = function("task_v284.nut", "OpexV284Tick")
        self.assertIn("(!investStall && waitingNow < requiredWaiting)", tick)
        for guard in ("AIEngine.GetCargoType(pending.wagon) != line.cargo",
                      "AIVehicle.GetCargoLoad(oldVehicle, line.cargo) != 0",
                      "!AIEngine.HasPowerOnRail(pending.engine", "< cashNeed",
                      "OpexInvestStallSourceGap(owner, line)", "OpexInvestStallFleetMargin(line, oldVehicle",
                      "pending.wagons != pending.oldWagons + 1"):
            self.assertIn(guard, tick)
        self.assertLess(tick.index('"invest_stall_recheck"'), tick.index("OpexBuildTrains("))

    def test_trimmed_replacement_is_rejected_before_orders_start_and_adoption(self):
        tick = function("task_v284.nut", "OpexV284Tick")
        check = tick.index('"invest_stall_built_capacity"')
        self.assertLess(tick.index("pending.newVehicle = built.vehicles"), check)
        self.assertLess(check, tick.index("AIOrder.CopyOrders("))
        self.assertLess(check, tick.index("AIVehicle.StartStopVehicle(pending.newVehicle)"))
        self.assertIn("AIVehicle.GetNumWagons(pending.newVehicle) - 1 != pending.wagons", tick)
        self.assertIn("<= AIVehicle.GetCapacity(oldVehicle, line.cargo)", tick)

    def test_platform_logs_record_quote_actual_costs_lengths_and_margin(self):
        log = function("task_rail_long_v2.nut", "OpexRailLongV2TransactionLog")
        for field in ("kind=platform", "len_a=", "len_b=", "target=", "quote=", "cost_a=", "cost_b="):
            self.assertIn(field, log)
        fleet = source("invest_stall_fleet.nut")
        for field in ("profit=", "capacity_month=", "production=", "rating=", "cash="):
            self.assertIn(field, fleet)

    def test_new_source_has_balanced_delimiters_and_no_reserved_locals(self):
        for name in ("invest_stall_fleet.nut", "task_rail_long_v2.nut", "task_v284.nut"):
            code = source(name)
            code = re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"', '', code, flags=re.S)
            stack = []
            pairs = {')': '(', ']': '[', '}': '{'}
            for char in code:
                if char in "([{":
                    stack.append(char)
                elif char in pairs:
                    self.assertTrue(stack, name)
                    self.assertEqual(stack.pop(), pairs[char], name)
            self.assertEqual(stack, [], name)
            self.assertNotRegex(code, r'\blocal\s+(?:clone|base|parent|static|delegate|resume|yield)\b')
            self.assertNotRegex(code, r'\bfunction\s*\(')
            self.assertNotIn('.find(', code)


if __name__ == "__main__":
    unittest.main()
