"""Static, fail-closed tests for V190-FIX2. No engine/WSL/Docker is invoked."""

from pathlib import Path
import re
import unittest

from v190_fix_directional_legacy import off_source
from test_rail_search_prio_20261103 import off_config_bytes
from test_rail_search_prio_source_off import off_search_prio_source


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai/OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class V190FixDirectionalTests(unittest.TestCase):
    def test_flag_is_inert_in_all_profiles_and_loaded_once(self):
        info = read("info.nut")
        self.assertEqual(info.count('name = "v190_fix_directional"'), 1)
        block = info.split('name = "v190_fix_directional"', 1)[1].split('flags = AICONFIG_BOOLEAN', 1)[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{difficulty}_value = 0", block)
        self.assertIn("V190_FIX_DIRECTIONAL <- false;", read("globals_pre.nut"))
        self.assertEqual(read("settings.nut").count('GetSetting("v190_fix_directional")'), 1)
        self.assertEqual(read("main.nut").count('require("v190_fix_directional.nut");'), 1)

    def test_frozen_off_projection_is_exact_and_idempotent(self):
        for name in ("info.nut", "globals_pre.nut", "settings.nut", "main.nut",
                     "builder_rail.nut", "task_rail.nut"):
            with self.subTest(name=name):
                source = read(name)
                old = off_source(name, source)
                self.assertNotEqual(source, old)
                self.assertEqual(old, off_source(name, old))
                self.assertNotIn('v190_fix_directional', old)
                self.assertNotIn("v190Directional", old)

    def test_partial_hunks_fail_closed(self):
        self.assertRaises(AssertionError, off_source, "builder_rail.nut",
                          read("builder_rail.nut").replace("OpexV190Fix2BuildDirectional(",
                                                           "OpexV190Fix2BROKEN(", 1))
        self.assertRaises(AssertionError, off_source, "task_rail.nut",
                          read("task_rail.nut").replace('"phase=commission line="',
                                                        '"phase=unknown line="', 1))

    def test_legacy_v190_and_rail_depot_signal_still_project_off(self):
        from v190_fix_legacy import off_source as v190_original
        from rail_depot_signal_legacy import off_source as depot_original, off_sha256
        from rail_depot_signal_legacy import FIXTURE
        for name in ("builder_rail.nut", "task_rail.nut"):
            original = read(name)
            old = v190_original(name, original)
            self.assertEqual(old, v190_original(name, old))
        for name, expected in FIXTURE["baseline_sha256"].items():
            with self.subTest(name=name):
                before_depot = off_search_prio_source(name, read(name))
                if name in ("info.nut", "globals_pre.nut", "settings.nut"):
                    before_depot = off_config_bytes(name, before_depot.encode("utf-8")).decode("utf-8")
                self.assertEqual(off_sha256(name, before_depot), expected)
                projected = depot_original(name, before_depot)
                self.assertEqual(projected, depot_original(name, projected))

    def test_true_one_direction_each_way_and_two_crossovers(self):
        code = read("v190_fix_directional.nut")
        self.assertIn("function OpexV190Fix2BuildDirectional(", code)
        self.assertIn("OpexV190VerifyIndependentDouble(line, depot1, depot2)", code)
        self.assertIn("local switchA = null;", code)
        self.assertIn("local switchB = null;", code)
        self.assertIn("OpexV190Fix2TrySwitch(tiles2[switchA.i2 - 1], tiles2[switchA.i2],", code)
        self.assertIn("OpexV190Fix2TrySwitch(tiles1[switchB.i1 + 1], tiles1[switchB.i1],", code)
        self.assertIn('OpexV190Fix2PlaceSignalWindow(tiles1, k,', code)
        self.assertIn('OpexV190Fix2PlaceSignalWindow(tiles2, k,', code)
        self.assertIn('1, 1, placedSignals);', code)
        self.assertIn('-1, -1, placedSignals);', code)
        self.assertIn('AIRail.BuildSignal(tile, front, AIRail.SIGNALTYPE_PBS_ONEWAY)', code)
        self.assertIn('local front = toward > 0 ? prev : next;', code)
        self.assertNotIn('local front = toward > 0 ? next : prev;', code)
        self.assertIn('function OpexV190Fix2PairSafe(', code)
        self.assertIn('foreach (a in candidatesA)', code)
        self.assertIn('foreach (b in candidatesB)', code)
        self.assertIn('OpexV190Fix2PairSafe(a, b, tiles1, tiles2, clear)', code)
        self.assertIn('function OpexV190Fix2PlaceSignalWindow(', code)
        self.assertIn('k = nextSignal + spacing;', code)
        self.assertIn('k = nextSignal - spacing;', code)
        self.assertNotIn('AIOrder.ShareOrders(', code)
        self.assertNotIn('SIGNALTYPE_NORMAL', code)

    def test_fail_closed_on_orders_switch_geometry_and_pbs(self):
        code = read("v190_fix_directional.nut")
        for snippet in (
            'AIOrder.GetOrderCount(train) != 2',
            'AIOrder.IsGotoStationOrder(train, 0)',
            'AIOrder.IsGotoStationOrder(train, 1)',
            'AIStation.GetStationID(AIOrder.GetOrderDestination(train, 0)) != stationA',
            'AIStation.GetStationID(AIOrder.GetOrderDestination(train, 1)) != stationB',
            'OpexTileTrackCount(tile) != 1',
            'AITile.GetOwner(tile) != AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)',
            'AIRail.GetSignalType(fromTile, fromNext)',
            'AIMap.DistanceManhattan(fromTile, toTile)',
            'OpexV190Fix2SwitchConnected(',
            'b.i1 - a.i1 <= 2 * clear + 4',
            'b.i2 - a.i2 <= 2 * clear + 4',
            'candidatesA.len() < candidateLimit',
            'candidatesB.len() < candidateLimit',
            'OpexV190Fix2Rollback(placedRails, placedSignals);',
            '"DIRECTIONAL_PBS_BUILD"',
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, code)
        self.assertEqual(code.count('OpexV190Fix2Rollback(placedRails, placedSignals);'), 3)
        self.assertIn('for (local k = placedRails.len() - 1; k >= 0; k--)', code)

    def test_diagonal_switch_never_uses_an_occupied_middle_tile(self):
        code = read("v190_fix_directional.nut")
        strict = code.split("function OpexV190Fix2TrySwitch(", 1)[1].split(
            "/* Renvoie null", 1)[0]
        self.assertIn('AITile.IsBuildable(mid)', strict)
        self.assertIn('AITile.HasTransportType(mid, AITile.TRANSPORT_RAIL)', strict)
        self.assertIn('AITile.GetSlope(mid) != AITile.SLOPE_FLAT', strict)
        self.assertIn('OpexV190Fix2Rollback(subRecords, []);', strict)
        self.assertIn('foreach (rec in subRecords) placedRails.append(rec);', strict)
        self.assertIn('OpexV181TryBuildSwitchSegment(fromTile, mid, toTile,', strict)
        self.assertEqual(code.count('OpexV190Fix2TrySwitch('), 5)  # definition, test A/B, build A/B

    def test_signal_orientation_is_verified_after_build(self):
        code = read("v190_fix_directional.nut")
        section = code.split('function OpexV190Fix2PlaceSignal(', 1)[1].split(
            'function OpexV190Fix2BuildDirectional(', 1)[0]
        self.assertIn('AIRail.GetSignalType(tile, front) != AIRail.SIGNALTYPE_PBS_ONEWAY', section)
        self.assertIn('AIRail.RemoveSignal(tile, front);', section)
        self.assertIn('placedSignals.append({ tile = tile, front = front });', section)
        self.assertLess(section.index('AIRail.GetSignalType(tile, front) != AIRail.SIGNALTYPE_PBS_ONEWAY'),
                        section.index('placedSignals.append({ tile = tile, front = front });'))

    def test_waypoints_force_station_to_correct_direction_in_both_trains(self):
        code = read("v190_fix_directional.nut")
        self.assertIn('function OpexV190Fix2BuildWaypoint(', code)
        self.assertIn('AIRail.BuildRailWaypoint(tile)', code)
        self.assertIn('tracks != AIRail.RAILTRACK_NW_SE && tracks != AIRail.RAILTRACK_NE_SW', code)
        self.assertIn('AIRail.GetSignalType(tile, prev) != AIRail.SIGNALTYPE_NONE', code)
        self.assertIn('AIRail.GetSignalType(tile, next) != AIRail.SIGNALTYPE_NONE', code)
        self.assertIn('OpexV190Fix2BuildWaypoint(tiles1, switchA.i1 + clear,', code)
        self.assertIn('OpexV190Fix2BuildWaypoint(tiles2, switchB.i2 - clear,', code)
        self.assertIn('AIOrder.InsertOrder(train, 1, waypointAB, AIOrder.OF_NONE)', code)
        self.assertIn('AIOrder.AppendOrder(train, waypointBA, AIOrder.OF_NONE)', code)
        self.assertIn('AIOrder.IsGotoWaypointOrder(train, 1)', code)
        self.assertIn('AIOrder.IsGotoWaypointOrder(train, 3)', code)
        self.assertIn('AIStation.GetStationID(AIOrder.GetOrderDestination(train, 2)) != stationB', code)
        self.assertIn('AIWaypoint.GetWaypointID(AIOrder.GetOrderDestination(train, 3)) != waypointIdBA', code)
        self.assertIn('" waypoint_ab=" + waypointAB + " waypoint_ba=" + waypointBA', code)

    def test_waypoint_failure_restores_orders_and_rails_before_fallback(self):
        code = read("v190_fix_directional.nut")
        self.assertIn('function OpexV190Fix2RestoreOrders(', code)
        self.assertIn('AIOrder.RemoveOrder(train, 3)', code)
        self.assertIn('AIOrder.RemoveOrder(train, 1)', code)
        self.assertIn('AIRail.RemoveRailWaypointTileRectangle(tile, tile, true)', code)
        self.assertIn('"DIRECTIONAL_WAYPOINT_ORDERS"', code)
        self.assertIn('"DIRECTIONAL_GUIDANCE_ROLLBACK_FAILED"', code)
        self.assertIn('OpexV190Fix2RollbackGuidance(line.vehicles, placedWaypoints,', code)
        body = code.split('local placedWaypoints = [];', 1)[1]
        self.assertLess(body.index('OpexV190Fix2GuideOrders('), body.index('"phase=directional ok=1"'))
        self.assertLess(body.index('OpexV190Fix2RollbackGuidance('), body.index('"phase=directional ok=1"'))

    def test_forbid_90_turns_checked_with_outer_tiles_on_both_switches(self):
        code = read("v190_fix_directional.nut")
        self.assertIn('function OpexV190Fix2TrackBit(', code)
        self.assertIn('function OpexV190Fix2TurnsSafe(', code)
        self.assertIn('if (farPrev == null || farNext == null) return false;', code)
        self.assertIn('OpexV190Fix2TurnsSafe([farPrev, fromPrev, fromTile,', code)
        self.assertIn('OpexV190Fix2TurnsSafe([farPrev, fromPrev, fromTile, mid,', code)
        self.assertIn('tiles2[i2 - 2], tiles1[i1 + 2]', code)
        self.assertIn('tiles1[i1 + 2], tiles2[i2 - 2]', code)
        self.assertIn('tiles2[switchA.i2 - 2]', code)
        self.assertIn('tiles1[switchB.i1 + 2]', code)
        self.assertIn('((prevBit == 4 || prevBit == 8) && (bit == 16 || bit == 32))', code)
        self.assertIn('((prevBit == 16 || prevBit == 32) && (bit == 4 || bit == 8))', code)
        # Reproduit l'enchainement du retour B24 -> voie2 depuis le quai bas
        # de la graine 512 (save b471c6fb, pf.forbid_90_deg=1).
        path = [(135, 88), (134, 88), (134, 89),
                (135, 89), (135, 90), (134, 90)]
        def bit(a, b, c):
            sides = {(a[0] - b[0], a[1] - b[1]),
                     (c[0] - b[0], c[1] - b[1])}
            return {
                frozenset({(-1, 0), (1, 0)}): 1,
                frozenset({(0, -1), (0, 1)}): 2,
                frozenset({(-1, 0), (0, -1)}): 4,
                frozenset({(1, 0), (0, 1)}): 8,
                frozenset({(0, -1), (1, 0)}): 16,
                frozenset({(-1, 0), (0, 1)}): 32,
            }.get(frozenset(sides), 0)
        sequence = [bit(path[i - 1], path[i], path[i + 1])
                    for i in range(1, len(path) - 1)]
        self.assertEqual(sequence, [8, 16, 32, 4])
        forbidden = {1: 2, 2: 1, 4: 48, 8: 48, 16: 12, 32: 12}
        self.assertTrue(any(sequence[i + 1] & forbidden[sequence[i]]
                            for i in range(len(sequence) - 1)))

    def test_v233_and_independent_path_are_preserved(self):
        builder = read("builder_rail.nut")
        self.assertIn("!OpexV233LIs(candidate) &&\n                V190_FIX_DIRECTIONAL && V197_GUIDED_DOUBLE", builder)
        self.assertIn("? OpexConvertDoubleTrackToLoop(loopLine, loopDiag)", builder)
        self.assertIn(": OpexV190VerifyIndependentDouble(loopLine, depot, depot2));", builder)
        self.assertIn("if (!OpexV233LIs(candidate) && !v190Directional) result.v190Independent <- true;", builder)
        self.assertIn("if (v190Directional) result.v190Directional <- true;", builder)
        self.assertIn("result.v181Loop <- !(\"v190Independent\" in result) || !result.v190Independent;", builder)

    def test_causal_logging_and_line_persistence(self):
        task = read("task_rail.nut")
        self.assertIn('v190Directional = ("v190Directional" in result)', task)
        self.assertIn('"phase=commission line="', task)
        for item in ('" loco1="', '" loco2="', '" a1="', '" b2="', '" orders1="', '" orders2="'):
            self.assertIn(item, task)
        module = read("v190_fix_directional.nut")
        self.assertIn('"phase=directional ok=1"', module)
        self.assertIn('" track1=A_to_B track2=B_to_A"', module)

    def test_new_squirrel_has_no_common_parser_traps(self):
        module = read("v190_fix_directional.nut")
        self.assertNotIn('.find(', module)
        self.assertNotIn('function(', module)
        self.assertNotIn('local base =', module)
        self.assertNotIn('local clone =', module)
        self.assertEqual(module.count('{'), module.count('}'))


if __name__ == "__main__":
    unittest.main()
