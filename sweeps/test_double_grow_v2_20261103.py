"""Static safety contracts for DOUBLE-GROW v2 (double_grow=2).

These tests check opt-in dispatch, deferred admission, fleet certification and
the source-level transaction boundary. They do not run OpenTTD and cannot
prove a safe physical retrofit or correct train movement.
"""

from pathlib import Path
import re
import unittest

from double_grow_off import off_source
from test_rail_search_prio_20261103 import off_config_bytes


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf8")


def function(name, file):
    """Return a whole top-level Squirrel function, not a name-only match."""
    text = source(file)
    match = re.search(r"(?m)^function " + re.escape(name) + r"\s*\(", text)
    if match is None:
        raise AssertionError(f"missing {name} in {file}")
    after = re.search(r"(?m)^function [A-Za-z_]\w*\s*\(", text[match.end():])
    end = match.end() + after.start() if after else len(text)
    return text[match.start():end]


def deferred_start(selector):
    """Find the currently selected synchronous or resumable retrofit entry."""
    calls = ("OpexDoubleGrowV2Begin(owner, line)",
             "OpexDoubleGrowV2Build(owner, line)")
    present = [call for call in calls if call in selector]
    if len(present) != 1:
        raise AssertionError("v2 selector must have exactly one retrofit admission call")
    return selector.index(present[0])


