"""DOUBLE-GROW source contracts: opt-in, deferred eligibility and exact OFF.

Physical geometry, PBS and train movement still require an OpenTTD smoke.
"""

from pathlib import Path
import re
import unittest

from double_grow_off import INSERTIONS, off_source
from test_rail_search_prio_20261103 import off_config_bytes


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


class TestDoubleGrowContracts(unittest.TestCase):
    def read(self, name):
        return (AI / name).read_text(encoding="utf8")

    def geometry_function(self, name):
        """Extract a top-level Squirrel function for order-sensitive contracts."""
        source = self.read("double_grow_geometry.nut")
        header = f"function {name}("
        start = source.find(header)
        self.assertGreaterEqual(start, 0, f"missing {name}")
        following = re.search(r"(?m)^function [A-Za-z_]\w*\(", source[start + len(header):])
        end = start + len(header) + following.start() if following else len(source)
        return source[start:end]

    def test_setting_is_entirely_opt_in(self):
        for name in ("globals_pre.nut", "settings.nut", "info.nut"):
            source = self.read(name)
            self.assertIn("DOUBLE_GROW" if name != "info.nut" else 'name = "double_grow"', source)
            self.assertEqual(off_source(name, source), off_source(name, off_source(name, source)))
        info = self.read("info.nut")
        block = "".join(INSERTIONS["info.nut"])
        self.assertIn("easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0", block)
        self.assertIn('DOUBLE_GROW <- false;', self.read("globals_pre.nut"))
        self.assertIn('AIController.GetSetting("double_grow") == 1', self.read("settings.nut"))

    def test_legacy_projection_unchanged(self):
        for name in INSERTIONS:
            source = self.read(name)
            clean = off_source(name, source)
            self.assertEqual(clean, off_source(name, clean))
            self.assertNotIn("DOUBLE_GROW", clean)
            self.assertNotIn('"double_grow"', clean)
        # The established legacy chain must understand the additional ON layer.
        self.assertNotIn(b'name = "double_grow"', off_config_bytes("info.nut"))

    def test_deferred_selector_does_not_claim_search_slot(self):
        source = self.read("double_grow.nut")
        self.assertIn("if (!DOUBLE_GROW", source)
        self.assertIn("owner._railSearch != null", source)
        self.assertIn("now - line.buildDate < 365", source)
        self.assertIn("line.lastProfit <= 0", source)
        self.assertIn("AIStation.GetCargoWaiting", source)
        self.assertIn("OpexDoubleGrowGeometry(owner, line)", source)
        self.assertNotIn("_startRailSearch(", source)
        self.assertNotIn("_startRailUpgradeSearch(", source)
        self.assertNotIn("_railSearch =", source)
        self.assertIn("if (DOUBLE_GROW && OpexDoubleGrowSelect(this, year)) return;",
                      self.read("task_rail.nut"))

    def test_fleet_requires_directional_certification(self):
        source = self.read("double_grow.nut")
        marker = 'if (("doubleGrowDirectional" in line) && line.doubleGrowDirectional)'
        self.assertIn(marker, source)
        self.assertLess(source.index(marker), source.index("OpexDoubleGrowFleet(owner, line)"))

    def test_railtype_selection_checks_actual_type(self):
        for name in ("double_grow_geometry.nut", "double_grow_fleet.nut"):
            source = self.read(name)
            self.assertNotIn("if (!AIRail.SetCurrentRailType(", source)
            self.assertIn("AIRail.GetCurrentRailType() != expectedType", source)

    def test_primary_corridor_stations_and_depot_are_forbidden(self):
        plan = self.geometry_function("OpexDoubleGrowPlan")
        clear = self.geometry_function("OpexDoubleGrowClear")
        self.assertIn("foreach (tile in route) forbidden[tile] <- true;", plan)
        self.assertIn("foreach (plan in [a, b])", plan)
        self.assertIn("forbidden[plan.anchor + i * plan.step] <- true;", plan)
        self.assertIn("forbidden[line.depot] <- true;", plan)
        self.assertIn("AIRail.GetRailDepotFrontTile(line.depot)", plan)
        self.assertIn("forbidden[front] <- true;", plan)
        self.assertIn("if (tile in forbidden)", clear)
        for cause in ("primary_depot", "primary_depot_front",
                      "primary_station", "primary_track"):
            self.assertIn(f'"{cause}"', clear)
        self.assertIn("OpexDoubleGrowClear(trace.tiles, structures, forbidden,", plan)
        self.assertIn("pA, pB, diag, route, line.depot)", plan)

    def test_rejection_diagnostics_keep_first_cause_index_and_tile(self):
        reject = self.geometry_function("OpexDoubleGrowDiagnosticReject")
        log = self.geometry_function("OpexDoubleGrowPlanLog")
        window = self.geometry_function("OpexDoubleGrowTraceWindow")
        clear = self.geometry_function("OpexDoubleGrowClear")
        self.assertIn('!(reason + "_detail" in diag)', reject)
        for field in ('reason + "_detail"', 'reason + "_idx"', 'reason + "_tile"'):
            self.assertIn(field, reject)
            self.assertIn(field, log)
        self.assertIn("return false;", reject)
        for cause in ("trace_window_fail", "trace_start_mismatch", "trace_end_mismatch"):
            self.assertIn(f'"{cause}"', window)
            self.assertIn(f'"{cause}"', log)
        for cause in ("clear_short", "clear_forbidden"):
            self.assertIn(f'"{cause}"', clear)
            self.assertIn(f'"{cause}"', log)
        # The dry-run explains V190 null, but never certifies a build.
        plan = self.geometry_function("OpexDoubleGrowPlan")
        self.assertLess(plan.index("if (trace == null)"),
                        plan.index("OpexDoubleGrowTraceDryIssue("))
        self.assertLess(plan.index("OpexDoubleGrowTraceDryIssue("),
                        plan.index("OpexDoubleGrowClear("))

    def test_fail_closed_before_spending_and_live_line_commit(self):
        plan = self.geometry_function("OpexDoubleGrowPlan")
        geometry = self.geometry_function("OpexDoubleGrowGeometry")
        self.assertLess(plan.index("OpexDoubleGrowTraceWindow("),
                        plan.index("OpexV190TraceParallelTrack("))
        self.assertLess(plan.index("OpexDoubleGrowClear("),
                        plan.index("OpexTestRailTrack("))
        self.assertLess(plan.index("if (native.failed > 0)"),
                        plan.index("return { tiles1 = route"))
        self.assertIn('return OpexDoubleGrowReject("NO_PARALLEL_BAND", line);', geometry)
        self.assertIn("local stagedLine = null;", geometry)
        self.assertIn("stagedLine = clone line;", geometry)
        self.assertIn("OpexDoubleGrowFleetFinalize(owner, line, stagedLine)", geometry)
        failure = geometry.index("if (!ok) {")
        committed = geometry.index('line.rawset("tiles1", route)')
        self.assertLess(failure, committed)
        self.assertIn("OpexDoubleGrowRollbackGeometry(geometry)", geometry[failure:committed])
        self.assertNotIn("line.rawset(", geometry[:failure])

    def test_rollback_cannot_demolish_primary_or_foreign_infrastructure(self):
        rollback = self.geometry_function("OpexDoubleGrowRollbackGeometry")
        self.assertNotIn("OpexV190RollbackDoubleTrack(", rollback)
        self.assertIn("(t in geometry.forbidden)", rollback)
        self.assertIn("AITile.GetOwner(t) != own", rollback)
        self.assertIn("AIStation.GetStationID(t) != stationId", rollback)
        self.assertIn("AIRail.RemoveRailStationTileRectangle(t, t, false)", rollback)
        self.assertIn("return ok;", rollback)

    def test_no_global_or_unbounded_astar_in_deferred_geometry(self):
        geometry = self.read("double_grow_geometry.nut")
        self.assertNotRegex(geometry, r"\b(?:OpexSearchPath|_startRailSearch|_startRailUpgradeSearch)\s*\(")
        self.assertNotRegex(geometry, r"\bwhile\s*\(\s*true\s*\)")
        self.assertNotIn("this._railSearch =", geometry)
        self.assertNotIn("OpexBuildTrack(", geometry)
        # When a segment-local repair is introduced, insist on both a local
        # geometry envelope and an operation/state cap; no second full-line A*.
        helpers = re.findall(
            r"(?m)^function (OpexDoubleGrow\w*(?:LocalAStar|LocalRepair|SegmentAStar|LocalDetour)\w*)\(",
            geometry)
        if not helpers:
            self.skipTest("segment-local A* not implemented: global/unbounded search forbidden")
        for helper in helpers:
            body = self.geometry_function(helper)
            self.assertRegex(body, r"(?i)(?:budget|opcap|maxops|maxstates|iterations)")
            self.assertRegex(body, r"(?i)(?:segment|window|maxlen|maxdist|radius)")

    def test_side_switch_requires_safe_trace_and_native_validation(self):
        geometry = self.read("double_grow_geometry.nut")
        plan = self.geometry_function("OpexDoubleGrowPlan")
        self.assertIn("if (OpexPlanHitsSet(pA, forbidden))", plan)
        self.assertIn("if (OpexPlanHitsSet(pB, pads))", plan)
        self.assertIn("OpexDoubleGrowClear(", plan)
        self.assertIn("OpexTestRailTrack(", plan)
        helpers = re.findall(
            r"(?m)^function (OpexDoubleGrow\w*(?:SideSwitch|SwitchSide)\w*)\(",
            geometry)
        if not helpers:
            self.assertIn("dxB * oyB - dyB * oxB != side", plan)
            self.skipTest("side-switch with two turnouts not yet implemented")
        # New side-switch routes must still flow through the same fail-closed
        # forbidden-tile and native track checks before a geometry is returned.
        self.assertLess(plan.index("OpexDoubleGrowClear("),
                        plan.index("OpexTestRailTrack("))
        self.assertLess(plan.index("OpexTestRailTrack("),
                        plan.index("return { tiles1 = route"))


if __name__ == "__main__":
    unittest.main()