class TestDoubleGrowV2Contracts(unittest.TestCase):
    def test_setting_2_is_explicit_and_default_0(self):
        info = source("info.nut")
        setting = re.search(r'AddSetting\(\{ name = "double_grow",(?P<body>.*?)\}\);',
                            info, re.DOTALL)
        self.assertIsNotNone(setting)
        body = setting.group("body")
        self.assertRegex(body, r"min_value\s*=\s*0,\s*max_value\s*=\s*2")
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(body, rf"{difficulty}_value\s*=\s*0\b")
        self.assertRegex(body, r"flags\s*=\s*0\b")
        self.assertIn("DOUBLE_GROW <- false;", source("globals_pre.nut"))
        self.assertIn("DOUBLE_GROW_V2 <- false;", source("globals_pre.nut"))
        settings = source("settings.nut")
        self.assertIn('DOUBLE_GROW = AIController.GetSetting("double_grow") == 1;', settings)
        self.assertIn('DOUBLE_GROW_V2 = AIController.GetSetting("double_grow") == 2;', settings)

    def test_v1_dispatch_is_preserved_and_v2_uses_its_own_entry_point(self):
        self.assertIn('require("double_grow.nut");', source("main.nut"))
        self.assertIn('require("double_grow_v2_build.nut");', source("main.nut"))
        self.assertIn('require("double_grow_v2.nut");', source("main.nut"))
        expansion = function("OpexAI::_expandRailLines", "task_rail.nut")
        v1 = "if (DOUBLE_GROW && OpexDoubleGrowSelect(this, year)) return;"
        v2 = "if (DOUBLE_GROW_V2 && OpexDoubleGrowV2Select(this, year)) return;"
        self.assertIn(v1, expansion)
        self.assertIn(v2, expansion)
        self.assertLess(expansion.index(v1), expansion.index(v2))
        self.assertLess(expansion.index(v2), expansion.index("OpexRailLongV2Select"))
        self.assertNotIn("DOUBLE_GROW_V2", function("OpexDoubleGrowSelect", "double_grow.nut"))

    def test_v2_does_not_take_or_preempt_an_active_search_slot(self):
        selector = function("OpexDoubleGrowV2Select", "double_grow_v2.nut")
        for blocked in ("owner._railSearch != null", "owner._activeWorker != null",
                        "owner._railExpansion != null", "owner._v257Pending != null",
                        "owner._v271Pending != null", "owner._railLongV2Pending != null",
                        "OpexV284Busy(owner)"):
            self.assertIn(blocked, selector)
        self.assertLess(selector.index("owner._railSearch != null"),
                        deferred_start(selector))
        for forbidden in ("_startRailSearch(", "_startRailUpgradeSearch(",
                          "_railSearch =", "_activeWorker =", "OpexWorkerCancel("):
            self.assertNotIn(forbidden, selector)

    def test_real_pending_primary_work_has_priority_over_retrofit(self):
        selector = function("OpexDoubleGrowV2Select", "double_grow_v2.nut")
        pending = function("OpexDoubleGrowV2PrimaryPending", "double_grow_v2.nut")
        self.assertIn("OpexDoubleGrowV2PrimaryPending(owner)", selector)
        self.assertLess(selector.index("OpexDoubleGrowV2PrimaryPending(owner)"),
                        deferred_start(selector))
        # Ranked 'best' contains rejected candidates; it is not a live work
        # queue. Only a concrete PO01C pending intent blocks the retrofit.
        self.assertRegex(pending, r"return\s+owner\s*!=\s*null\s*&&\s*owner\._po01cPending\s*;")
        for forbidden in ("_ensureSelection(", "_projects.best",
                          "OpexProjectFinanceCapital(", "foreach (",
                          "_startRailSearch("):
            self.assertNotIn(forbidden, pending)
        self.assertIn("_po01cPending = false;", source("main.nut"))
        for busy in ("owner._railSearch != null", "owner._activeWorker != null",
                     "owner._railExpansion != null", "owner._v257Pending != null",
                     "owner._v271Pending != null", "owner._railLongV2Pending != null",
                     "OpexV284Busy(owner)"):
            self.assertIn(busy, selector)
        self.assertIn("if (principalBusy) return false;", selector)
        self.assertLess(selector.index("if (principalBusy) return false;"),
                        deferred_start(selector))

    def test_secondary_search_pauses_and_resumes_when_primary_is_busy(self):
        selector = function("OpexDoubleGrowV2Select", "double_grow_v2.nut")
        # A secondary search may live outside the main _railSearch slot; the
        # selector must inspect the *same* state that Begin/Continue/Cancel use.
        self.assertIn("owner._doubleGrowV2State != null", selector)
        has_pending = function("OpexDoubleGrowV2HasPending", "double_grow_v2_build.nut")
        begin = function("OpexDoubleGrowV2Begin", "double_grow_v2_build.nut")
        cancel = function("OpexDoubleGrowV2Cancel", "double_grow_v2_build.nut")
        cont = function("OpexDoubleGrowV2Continue", "double_grow_v2_build.nut")
        for method in (has_pending, begin, cancel, cont):
            self.assertIn("owner._doubleGrowV2State", method)
        self.assertIn("owner._doubleGrowV2State = null;", cancel)
        self.assertIn("owner._doubleGrowV2State = prep;", begin)
        self.assertIn("_doubleGrowV2State = null;", source("main.nut"))
        self.assertIn('owner._doubleGrowV2State.rawset("pauseLogged", true)', selector)
        self.assertIn('owner._doubleGrowV2State.pauseLogged = false;', selector)
        self.assertIn('"version=2 action=pause reason=principal_busy"', selector)
        self.assertIn('"version=2 action=resume spent="', selector)
        self.assertNotIn("OpexDoubleGrowV2Cancel(owner)", selector)
        self.assertIn("OpexDoubleGrowV2Continue(owner)", selector)
        self.assertIn("OpexDoubleGrowV2Begin(owner, line)", selector)
        self.assertIn("if (principalBusy)", selector)
        self.assertLess(selector.index('owner._doubleGrowV2State.rawset("pauseLogged", true)'),
                        selector.index("OpexDoubleGrowV2Continue(owner)"))
        self.assertLess(selector.index("if (principalBusy) return false;"),
                        selector.index("OpexDoubleGrowV2Begin(owner, line)"))
        # The optional A* has its own transient object. Neither the selection
        # nor its cancellation may cancel the primary rail worker.
        self.assertNotIn("OpexWorkerCancel(", selector)
        self.assertNotIn("owner._railSearch =", selector)

    def test_v2_defers_to_existing_profitable_freight_and_waiting_cargo(self):
        selector = function("OpexDoubleGrowV2Select", "double_grow_v2.nut")
        for gate in ('!DOUBLE_GROW_V2', 'line.kind != "freight"',
                     'line.mode != "rail"', "line.trains != line.vehicles.len()",
                     "now - line.buildDate < 365", "line.lastProfit <= 0",
                     'AIStation.GetCargoWaiting(station, line.cargo)',
                     "waiting < 120", "OpexDoubleGrowV2AdmissionQuote(owner, line)",
                     "now < line.doubleGrowV2Retry"):
            self.assertIn(gate, selector)
        self.assertIn("if (quote <= 0 || cash < quote)", selector)
        self.assertIn("OpexAvailableCapital()", selector)
        builder = function("OpexDoubleGrowV2Build", "double_grow_v2_build.nut")
        self.assertIn("OpexAvailableCapital() < estimate + 50000", builder)
        self.assertIn("AICompany.GetBankBalance(AICompany.COMPANY_SELF) < estimate + 50000", builder)
        self.assertLess(selector.index("waiting < 120"),
                        deferred_start(selector))
        self.assertIn('line.rawset("doubleGrowV2Retry", now + 30)', selector)
        self.assertIn('line.trains != 1', selector)
        self.assertIn('line.doubleGrowDirectional', selector)

    def test_admission_quotes_route_two_platforms_depot_train_and_reserve(self):
        quote = function("OpexDoubleGrowV2AdmissionQuote", "double_grow_v2.nut")
        select = function("OpexDoubleGrowV2Select", "double_grow_v2.nut")
        self.assertIn("OpexDoubleGrowPrimaryRoute(line)", quote)
        self.assertIn("AIRail.GetBuildCost(railType, AIRail.BT_TRACK)", quote)
        self.assertIn("2 * line.platformLength * owner._catalog.costStation", quote)
        self.assertIn("AIVehicle.GetNumWagons(sample)", quote)
        self.assertIn("AIVehicle.GetWagonEngineType(sample, i)", quote)
        self.assertIn("AIEngine.GetPrice(engine)", quote)
        self.assertIn("AIRail.GetBuildCost(railType, AIRail.BT_DEPOT)", quote)
        self.assertIn("route.len() * tileCost + padCost", quote)
        self.assertIn("+ AIRail.GetBuildCost(railType, AIRail.BT_DEPOT) + trainCost + 50000", quote)
        self.assertLess(select.index("local quote = OpexDoubleGrowV2AdmissionQuote(owner, line)"),
                        select.index("OpexDoubleGrowV2Begin(owner, line)"))
        self.assertIn('" result=skip_cash quote="', select)
        self.assertIn('" result=start quote="', select)

    def test_v2_growth_requires_directional_proof_and_is_capped_at_six(self):
        selector = function("OpexDoubleGrowV2Select", "double_grow_v2.nut")
        directional = selector.index('line.doubleGrowDirectional')
        growth = selector.index("OpexDoubleGrowFleet(owner, line)")
        retrofit = deferred_start(selector)
        self.assertLess(directional, growth)
        self.assertLess(growth, retrofit)
        self.assertIn("line.trains < 6", selector)
        fleet = function("OpexDoubleGrowFleet", "double_grow_fleet.nut")
        finalize = function("OpexDoubleGrowFleetFinalize", "double_grow_fleet.nut")
        quote = function("OpexDoubleGrowQuote", "double_grow_fleet.nut")
        for code in (fleet, finalize):
            self.assertIn("DOUBLE_GROW || DOUBLE_GROW_V2", code)
        self.assertIn("DOUBLE_GROW_V2 ? 6 : 8", quote)
        self.assertIn("OpexDoubleGrowOrdersSafe(line)", fleet)
        self.assertIn("OpexDoubleGrowQuote(owner, line)", fleet)
        self.assertIn("OpexDoubleGrowSignalsSafe(line, line.vehicles.len() + 1)", quote)
        self.assertIn("OpexDoubleGrowMargin(owner, line, model)", quote)
        self.assertLess(fleet.index("if (!ok) {"), fleet.index("line.vehicles.append(extra)"))
        self.assertIn("AIVehicle.SellVehicle(extra)", fleet)
        self.assertIn("line.doubleGrowNextDate", fleet)

    def test_v2_builder_requires_a_transaction_and_fail_closed_rollback(self):
        builder = source("double_grow_v2_build.nut")
        body = function("OpexDoubleGrowV2Build", "double_grow_v2_build.nut")
        self.assertNotIn("_startRailSearch(", builder)
        self.assertNotIn("_startRailUpgradeSearch(", builder)
        self.assertNotIn("_railSearch =", builder)
        # Existing live service is not surrendered to the retrofit attempt.
        self.assertNotIn("OpexCancelRailLine(", body)
        self.assertNotIn("OpexV190RollbackDoubleTrack(", body)
        # The original primary route and the two secondary rails must be
        # checked BEFORE the conversion changes train orders.
        begin = function("OpexDoubleGrowV2Begin", "double_grow_v2_build.nut")
        self.assertIn("OpexDoubleGrowPrimaryRoute(line)", begin)
        self.assertIn("OpexDoubleGrowV2Prepare(line, route)", begin)
        self.assertIn("OpexDoubleGrowVerifyRoute(route", body)
        self.assertNotIn("AIRail.BuildRailStation(", begin)
        self.assertIn("OpexDoubleGrowV2Plan(state.line, state, result)",
                      function("OpexDoubleGrowV2Continue", "double_grow_v2_build.nut"))
        self.assertLess(body.index("OpexV190VerifyIndependentDouble(staged"),
                        body.index("OpexDoubleGrowFleetFinalize(owner, line, staged)"))
        self.assertIn("staged = clone line;", body)
        self.assertIn('staged.rawset("vehicles", [line.vehicles[0]])', body)
        self.assertIn("OpexDoubleGrowRollbackGeometry(plan)", body)
        rollback = function("OpexDoubleGrowRollbackGeometry", "double_grow_geometry.nut")
        self.assertIn("(t in geometry.forbidden)", rollback)
        self.assertIn("AITile.GetOwner(t) != own", rollback)
        self.assertIn("AITile.GetOwner(geometry.depot2) == own", rollback)
        self.assertIn("AIStation.GetStationID(t) != stationId", rollback)
        self.assertNotIn("OpexV190RollbackDoubleTrack(", rollback)
        self.assertLess(body.index("if (!built) {"), body.index('line.rawset("tiles1", route)'))
        self.assertLess(body.index("OpexDoubleGrowRollbackGeometry(plan)"),
                        body.index('line.rawset("tiles1", route)'))
        self.assertNotIn("line.rawset(", body[:body.index("if (!built) {")])
        self.assertIn("return false;", body)
        self.assertIn('line.rawset("doubleGrowDirectional", true)', body)

    def test_planning_fails_closed_on_primary_infrastructure_and_native_cost(self):
        protect = function("OpexDoubleGrowV2Protected", "double_grow_v2_build.nut")
        plan = function("OpexDoubleGrowV2Plan", "double_grow_v2_build.nut")
        build = function("OpexDoubleGrowV2Build", "double_grow_v2_build.nut")
        for guard in ("foreach (tile in route)", "blocked[line.depot] <- true",
                      "AIRail.GetRailDepotFrontTile(line.depot)",
                      "platform.anchor + i * platform.step", "platform.station_exit",
                      "platform.lead"):
            self.assertIn(guard, protect)
        prepare = function("OpexDoubleGrowV2Prepare", "double_grow_v2_build.nut")
        self.assertIn("OpexDoubleGrowV2Protected(line, route)", prepare)
        self.assertIn("OpexPlanHitsSet(pA, blocked)", prepare)
        self.assertIn("OpexPlanHitsSet(pB, blocked)", plan)
        self.assertIn("OpexPlanHitsSet(pB, padASet)", plan)
        self.assertIn("OpexDoubleGrowClear(tiles, structures, blocked,", plan)
        self.assertLess(plan.index("OpexDoubleGrowClear(tiles, structures"),
                        plan.index("OpexTestRailTrack(tiles, structures)"))
        self.assertIn("native.failed != 0", plan)
        self.assertLess(build.index("OpexAvailableCapital() < estimate + 50000"),
                        build.index("AIRail.BuildRailStation("))

    def test_independent_search_is_bounded_and_cannot_touch_existing_corridor(self):
        plan = function("OpexDoubleGrowV2Plan", "double_grow_v2_build.nut")
        prepare = function("OpexDoubleGrowV2Prepare", "double_grow_v2_build.nut")
        begin = function("OpexDoubleGrowV2Begin", "double_grow_v2_build.nut")
        cont = function("OpexDoubleGrowV2Continue", "double_grow_v2_build.nut")
        self.assertNotIn("OpexV190TraceParallelTrack(", plan)
        self.assertRegex(prepare, r"foreach \(tile, \w+ in blocked\) ignored\.append\(tile\);")
        self.assertIn("OpexCreateRailPathfinder(prep.eligibleA, prep.eligibleB,", begin)
        self.assertRegex(begin, r"prep\.budget\s*<-\s*\d+")
        self.assertIn("OpexAdvanceRailPathfinder(state.pathfinder,", cont)
        self.assertRegex(cont, r"AIController\.GetTick\(\)\s*\+\s*\d+,\s*\d+\)")
        self.assertIn("if (!result.done)", cont)
        self.assertIn("state.spent = result.iterations", cont)
        self.assertIn("OpexJoinPathIsDedicated(tiles)", plan)
        self.assertIn("OpexMatchPlanExact(eligibleA", plan)
        self.assertIn("OpexMatchPlanExact(eligibleB", plan)
        self.assertIn("OpexDoubleGrowClear(tiles, structures, blocked,", plan)
        self.assertLess(plan.index("OpexMatchPlanExact(eligibleA"),
                        plan.index("OpexTestRailTrack(tiles, structures)"))

    def test_off_projection_removes_both_versions_and_is_idempotent(self):
        # OFF baselines are anchored on the previous code, including no v2
        # requires or dispatch. No historical fixture may be regenerated here.
        for name in ("globals_pre.nut", "settings.nut", "info.nut",
                     "main.nut", "task_rail.nut"):
            original = source(name)
            projected = off_source(name, original)
            self.assertEqual(off_source(name, projected), projected, name)
            self.assertNotIn("DOUBLE_GROW_V2", projected, name)
            self.assertNotIn("DOUBLE_GROW", projected, name)
            self.assertNotIn('"double_grow"', projected, name)
            self.assertNotIn("double_grow_v2", projected, name)
        self.assertNotIn(b'name = "double_grow"', off_config_bytes("info.nut"))


if __name__ == "__main__":
    unittest.main()
