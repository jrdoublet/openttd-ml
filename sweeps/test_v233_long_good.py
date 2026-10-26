"""V233L source contracts and edge-case fixtures; no Squirrel VM/game invoked.

OFF projection pins original bytes; the small independent observation model
checks calendar/zero/missing-data cases, not execution timing or profitability.
"""
import hashlib
from pathlib import Path
import re
import unittest
from types import SimpleNamespace

from po01c_generate import generated
from test_v261_forum_behaviours import body, source, uncomment
from v233_long_good_legacy import FIXTURE, off_source

AI = Path(__file__).resolve().parents[1] / "ai/OpexAI"


def observe(samples):
    """Six real observations in seven calendar months; no missing value imputed."""
    window = []
    last = None
    for month, production, transported in samples:
        if last is not None and month <= last:
            continue
        window.append((month, production, max(0, production - transported)))
        window = [sample for sample in window if sample[0] >= month - 6][-6:]
        last = month
    durable = (len(window) == 6 and sum(p > 0 for _, p, _ in window) >= 2
               and sum(p for m, p, _ in window if m >= last - 2) > 0)
    return window, durable, sum(r for _, _, r in window) // len(window) if window else 0


def fresh(month, now):
    return 1 <= now - month <= 3 and month >= 0


def reject_reasons(samples, now, *, input_live=True, export_exists=False, distance=200):
    """Independent gate expectations, including simultaneous source failures."""
    window, durable, monthly = observe(samples)
    reasons = set()
    if not durable:
        reasons.add("window")
    if not window or not fresh(window[-1][0], now):
        reasons.add("stale")
    if not input_live:
        reasons.add("input_not_live")
    if export_exists:
        reasons.add("export_exists")
    if monthly <= 0:
        reasons.add("no_residual")
    if not reasons and not 150 <= distance <= 300:
        reasons.add("distance")
    return reasons


class V233LongGoodContracts(unittest.TestCase):
    def test_track3_budget_uses_real_length_with_bounded_local_share(self):
        budget = body("v233_long_good.nut", "OpexV233LDoubleBudget")
        expr = budget.split('return ', 1)[1].split(';', 1)[0]
        for length, expected in ((0, 8000), (125, 8000), (130, 8320),
                                 (250, 16000), (375, 24000), (2000, 24000)):
            self.assertEqual(eval(expr, {"__builtins__": {}, "min": min, "max": max},
                                  {"routeLength": length}), expected)
        wrapper = body("v233_long_good.nut", "OpexV233LPlanDoubleTrack")
        self.assertIn('routeLength += AIMap.DistanceManhattan(tiles[i - 1], tiles[i])', wrapper)
        planner = body("builder_rail.nut", "OpexV190PlanDoubleTrack")
        self.assertIn('(iterationBudget / 2) - acc.iterations', planner)
        self.assertIn('acc.iterations += repaired.iterations', planner)
        self.assertIn('iterationBudget -= acc.iterations', planner)
        self.assertIn('if (v233Context != null) acc.iterations += search.iterations', planner)

    def test_track3_launch_reservation_never_masks_primary_interfaces(self):
        reserve = body("v233_long_good.nut", "OpexV233LReserveDouble")
        corridor = body("v233_long_good.nut", "OpexV233LCorridor")
        for token in ('front in primary', 'after in primary', 'front in platforms', 'after in platforms',
                      'local testMode = AITestMode()', 'if (!lenient) return null;',
                      'AIRail.BuildRail(p.station_exit, p.lead, front)',
                      'AIRail.BuildRail(p.lead, front, after)'):
            self.assertIn(token, corridor)
        self.assertIn('reason=LAUNCH', reserve)
        self.assertIn('OpexV233LKeepLaunch(', reserve)
        # All four orientations, including negative map deltas: both steps
        # must extend away from the platform, never wrap to another map row.
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            exit_tile = (20, 20)
            lead = (20 + dx, 20 + dy)
            front = (lead[0] + dx, lead[1] + dy)
            after = (lead[0] + 2 * dx, lead[1] + 2 * dy)
            self.assertEqual(abs(after[0] - exit_tile[0]) + abs(after[1] - exit_tile[1]), 3)
            self.assertEqual(len({exit_tile, lead, front, after}), 4)

    def test_track3_bridge_probe_matches_quote_and_build_selection(self):
        probe = body("v233_long_good.nut", "OpexV233LBridgeProbe")
        for token in ('AIMap.DistanceManhattan(fromTile, toTile) + 1', 'AIBridgeList_Length(length)',
                      'OpexBridgeSortBySpeed(bridges)', 'bridges.Begin()', 'local testMode = AITestMode()',
                      'AIError.ERR_AREA_NOT_CLEAR', 'bridge_type=', 'slope=', 'owner=',
                      'phase=bridge_span', 'reported < 8'):
            self.assertIn(token, probe)
        self.assertLess(probe.index('error = AIError.GetLastError()'), probe.index('AITile.GetSlope'))
        for fn in ('OpexBuildTrack', 'OpexTestRailTrack', 'OpexSimulateRailInfraCost'):
            code = body("builder_rail.nut", fn)
            self.assertIn('AIBridgeList_Length(AIMap.DistanceManhattan(cur, next) + 1)', code)
            self.assertIn('OpexBridgeSortBySpeed(bridges)', code)
            self.assertIn('AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next)', code)

    def test_track3_structure_failure_defers_to_local_repair_before_full_search(self):
        trace = body("builder_rail.nut", "OpexV190TraceParallelTrack")
        self.assertRegex(trace, r'if \(v233Context != null\) \{\s*structKind = plannedKind')
        planner = body("builder_rail.nut", "OpexV190PlanDoubleTrack")
        self.assertLess(planner.index('OpexV233LRepairParallel('), planner.index('OpexTestRailTrack('))
        self.assertLess(planner.index('OpexV233LRepairParallel('), planner.index('OpexSearchPath('))
        repair = body("v233_long_good.nut", "OpexV233LRepairParallel")
        for token in ('repairs <= 6', 'foreach (radius in [4, 8, 16])', 'AIController.GetTick() >= deadline',
                      'budget - result.iterations', 'result.iterations += search.iterations',
                      'if (search.path == null || search.path == false) continue;',
                      'OpexResolveSearchTiles(search)', 'OpexResolveSearchStructures(search)',
                      'OpexV233LParallelIssue(candidate, patched, blocked)',
                      'OpexJoinPathIsDedicated(joined)'):
            self.assertIn(token, repair)
        # No partial construction: local searches are through the current
        # harness helpers, all native commands in the issue scanner are tests.
        for token in ('DemolishTile', 'RemoveRail', 'OpexBuildTrack', 'BuildVehicle'):
            self.assertNotIn(token, repair)
        self.assertIn('local testMode = AITestMode()', body("v233_long_good.nut", "OpexV233LParallelIssue"))

    def test_track3_splice_preserves_direction_and_rejects_tail_collisions(self):
        code = body("v233_long_good.nut", "OpexV233LSpliceParallel")
        # Execute the actual interface guard on fixtures; not a Squirrel VM.
        guard = re.search(r'if \((.*?)\) return null;', code, re.S)[1]
        guard = guard.replace('tail.len()', 'len(tail)').replace('tail.top()', 'tail[-1]').replace('||', ' or ')
        guard = '(' + guard + ')'
        tiles = list(range(10))
        valid = [2, 3, 30, 31, 6, 7]
        for tail, rejected in ((valid, False), ([2, 30, 31, 6, 7], True),
                               ([2, 3, 30, 31, 7], True), ([3, 2, 30, 6, 7], True),
                               ([2, 3, 6], True)):
            self.assertEqual(eval(guard, {"__builtins__": {}, "len": len},
                                  dict(tiles=tiles, tail=tail, left=2, right=7)), rejected)
        self.assertIn('i < left', code)
        self.assertIn('i = right + 1', code)
        self.assertIn('if (t in seen || t in forbidden) return null', code)
        for tail, forbidden, accepted in ((valid, {99}, True), (valid, {30}, False),
                                          ([2, 3, 0, 31, 6, 7], set(), False),
                                          ([2, 3, 30, 30, 6, 7], set(), False)):
            joined = tiles[:2] + tail + tiles[8:]
            self.assertEqual(len(joined) == len(set(joined)) and not set(joined) & forbidden, accepted)

    def test_track3_local_interfaces_and_untouched_structures_are_preserved(self):
        repair = body("v233_long_good.nut", "OpexV233LRepairParallel")
        for token in ('AIMap.DistanceManhattan(tiles[left], tiles[left + 1]) != 1',
                      'AIMap.DistanceManhattan(tiles[right - 1], tiles[right]) != 1',
                      'if (i < left || i > right) ignored.append(tiles[i]);',
                      'OpexV233LFence(tiles, left, right, 20, ignored)',
                      'station_exit = tiles[left], lead = tiles[left + 1]',
                      'station_exit = tiles[right], lead = tiles[right - 1]',
                      's.from == joined[i] && s.to == joined[i + 1]',
                      'if (t != p.station_exit && !(t in blocked)) blocked[t] <- true'):
            self.assertIn(token, repair)
        issue = body("v233_long_good.nut", "OpexV233LParallelIssue")
        for token in ('cur - prev != step', 'tiles[i + 2] - next != step', '"RAMP_AXIS"',
                      'AITunnel.GetOtherTunnelEnd(cur) == next && AITunnel.BuildTunnel'):
            self.assertIn(token, issue)

    def test_track3_nopa_diagnostics_report_native_exits_and_closed_tiles(self):
        head = body("v233_long_good.nut", "OpexV233LSearchHeadLog")
        for token in ('if (!DECISION_LOG) return;', 'local testMode = AITestMode()',
                      'lead_forbidden=', 'next_rail=', 'native=', 'error=', 'side='):
            self.assertIn(token, head)
        planner = body("builder_rail.nut", "OpexV190PlanDoubleTrack")
        self.assertIn('OpexV233LSearchHeadLog(v233Context, p, "A", forbidden)', planner)
        self.assertIn('OpexV233LSearchHeadLog(v233Context, p, "B", forbidden)', planner)

    def test_track3_error_260_is_area_not_clear_and_slide_keeps_builder_bridge_type(self):
        probe = body("v233_long_good.nut", "OpexV233LBridgeProbe")
        self.assertIn("error == AIError.ERR_AREA_NOT_CLEAR ? 1 : 0", probe)
        self.assertIn("reason=BRIDGE_ALT", probe)
        self.assertLess(probe.index("error = AIError.GetLastError()"), probe.index("bridges.Next()"))
        self.assertIn("return ok ? 0 : error", probe)
        issue = body("v233_long_good.nut", "OpexV233LParallelIssue")
        self.assertIn("ok = error == 0", issue)
        slide = body("v233_long_good.nut", "OpexV233LSlideBridge")
        self.assertIn("if (endOff - startOff < 2) continue;", slide)
        self.assertIn("for (local k = 0; k < seq.len() - 1; k++)", slide)
        self.assertIn("if (!built || !bridged)", slide)
        self.assertIn("OpexV190MakeTile(origin, udx * off, udy * off)", body("v233_long_good.nut", "OpexV233LCollectAxis"))
        self.assertIn("bridges.Begin()", slide)
        self.assertNotIn("DemolishTile", slide)
        # Same-length shifts first, then a shorter or longer span. Heads stay
        # on the bridge axis; a negative step must not wrap to another row.
        nudges = ((1, 1), (-1, -1), (4, 4), (1, 0), (0, -1), (-2, -1))
        for start_off, end_delta in nudges:
            dist = 5
            end_off = dist + end_delta
            self.assertGreaterEqual(end_off - start_off, 2)
            approach = list(range(-1, start_off - 1, -1)) if start_off < -1 else list(range(-1, start_off + 1))
            step = 1 if end_off <= dist + 1 else -1
            landing = list(range(end_off, dist + 1 + step, step))
            seq = approach + landing
            self.assertEqual(seq[0], -1)
            self.assertEqual(seq[-1], dist + 1)
            self.assertEqual(len(seq), len(set(seq)))
        repair = body("v233_long_good.nut", "OpexV233LRepairParallel")
        self.assertLess(repair.index("OpexV233LSlideBridge("), repair.index("OpexSearchPath("))
        self.assertIn("slid.tiles[nextIssue] != oldHead", repair)
        self.assertIn("reason=SLIDE_KEEP", repair)
        self.assertIn("if (nextIssue < 0) {\n            result.trace = trace;\n            return result;", repair)
        fence = body("v233_long_good.nut", "OpexV233LFence")
        self.assertIn("if (!(tiles[i] in keep)) keep[tiles[i]] <- true", fence)
        self.assertIn("V294_RAIL_BRIDGE_LEN > 1 ? V294_RAIL_BRIDGE_LEN : 6", fence)
        self.assertIn("if (insideY && x >= inMinX && x <= inMaxX) continue;", fence)
        self.assertIn("if (!(t in keep)) ignored.append(t)", fence)
        # Last free tile is the inner edge. Pathfinder jumps i < max length,
        # so a band of that thickness still contains the landing.
        for jump in (2, 19, 20):
            inner, thick = 20, 20
            landing = inner + jump
            self.assertTrue(inner < landing <= inner + thick)

    def test_track3_launch_corridor_and_slot_inserts_do_not_throw(self):
        reserve = body("v233_long_good.nut", "OpexV233LReserveDouble")
        self.assertIn("[-dy, dx]", reserve)
        self.assertIn("[dy, -dx]", reserve)
        self.assertIn("reason=LAUNCH_NONE", reserve)
        self.assertLess(reserve.index("[dx, dy]"), reserve.index("[-dy, dx]"))
        self.assertIn("if (!(tile in primary)) primary[tile] <- true", reserve)
        planner = body("v233_long_good.nut", "OpexV233LPlanDoubleTrack")
        self.assertIn("if (!(t in forbidden)) forbidden[t] <- true", planner)
        self.assertIn("if (!(tile in forbidden)) forbidden[tile] <- true", planner)

    def test_track4_after_tile_is_proved_without_moving_the_primary_plan(self):
        corridor = body("v233_long_good.nut", "OpexV233LCorridor")
        self.assertIn("AIRail.BuildRail(front, after, beyond)", corridor)
        self.assertLess(corridor.index("AIRail.BuildRail(p.lead, front, after)"),
                        corridor.index("AIRail.BuildRail(front, after, beyond)"))
        self.assertLess(corridor.index("local testMode = AITestMode()"),
                        corridor.index("AIRail.BuildRail(front, after, beyond)"))
        self.assertLess(corridor.index("AIRail.BuildRail(front, after, beyond)"),
                        corridor.index("if (!lenient) return null;"))
        self.assertIn("beyond == front || beyond == after", corridor)
        # Rail on `after` needs a third tile one step further, still off the platform.
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            lead = (20 + dx, 20 + dy)
            after = (lead[0] + 2 * dx, lead[1] + 2 * dy)
            beyond = (lead[0] + 3 * dx, lead[1] + 3 * dy)
            self.assertEqual(abs(beyond[0] - after[0]) + abs(beyond[1] - after[1]), 1)
            self.assertEqual(len({(20, 20), lead, after, beyond}), 4)
        plans = body("v233_long_good.nut", "OpexV233LPlatformPlans")
        self.assertIn('if (validB.len() > 0) { validA.append(p); break; }', plans)
        self.assertNotIn("LAUNCH_CLOSED", plans)
        self.assertNotIn("holdA", plans)
        self.assertNotIn("OpexV233LParallelLaunchOpen", plans)
        self.assertNotIn("approach", plans)

    def test_track4_first_local_ok_is_adopted_and_larger_radii_stop(self):
        repair = body("v233_long_good.nut", "OpexV233LRepairParallel")
        self.assertIn("phase=adopt", repair)
        self.assertIn("reason=REJECT_SPLICE", repair)
        self.assertIn("reason=REJECT_DEDICATED", repair)
        self.assertIn("reason=REJECT_ISSUE", repair)
        self.assertIn("if (search.path == null || search.path == false) continue;", repair)
        reject = repair.index("reason=REJECT_SPLICE")
        self.assertIn("break;", repair[reject:reject + 500])
        self.assertNotIn("continue;", repair[reject:reject + 350])
        adopt = repair.index("phase=adopt")
        self.assertLess(adopt, repair.index("reason=SPLICED", adopt))
        self.assertIn("approach = approach", repair)
        self.assertIn("tail[0] == approach", repair)
        search = body("builder_rail.nut", "OpexCreateSegmentedSearch")
        self.assertIn("plan.approach", search)
        self.assertIn("[plan.lead, plan.station_exit, plan.approach]", search)
        self.assertIn("[plan.lead, plan.station_exit]", search)
        direct = body("builder_rail.nut", "OpexCreateRailPathfinder")
        self.assertIn("[plan.lead, plan.station_exit, plan.approach]", direct)
        finder = source("pathfinder_v90/v129.nut")
        self.assertIn("node.len() >= 3 && node[2] != null", finder)
        self.assertIn("node[1] % 61", finder)
        self.assertIn("node[0] % 61", finder)
        self.assertNotRegex(finder, r"function\s*\(")
        self.assertNotIn(".find(", finder)

    def test_track2_reservation_precedes_every_primary_search_including_reverse_probe(self):
        entries = (("builder_rail.nut", "OpexPlanRailRoute", "OpexSearchPath("),
                   ("task_rail.nut", "OpexAI::_startRailSearch", "OpexV294fReverseProbe("),
                   ("task_rail.nut", "OpexAI::_startRailStockSearch", "OpexCreateRailPathfinder("))
        for filename, name, search in entries:
            with self.subTest(entry=name):
                code = body(filename, name)
                reservation = code.index('if (OpexV233LIs(candidate)) {\n    clearanceTiles = OpexV233LReserveDouble(')
                self.assertLess(reservation, code.index(search))
                self.assertIn('} else if (OpexV190Active() && candidate.kind == "freight")', code)
        helper = body("v233_long_good.nut", "OpexV233LReserveDouble")
        self.assertIn('OpexV190MergeIgnoredTiles(clearance, plansA, plansB)', helper)
        self.assertIn('if (DECISION_LOG)', helper)
        # Alternative B platforms in smoke4 overlap one another. Reserving their
        # union while exempting all primary exits leaves holes for track 1.
        sites = body("v233_long_good.nut", "OpexV233LPlatformPlans")
        self.assertIn('if (ok && phase == "build") {', sites)
        self.assertIn('validB = [selectedB];', sites)
        self.assertIn('OpexV233LParallelSide(validA[0], q, validA[0].parallel, q.parallel) != 0', sites)

    def test_track2_is_mandatory_independently_of_economic_train_count(self):
        complete = body("builder_rail.nut", "OpexCompleteRailRouteAfterSearch")
        self.assertIn('if (OpexV233LIs(candidate) || (!OpexV198Active()', complete)
        self.assertIn('dual = OpexV233LPlanDoubleTrack(catalog, candidate,', complete)
        self.assertIn('if (OpexV233LIs(candidate) && plan.doubleTrack != 1)', complete)
        self.assertIn('plan.reason = "NOPLAN2";', complete)
        execute = body("builder_rail.nut", "OpexV190ExecuteRailPlan")
        self.assertLess(execute.index('OpexV233LIs(candidate) && !okD'),
                        execute.index('local started = []'))
        self.assertIn('line.doubleTrack != 1', body("v233_long_good.nut", "OpexV233LSelectGrowth"))

    def test_parallel_side_uses_real_source_expressions_for_all_head_orientations(self):
        code = uncomment(body("v233_long_good.nut", "OpexV233LParallelSide"))
        assignments = re.findall(r'local (\w+) = ([^;]+);', code)
        predicate = code.rsplit('return ', 1)[1].split(' ? ', 1)[0].replace('&&', ' and ')
        api = SimpleNamespace(GetTileX=lambda t: t % 256, GetTileY=lambda t: t // 256)
        # Independent geometry: the same physical side of a directed A->B
        # route is opposite to the outward direction of station B.
        for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for bx, by in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for side in (-1, 1):
                    for correct in (True, False):
                        a, b = 100 * 256 + 100, 140 * 256 + 140
                        offset_a = -ay * side + 256 * ax * side
                        offset_b = by * side - 256 * bx * side
                        scope = dict(AIMap=api,
                            planA=SimpleNamespace(station_exit=a, lead=a + ax + ay * 256),
                            planB=SimpleNamespace(station_exit=b, lead=b + bx + by * 256),
                            pA=SimpleNamespace(station_exit=a + offset_a),
                            pB=SimpleNamespace(station_exit=b + (offset_b if correct else -offset_b)))
                        for key, expr in assignments:
                            scope[key] = eval(expr, {"__builtins__": {}}, scope)
                        actual = scope['side'] if eval(predicate, {"__builtins__": {}}, scope) else 0
                        self.assertEqual(actual, side if correct else 0)

    def test_parallel_test_result_and_structure_schema_match_consumers(self):
        planner = body("builder_rail.nut", "OpexV190PlanDoubleTrack")
        self.assertIn('v233Context != null ? testFails.failed : testFails', planner)
        self.assertIn('firstTile = firstTile', body("builder_rail.nut", "OpexTestRailTrack"))
        self.assertIn('OpexRailPathGeometryIssue(candidateTiles, pA, pB)', planner)
        self.assertIn('} else {\n        if (!OpexRailEndConnected(', planner)
        trace = body("builder_rail.nut", "OpexV190TraceParallelTrack")
        self.assertIn('if (v233Context != null) {\n        structures2.append({ from = start2, to = end2, kind = structKind,', trace)
        self.assertIn('structure.from == fromTile && structure.to == toTile',
                      body("builder_rail.nut", "OpexPlannedStructureKind"))
        execute = body("builder_rail.nut", "OpexV190ExecuteRailPlan")
        self.assertIn('conn2 = (tFail == 0 && connExitA2 && connExitB2);', execute)

    def test_parallel_turn_guard_matches_pathfinder_and_rejects_self_intersection(self):
        code = body("v233_long_good.nut", "OpexV233LParallelGeometry")
        self.assertIn('if (tiles[i] in seen)', code)
        self.assertIn('"SELF_INTERSECTION"', code)
        expr = re.search(r'&& (tiles\[i\] - tiles\[i - 1\] == tiles\[i - 3\] - tiles\[i - 2\])', code)[1]
        for tiles, expected in (([1000, 1001, 1257, 1256], True),
                                ([1000, 1001, 1257, 1258], False),
                                ([1000, 1256, 1257, 1001], True),
                                ([1000, 1256, 1257, 1513], False)):
            self.assertEqual(eval(expr, {"__builtins__": {}}, {'tiles': tiles, 'i': 3}), expected)
        self.assertIn('OpexV233LParallelGeometry(v233Context, candidateTiles)',
                      body("builder_rail.nut", "OpexV190PlanDoubleTrack"))

    def test_track5_primary_forbidden_set_matches_pre_track4_launch(self):
        """Track 1 launch tiles stay the pre-TRACK4 lenient pair, minus a departure conflict.

        Quay and lead tiles still come only from OpexV190MergeIgnoredTiles. Beyond,
        a later strict lateral, and the other quay end are not added to that set.
        """
        reserve = body("v233_long_good.nut", "OpexV233LReserveDouble")
        self.assertLess(reserve.index("OpexV233LDetachOtherEnd"),
                        reserve.index("OpexV190MergeIgnoredTiles"))
        self.assertLess(reserve.index("OpexV190MergeIgnoredTiles"),
                        reserve.index("foreach (t in kept)"))
        self.assertLess(reserve.index("foreach (axis in [[dx, dy], [-dy, dx], [dy, -dx]])"),
                        reserve.index("OpexV233LOfferOtherEnd("))
        self.assertLess(reserve.index("OpexV233LOfferOtherEnd("),
                        reserve.index("reason=RESERVED"))
        self.assertEqual(reserve.count("ignored.append"), 1)
        self.assertNotIn("beyond", reserve)
        self.assertNotIn("OpexV233LInstallOtherEnd", reserve)
        self.assertNotIn("approach", reserve)
        self.assertIn('local labels = ["A", "B"];', reserve)
        self.assertIn("tried_other=", reserve)
        self.assertIn("reason=OTHER_TRY", reserve)
        self.assertIn("reason=RELEASE", reserve)
        self.assertIn("reason=ENDPOINTS", reserve)
        offer = body("v233_long_good.nut", "OpexV233LOfferOtherEnd")
        self.assertNotIn("ignored", offer)
        self.assertIn("reason=LAUNCH_OTHER", offer)
        self.assertIn("return 2;", offer)
        install = body("v233_long_good.nut", "OpexV233LPlanDoubleTrack")
        self.assertLess(install.index("OpexV233LInstallOtherEnd(planA)"),
                        install.index("OpexV190PlanDoubleTrack("))
        self.assertLess(install.index("OpexV233LInstallOtherEnd(planB)"),
                        install.index("OpexV190PlanDoubleTrack("))
        keep = body("v233_long_good.nut", "OpexV233LKeepLaunch")
        self.assertIn("if (front == null || front in departure) return null;", keep)
        self.assertIn("if (after != null && !(after in departure)) kept.append(after);", keep)
        other = body("v233_long_good.nut", "OpexV233LOtherParallel")
        self.assertIn("local otherExit = p.station_exit == low ? high : low;", other)
        self.assertIn("local otherLead = OpexV190MakeTile(otherExit, -dx, -dy);", other)
        self.assertIn("dx * dx + dy * dy != 1", other)
        self.assertIn("anchor = p.anchor, step = p.step, length = p.length, direction = p.direction", other)
        self.assertIn("v233OtherEnd = 1", other)
        same = body("v233_long_good.nut", "OpexV233LSameEnd")
        self.assertIn('plan.v233OtherEnd == 1) return true;', same)
        self.assertIn("return OpexSameStationEnd(plan, original);", same)
        planner = body("builder_rail.nut", "OpexV190PlanDoubleTrack")
        self.assertIn("(v233Context != null ? OpexV233LSameEnd(p, planA) : OpexSameStationEnd(p, planA))", planner)
        self.assertIn("(v233Context != null ? OpexV233LSameEnd(p, planB) : OpexSameStationEnd(p, planB))", planner)
        self.assertNotIn("if (OpexSameStationEnd(p, planA)", planner)
        self.assertNotIn("approach", body("v233_long_good.nut", "OpexV233LSiteProbe"))
        for fn in ("OpexCreateRailPathfinder", "OpexCreateSegmentedSearch"):
            code = body("builder_rail.nut", fn)
            self.assertIn('("approach" in plan) && plan.approach != null', code)
            self.assertIn("else sources.push([plan.lead, plan.station_exit]);", code)
        self.assertEqual(source("v233_long_good.nut").count("approach = approach"), 2)
        self.assertIn("approach = approach", body("v233_long_good.nut", "OpexV233LRepairParallel"))
        self.assertIn("approach = approach", body("v233_long_good.nut", "OpexV233LPoseSearch"))
        finder = source("pathfinder_v90/v129.nut")
        self.assertIn("V233_LONG_GOOD > 0 && node.len() >= 3 && node[2] != null", finder)

        def xy(tile):
            return tile % 256, tile // 256

        def make(tile, px, py):
            x, y = xy(tile)
            x += px
            y += py
            if not (0 <= x < 256 and 0 <= y < 256):
                return None
            return y * 256 + x

        def departure(exit_tile, lead):
            dx = xy(lead)[0] - xy(exit_tile)[0]
            dy = xy(lead)[1] - xy(exit_tile)[1]
            out = {exit_tile, lead}
            if dx == 0 and dy == 0:
                return out
            for step in ((dx, dy), (2 * dx, 2 * dy), (-dy, dx), (dy, -dx)):
                nxt = make(lead, step[0], step[1])
                if nxt is not None:
                    out.add(nxt)
            return out

        def keep_launch(front, after, blocked):
            if front is None or front in blocked:
                return None
            kept = [front]
            if after is not None and after not in blocked:
                kept.append(after)
            return kept

        def other_lead(anchor, step, length, exit_tile, lead):
            dx = xy(lead)[0] - xy(exit_tile)[0]
            dy = xy(lead)[1] - xy(exit_tile)[1]
            self.assertEqual(dx * dx + dy * dy, 1)
            low = anchor
            high = anchor + (length - 1) * step
            other_exit = high if exit_tile == low else low
            self.assertNotEqual(other_exit, exit_tile)
            return other_exit, make(other_exit, -dx, -dy)

        # Smoke 7, seed 100. Straight lenient front/after were reserved; beyond was not.
        # 58979->20909 found track 1 in 813 iterations from these ends.
        # 6172->21717 found it in 834. The log's later RAIL_ATTEMPT count includes track 2.
        cases = (
            (58723, 58722, 58467, 1, 2, 58467, 58466, 58465, 58464, 58463, 58469),
            (22956, 23212, 22701, 256, 2, 22957, 23213, 23469, 23725, 23981, 22445),
            (5915, 5659, 5914, 256, 3, 5914, 5658, 5402, 5146, 4890, 6682),
            (21723, 21979, 21210, 256, 3, 21722, 21978, 21977, 21976, 21975, 20954),
        )
        for primary_exit, primary_lead, anchor, step, length, exit_tile, lead, front, after, beyond, flipped in cases:
            blocked = departure(primary_exit, primary_lead)
            pre_track4 = [front, after]
            kept = keep_launch(front, after, blocked)
            self.assertEqual(kept, pre_track4)
            self.assertNotIn(beyond, kept)
            other_exit, flipped_lead = other_lead(anchor, step, length, exit_tile, lead)
            self.assertEqual(flipped_lead, flipped)
            self.assertNotIn(flipped, kept)
            self.assertNotIn(other_exit, kept)
            self.assertTrue(set(pre_track4).symmetric_difference(kept) <= blocked)

        # Parallel front sits on the primary's forward tile: drop that axis, do not keep after.
        exit_tile, lead = 20 + 20 * 256, 19 + 20 * 256
        blocked = departure(exit_tile, lead)
        forward = 18 + 20 * 256
        self.assertIn(forward, blocked)
        self.assertIsNone(keep_launch(forward, 17 + 20 * 256, blocked))
        # Only `after` collides: reserve front and release after.
        released = keep_launch(18 + 21 * 256, forward, blocked)
        self.assertEqual(released, [18 + 21 * 256])
        self.assertTrue(set([18 + 21 * 256, forward]).symmetric_difference(released) <= blocked)

    def test_double_logs_distinguish_platform_search_native_and_loop_failures(self):
        platform = body("v233_long_good.nut", "OpexV233LDoublePlatformLog")
        for reason in ('WRONG_END', 'PRIMARY_HITS_LEAD', 'PRIMARY_HITS_PLATFORM'):
            self.assertIn(reason, platform)
        wrapper = body("v233_long_good.nut", "OpexV233LPlanDoubleTrack")
        self.assertIn('if (DECISION_LOG)', wrapper)
        for token in ('phase=plan reason=', 'dual.reason', 'dual.step', 'dual.iterations', 'budget='):
            self.assertIn(token, wrapper)
        trace = body("builder_rail.nut", "OpexV190TraceParallelTrack")
        for reason in ('NO_BRIDGE_TYPE', 'BRIDGE_NATIVE', 'TUNNEL_NATIVE'):
            self.assertIn(reason, trace)
        planner = body("builder_rail.nut", "OpexV190PlanDoubleTrack")
        for reason in ('HEAD_ALIGNMENT', 'NATIVE_TRACK', 'SWITCH_AB', 'SWITCH_A', 'SWITCH_B', 'PRIMARY_COLLISION'):
            self.assertIn(reason, planner)
        self.assertIn('phase=search reason=BEGIN budget=', planner)
        self.assertIn('ticks_left=', planner)
        self.assertIn('candidate != null && DECISION_LOG', body("v233_long_good.nut", "OpexV233LDoubleTraceLog"))
        execute = body("builder_rail.nut", "OpexV190ExecuteRailPlan")
        self.assertIn('phase=build reason=" + result.doubleReason', execute)
        self.assertIn('phase=build reason=OK ok=1 trains=', execute)

    def test_track6_adjacent_pose_matches_recheck_and_rolls_back(self):
        """Smoke 9, 37055->55398: the plan passed and the separate quay B failed at pose.

        The recheck builds both platforms as one num=2 command before the track.
        A failed command logs step=stn_b2 and AIError before any later tile read.
        """
        pair = body("v233_long_good.nut", "OpexV233LStationPair")
        self.assertIn("parallel.v233OtherEnd == 1) return -1;", pair)
        self.assertIn("primary.step == 1 ? AIMap.GetMapSizeX() : 1", pair)
        self.assertIn("abs(primary.anchor - parallel.anchor) != sideways", pair)
        # 37055 side B is one row south; side A is one row north. The other
        # end keeps the anchor, so it is not a second rectangle.
        def station_pair(primary, parallel, step, other=False, map_x=256):
            if other or abs(primary - parallel) != (map_x if step == 1 else 1):
                return -1
            return min(primary, parallel)
        self.assertEqual(station_pair(55646, 55902, 1), 55646)
        self.assertEqual(station_pair(36799, 36543, 1), 36543)
        self.assertEqual(station_pair(58467, 58467, 1, other=True), -1)

        adjacent = body("v233_long_good.nut", "OpexV233LPoseAdjacent")
        self.assertLess(adjacent.index("local err = AIError.GetLastError();"),
                        adjacent.index("OpexV233LPoseFailLog"))
        self.assertIn("BuildRailStation(first, primary.direction, 2, primary.length, station)", adjacent)
        self.assertNotIn("DemolishTile", adjacent)
        self.assertLess(adjacent.index("AIRail.BuildRailStation"), adjacent.index("primary.v233Pair <- parallel"))
        fail = body("v233_long_good.nut", "OpexV233LPoseFailLog")
        self.assertIn("phase=build step=", fail)
        self.assertIn('reason=FAIL error=" + err', fail)
        self.assertNotIn("GetLastError", fail)
        one = body("v233_long_good.nut", "OpexV233LPoseOne")
        self.assertLess(one.index("OpexV233LPlatformReady"), one.index("DemolishTile"))
        self.assertLess(one.index("AIRail.BuildRailStation"), one.index("AIError.GetLastError()"))
        self.assertIn("reason=ALREADY", one)
        execute = body("builder_rail.nut", "OpexV190ExecuteRailPlan")
        self.assertLess(execute.index("OpexV233LPoseAdjacent"), execute.index("OpexBuildTrack(tiles"))
        self.assertLess(execute.index('OpexV233LPoseOne(candidate, planB2, stIdB_exist, "stn_b2")'),
                        execute.index("if (okA2 && okB2)"))
        self.assertIn('if (!OpexV233LIs(candidate)) dCosts = AIAccounting();', execute)
        self.assertNotIn("local dCosts = AIAccounting();", execute)
        second = execute.index("if (okA2 && okB2)")
        self.assertLess(second, execute.index("OpexBuildTrains", second))
        self.assertIn("trains=0 rollback=1", execute)
        self.assertLess(execute.index("OpexV233LIs(candidate) && !okD"),
                        execute.index("local started = []"))
        self.assertIn("line.doubleTrack != 1", body("v233_long_good.nut", "OpexV233LSelectGrowth"))
        rollback = body("builder_rail.nut", "OpexRollback")
        self.assertEqual(rollback.count("OpexV233LRollbackPair"), 2)
        self.assertNotIn("RemoveAirport", rollback)
        self.assertIn("V233_LONG_GOOD > 0", rollback)

    def test_track6_nopa_at_head_is_dropped_before_the_full_search(self):
        """Smoke 9, 58979->20909: west NOPA at 5 must not seed the 14k search.

        LAUNCH_OTHER lead 58469 stays. An empty side returns SEARCH_NOPA
        without OpexSearchPath. Track 1 still excludes that other end.
        """
        repair = body("v233_long_good.nut", "OpexV233LRepairParallel")
        marker = "if (search.path == null || search.path == false) continue;"
        self.assertLess(repair.index("search.iterations <= 5"), repair.index(marker))
        self.assertIn("radius == 4 && left == 0", repair)
        self.assertIn('search.stop == "NOPA"', repair)
        self.assertIn("result.enclosedLead = planA.lead", repair)
        self.assertIn("OpexV233LNoteEnclosed(candidate, planA.lead)", repair)
        self.assertIn("enclosedLead = null", repair)
        kept = [lead for lead in (58466, 58469) if lead not in {58466}]
        self.assertEqual(kept, [58469])
        drop = body("v233_long_good.nut", "OpexV233LWithoutEnclosed")
        self.assertIn("reason=DROP_ENCLOSED", drop)
        self.assertNotIn(".find(", drop)
        planner = body("builder_rail.nut", "OpexV190PlanDoubleTrack")
        self.assertLess(planner.index("OpexV233LWithoutEnclosed"),
                        planner.index("phase=search reason=BEGIN"))
        self.assertLess(planner.index("reason=SKIP_ENCLOSED"),
                        planner.index("local search = OpexSearchPath"))
        self.assertIn('acc.step = "SEARCH_NOPA"', planner)
        self.assertEqual(body("v233_long_good.nut", "OpexV233LReserveDouble").count("ignored.append"), 1)
        self.assertNotIn("ignored", body("v233_long_good.nut", "OpexV233LOfferOtherEnd"))
        # 6172 smoke 9 still uses the smoke 7 launch pair. Length 2 comes from
        # the wagon formula; 21210 is the other-end lead and stays out.
        plans = body("v233_long_good.nut", "OpexV233LPlatformPlans")
        self.assertIn("OpexRailPlatformLengthForWagons(candidate.wagons)", plans)
        self.assertNotIn("21210", body("v233_long_good.nut", "OpexV233LReserveDouble"))
        self.assertNotIn("length = 3", plans)

    def test_track7_aside_bridge_and_span_budget_precede_the_full_search(self):
        """Smoke 10, 62245->46727: length-8 bridge lands on company rail.

        Slide stays on the axis. The other perpendicular side, then a longer
        or shorter span, is tried before any A*. A length-8 obstacle no
        longer inherits the 1000-iteration floor of a 4-node window.
        """
        repair = body("v233_long_good.nut", "OpexV233LRepairParallel")
        self.assertLess(repair.index("OpexV233LSlideBridge("), repair.index("OpexV233LAsideBridge("))
        self.assertLess(repair.index("OpexV233LAsideBridge("), repair.index("foreach (radius in [4, 8, 16])"))
        self.assertLess(repair.index("foreach (radius in [4, 8, 16])"), repair.index("OpexSearchPath("))
        self.assertIn("if (span > reach) reach = span", repair)
        self.assertIn("span * span * 48", repair)
        self.assertIn("min(8000, max(1000, span * span * 48))", repair)
        # Length 8: 3072, above the old 1000 floor and inside the 8000 cap.
        # A one-tile obstacle stays on the 1000 floor.
        self.assertEqual(min(8000, max(1000, 8 * 8 * 48)), 3072)
        self.assertEqual(min(8000, max(1000, 1 * 1 * 48)), 1000)
        aside = body("v233_long_good.nut", "OpexV233LAsideBridge")
        for token in ("reason=OCCUPANT", "reason=ASIDE_OK", "reason=ASIDE_NONE",
                      "OpexV190MakeTile", "AIBridge.BuildBridge", "local testMode = AITestMode()"):
            self.assertIn(token, aside)
        for token in ("DemolishTile", "RemoveRail", ".find(", "function("):
            self.assertNotIn(token, aside)
        # Same-length shift of both heads by one perpendicular step.
        # Map x grows by 1. Bridge along +x, perp (0, +1) moves the span off the rail.
        cur, nxt = (54, 240), (61, 240)
        perp = (0, 1)
        new_start = (cur[0] + perp[0], cur[1] + perp[1])
        new_end = (nxt[0] + perp[0], nxt[1] + perp[1])
        self.assertEqual(abs(new_end[0] - new_start[0]) + abs(new_end[1] - new_start[1]), 7)
        self.assertNotEqual(new_start[1], cur[1])
        kind = body("v233_long_good.nut", "OpexV233LOccupantKind")
        for label in ('"rail"', '"bridge"', '"tunnel"', '"road"', '"water"', '"house"', '"slope"', '"clear"'):
            self.assertIn(label, kind)
        self.assertLess(kind.index("IsBridgeTile"), kind.index("IsRailTile"))
        probe = body("v233_long_good.nut", "OpexV233LBridgeProbe")
        self.assertIn('kind=" + OpexV233LOccupantKind(t)', probe)
        self.assertIn("water=", probe)

    def test_track7_pocket_probe_drops_a_head_before_the_full_search(self):
        """Smoke 10, 58979->20909: east head is open one tile, then 14656 iters.

        A 64-step probe that cannot close 12 tiles toward the other lead
        notes the head and returns SKIP_POCKET. The straight corridor names
        the first blocker. An open corridor is not rejected.
        """
        planner = body("builder_rail.nut", "OpexV190PlanDoubleTrack")
        self.assertLess(planner.index('OpexV233LSearchHeadLog(v233Context, p, "A", forbidden)'),
                        planner.index("OpexV233LProbeHeads("))
        self.assertLess(planner.index("OpexV233LProbeHeads("),
                        planner.index("phase=search reason=BEGIN"))
        self.assertLess(planner.index("reason=SKIP_POCKET"),
                        planner.index("local search = OpexSearchPath"))
        self.assertLess(planner.index("reason=SKIP_ENCLOSED"),
                        planner.index("OpexV233LProbeHeads("))
        pocket = body("v233_long_good.nut", "OpexV233LProbeHead")
        self.assertIn("OpexV233LWalkCorridor(candidate, p, side, forbidden)", pocket)
        self.assertIn("OpexV233LNoteEnclosed(candidate, p.lead)", pocket)
        self.assertIn("reason=POCKET", pocket)
        self.assertIn("reason=POCKET_OPEN", pocket)
        self.assertIn("AIController.GetTick() >= deadline", pocket)
        self.assertIn("startDist + 3", pocket)
        self.assertIn("> 16", pocket)
        walk = body("v233_long_good.nut", "OpexV233LWalkCorridor")
        self.assertIn("reason=CORRIDOR", walk)
        self.assertIn("OpexV233LOccupantKind(nxt)", walk)
        self.assertLess(walk.index("error = AIError.GetLastError()"), walk.index("OpexV233LOccupantKind(nxt)"))
        # 210 tiles apart, best still 206: not enough. 198 is enough.
        start = 210
        need = 12 if start >= 12 else start
        self.assertLess(start - 206, need)
        self.assertGreaterEqual(start - 198, need)
        self.assertNotIn(".find(", pocket)
        self.assertNotIn("function(", pocket)

    def test_track8_pose_failure_splices_around_a_local_obstacle(self):
        """Smoke 11, 6172->21717: track 2 plans (658 iters) then pose fails.

        1974-09-30 TRACK_FAIL_idx138_err260 (ERR_AREA_NOT_CLEAR) must not
        roll the line back before a local splice. Three repairs at most.
        Cash and a failed repair keep the existing DOUBLEFAIL rollback.
        """
        repair = body("v233_long_good.nut", "OpexV233LRepairPose")
        for token in ("phase=repair reason=OK", "OpexV233LOccupantKind",
                      "OpexV233LDropBuilt", "OpexV233LPoseSearch",
                      "min(8000, max(1000, span * span * 48))",
                      "ctx.repairs >= 3", '"LIMIT"', '"NOPA"',
                      "restart = left + 1", "OpexV233LPoseLocal"):
            self.assertIn(token, repair)
        self.assertLess(repair.index("ctx.repairs >= 3"), repair.index("OpexV233LDropBuilt"))
        self.assertLess(repair.index("OpexV233LDropBuilt"), repair.index("OpexV233LPoseSearch"))
        self.assertLess(repair.index("return null"), repair.index("ctx.repairs >= 3"))
        self.assertNotIn(".find(", repair)
        self.assertNotIn("function(", repair)
        pose = body("v233_long_good.nut", "OpexV233LPoseLocal")
        self.assertLess(pose.index("ERR_NOT_ENOUGH_CASH"), pose.index("ERR_AREA_NOT_CLEAR"))
        self.assertLess(pose.index("return false"), pose.index("return true"))
        self.assertIn("ERR_LAND_SLOPED_WRONG", pose)
        log = body("v233_long_good.nut", "OpexV233LPoseLog")
        self.assertIn("phase=repair reason=", log)
        self.assertIn("idx=", log)
        self.assertIn("kind=", log)
        self.assertIn("error=", log)
        search = body("v233_long_good.nut", "OpexV233LPoseSearch")
        for token in ("OpexSearchPath", "OpexV233LSpliceParallel", "OpexV233LFence",
                      "OpexV233LParallelGeometry", "OpexJoinPathIsDedicated",
                      "OpexResolveSearchStructures", "OpexV233LParallelIssue"):
            self.assertIn(token, search)
        self.assertIn("tiles = tail", search)
        self.assertLess(search.index("OpexSearchPath"), search.index("OpexV233LSpliceParallel"))
        self.assertLess(search.index("OpexV233LSpliceParallel"),
                        search.index("OpexV233LParallelIssue(candidate, window, blocked)"))
        drop = body("v233_long_good.nut", "OpexV233LDropBuilt")
        self.assertLess(drop.index("AICompany.IsMine"), drop.index("AITile.DemolishTile"))
        self.assertLess(drop.index("IsRailStationTile"), drop.index("AITile.DemolishTile"))
        self.assertIn("fromIdx", drop)
        span = body("v233_long_good.nut", "OpexV233LPoseSpan")
        self.assertIn("AIMap.DistanceManhattan(tiles[last], tiles[nxt])", span)
        build = body("builder_rail.nut", "OpexBuildTrack")
        repair_at = build.index("OpexV233LRepairPose")
        give_at = build.index("v233GiveUp", repair_at)
        ret_at = build.index("return failed;", give_at)
        self.assertLess(give_at, ret_at)
        self.assertLess(build.index("!V199_ROBUST_BUILD"), repair_at)
        self.assertIn("v233Repair", build)
        self.assertIn("repaired.restart - 1", build)
        self.assertLess(build.index('local err = AIError.GetLastError();', repair_at),
                        build.index("if (v233GiveUp) err = errNow;", repair_at))
        self.assertLess(build.index("OpexRailCaptureTrackFailure(failure, tiles, i, cur, segmentKind", repair_at),
                        ret_at)
        self.assertNotIn("v233Repair", body("builder_rail.nut", "OpexExecuteRailPlan"))
        execute = body("builder_rail.nut", "OpexV190ExecuteRailPlan")
        call = "tFail = OpexBuildTrack(tiles2, plan.structures2, trackFailure2, trackOpt2);"
        self.assertLess(execute.index("if (OpexV233LIs(candidate)) trackOpt2.v233Repair"),
                        execute.index(call))
        self.assertLess(execute.index(call), execute.index('result.reason = "DOUBLEFAIL"'))
        self.assertIn("OpexRollback(tiles, planA, planB, depot, trains.rollbackVehicles);", execute)
        self.assertIn("trains=0 rollback=1", execute)
        self.assertIn('result.reason = "DOUBLEFAIL"', execute)
        # Index 138, one occupied tile, adjacent plan of 301 nodes.
        # Anchor walks back to a 4-tile gap: 134. The goal is the first
        # adjacent pair after the zone, 140. Pose resumes on the cleared lead.
        left = -1
        index, length = 138, 301
        for anchor in range(index - 2, max(0, index - 16) - 1, -1):
            left = anchor
            if index - left >= 4:
                break
        zone = index
        right = zone + 2
        self.assertEqual((left, zone, right, left + 1), (134, 138, 140, 135))
        self.assertEqual(min(8000, max(1000, 1 * 1 * 48)), 1000)
        self.assertEqual(min(8000, max(1000, 8 * 8 * 48)), 3072)
        self.assertLess(right, length)

    def test_setting_bounds_defaults_and_single_read(self):
        block = re.search(r'AddSetting\(\{\s*name = "v233_long_good",.*?\}\);', source("info.nut"), re.S)[0]
        self.assertIn("min_value = 0, max_value = 1", block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, level + r"_value\s*=\s*0\b")
        self.assertEqual(source("settings.nut").count('GetSetting("v233_long_good")'), 1)
        self.assertIn("V233_LONG_GOOD <- 0;", source("globals_pre.nut"))
        self.assertEqual(source("info.nut").count("AddSetting("), 60)

    def test_off_reviewed_edits_preserve_all_original_hashes(self):
        for name, entry in FIXTURE["files"].items():
            with self.subTest(name=name):
                projected = off_source(name, source(name))
                self.assertEqual(hashlib.sha256(projected.encode()).hexdigest(), entry["sha256_off"])
                if name not in ("main.nut", "globals_pre.nut", "info.nut", "settings.nut", "persist.nut"):
                    self.assertNotIn("OpexV233L", uncomment(projected))
        edited = source("candidates.nut").replace("V233_LONG_GOOD > 0 ? OpexV233LSource", "true ? OpexV233LSource")
        with self.assertRaises(AssertionError):
            off_source("candidates.nut", edited)

    def test_off_switch_short_circuits_all_entry_paths(self):
        self.assertIn('return V233_LONG_GOOD > 0 && candidate != null', body("v233_long_good.nut", "OpexV233LIs"))
        self.assertIn('V233_LONG_GOOD > 0 ? OpexV233LSource', body("candidates.nut", "OpexFreightCandidates"))
        self.assertIn('if (V233_LONG_GOOD > 0) OpexV233LTick(this);', body("orchestrator.nut", "OpexAI::_runOrchestratorTick"))
        self.assertIn('if (V233_LONG_GOOD > 0 && OpexV233LSelectGrowth', body("task_rail.nut", "OpexAI::_expandRailLines"))
        self.assertIn('local longModel = V233_LONG_GOOD > 0 && longGood;', body("economy.nut", "OpexLineEconomics"))

    def test_source_checks_exact_factory_cargo_and_live_input(self):
        code = body("v233_long_good.nut", "OpexV233LInput")
        for token in ('line.cargo == cargo', 'IsProcessingIndustry', 'producing.HasItem(cargo)',
                      'accepting.HasItem(line.cargo)', 'OpexV233LTouches', 'AIVehicle.IsValidVehicle',
                      'OpexVehicleServesStation', 'AITile.GetOwner(line.stationB)'):
            self.assertIn(token, code)
        source_code = body("v233_long_good.nut", "OpexV233LSource")
        self.assertIn('AICargo.GetCargoLabel(cargo) != "GOOD"', source_code)
        self.assertIn('line.originA == source.tile', source_code)
        self.assertIn('OpexV233LInput(line, cargo) == source.id', source_code)
        self.assertIn('complete && !inputLive', source_code)
        self.assertNotIn('AIStation.GetOwner', source("v233_long_good.nut"))  # GameScript-only API.

    def test_alternating_deliveries_are_durable_zero_not_missing(self):
        samples = [[m, 120 if m % 2 else 0, 20 if m % 2 else 0] for m in range(6)]
        window, durable, monthly = observe(samples)
        self.assertEqual(len(window), 6)
        self.assertTrue(durable)
        self.assertEqual(monthly, 50)
        self.assertEqual(window[0], (0, 0, 0))
        code = body("v233_long_good.nut", "OpexV233LObserve")
        self.assertIn('row.month >= month - 1', code)
        self.assertIn('OpexV233LMonth() != month', code)
        self.assertIn('OpexV233LRecord(row, month - 1, production, residual)', code)
        record = body("v233_long_good.nut", "OpexV233LRecord")
        self.assertIn('month <= row.month', record)
        self.assertIn('row.months.append(month)', record)
        self.assertIn('row.production.append(production)', record)
        self.assertIn('row.residual.append(residual)', record)
        self.assertIn('row.months[0] < month - V233L_WINDOW', record)

    def test_missing_duplicate_and_stopped_production_windows(self):
        cases = (
            ([[m, 100, 20] for m in range(5)], False, 80),
            ([[m, 100, 20] for m in (0, 1, 2, 4, 5, 6)], True, 80),
            ([[m, 100, 20] for m in (0, 1, 3, 4, 6, 7)], False, 80),
            ([[m, 100, 20] for m in range(6)] + [[9, 100, 20]], False, 80),
            ([[0, 600, 0]] + [[m, 0, 0] for m in range(1, 6)], False, 100),
            ([[m, 100, 200] for m in range(6)], True, 0),
            ([[m, 100, 20] for m in range(6)] + [[5, 999, 0]], True, 80),
            ([[m, 100, 20] for m in range(6)] + [[3, 999, 0]], True, 80),
        )
        for samples, durable, monthly in cases:
            with self.subTest(samples=samples):
                _, actual_durable, actual_monthly = observe(samples)
                self.assertEqual((actual_durable, actual_monthly), (durable, monthly))
        self.assertIn('positive >= 2 && recent > 0', body("v233_long_good.nut", "OpexV233LDurable"))

    def test_missing_month_is_neither_zero_nor_sample(self):
        # At month 5, the absent month 3 cannot complete a six-sample window.
        samples = [[m, 100, 10] for m in (0, 1, 2, 4, 5)]
        window, durable, monthly = observe(samples)
        self.assertEqual([m for m, _, _ in window], [0, 1, 2, 4, 5])
        self.assertFalse(durable)
        self.assertEqual(monthly, 90)
        window, durable, monthly = observe(samples + [[6, 400, 40]])
        self.assertTrue(durable)
        self.assertEqual([m for m, _, _ in window], [0, 1, 2, 4, 5, 6])
        self.assertEqual(monthly, 135)  # 810 / 6 observations, never / 7.

    def test_recent_production_uses_calendar_months_with_gap(self):
        samples = [[m, 100 if m in (2, 3) else 0, 0] for m in (0, 1, 2, 3, 4, 6)]
        self.assertFalse(observe(samples)[1])  # last three calendar months 4..6 are idle.
        samples[-1][1] = 100
        self.assertTrue(observe(samples)[1])
        self.assertIn('row.months[i] >= row.month - 2', body("v233_long_good.nut", "OpexV233LDurable"))

    def test_sample_expiry_boundaries_and_all_consumers(self):
        for now, expected in ((4, False), (5, False), (6, True), (7, True), (8, True), (9, False)):
            with self.subTest(now=now):
                self.assertEqual(fresh(5, now), expected)
        self.assertFalse(fresh(-1, 1))
        helper = body("v233_long_good.nut", "OpexV233LFresh")
        self.assertIn('month >= 0 && month < now && now - month <= V233L_MAX_AGE', helper)
        self.assertIn('const V233L_MAX_AGE = 3;', source("v233_long_good.nut"))
        for name in ("Source", "Recheck", "InputTarget", "FleetMargin"):
            with self.subTest(consumer=name):
                self.assertIn('OpexV233LFresh(row.month,', body("v233_long_good.nut", "OpexV233L" + name))
        admit = body("v233_long_good.nut", "OpexV233LAdmit")
        self.assertIn('OpexV233LFresh(context.sampleMonth, OpexV233LMonth())', admit)
        self.assertIn('sampleMonth = row.month', body("v233_long_good.nut", "OpexV233LSource"))

    def test_distinct_reject_reasons_and_simultaneous_failures(self):
        samples = [[m, 100, 20] for m in (0, 1, 2, 4, 5, 6)]
        self.assertEqual(reject_reasons(samples, 9), set())  # age three, not only previous month.
        self.assertEqual(reject_reasons(samples, 10), {"stale"})
        self.assertEqual(reject_reasons(samples, 7, input_live=False), {"input_not_live"})
        self.assertEqual(reject_reasons(samples, 7, export_exists=True), {"export_exists"})
        self.assertEqual(reject_reasons([[m, 100, 100] for m in range(6)], 6), {"no_residual"})
        self.assertEqual(reject_reasons([[0, 0, 0]], 4, input_live=False, export_exists=True),
                         {"window", "stale", "input_not_live", "export_exists", "no_residual"})
        for distance in (149, 150, 300, 301):
            self.assertEqual(reject_reasons(samples, 7, distance=distance),
                             set() if 150 <= distance <= 300 else {"distance"})
        code = body("v233_long_good.nut", "OpexV233LSource")
        for reason in ("window", "stale", "input_not_live", "export_exists", "no_residual", "budget", "source_changed"):
            self.assertIn(f'reasons.append("{reason}")', code)
        self.assertIn('foreach (reason in reasons) OpexV233LLog("REJECT"', code)
        self.assertIn('if (complete && !inputLive)', code)
        self.assertLess(code.index('foreach (line in lines)'), code.index('reasons.append("input_not_live")'))
        self.assertIn('ready = reasons.len() == 0', code)
        self.assertNotIn('production_or_export', source("v233_long_good.nut"))

    def test_load_checks_observation_dates_and_migrates_consecutive_legacy_windows(self):
        code = body("v233_long_good.nut", "OpexV233LLoad")
        for token in ('row.months.len() != row.production.len()', 'month <= previous',
                      'month > row.month', 'month < row.month - V233L_WINDOW',
                      'previous != row.month', 'row.months <- []',
                      'row.month - row.production.len() + 1 + i'):
            self.assertIn(token, code)
        self.assertNotIn('AIDate.', code)  # Load must work before world APIs/settings.
        self.assertLess(code.index('pending.phase != "prepare" && pending.before == null'),
                        code.index('row.months <- []'))  # no partial migration of invalid saves.

    def test_candidate_keeps_destination_guard_and_normal_portfolio(self):
        code = body("candidates.nut", "OpexFreightCandidates")
        self.assertIn('(ss != null && longGood == null) || st != null', code)
        self.assertIn('longGood != null && !OpexV233LAdmit', code)
        self.assertIn('candidate.v233LongGood <- true', code)
        self.assertIn('out.append(candidate)', code)
        self.assertIn('distance < 150 || distance > 300', body("v233_long_good.nut", "OpexV233LAdmit"))
        self.assertIn('distance >= 150 && distance <= 300', body("v233_long_good.nut", "OpexV233LRecheck"))
        self.assertNotIn('v233', source("projects_selection.nut").lower())
        self.assertNotIn('v233', source("capital.nut").lower())

    def test_two_train_sizing_tariff_and_both_recalculations(self):
        econ = body("economy.nut", "OpexLineEconomics")
        self.assertIn('if (longModel) calibrationOffered /= 2.0;', econ)
        self.assertIn('longModel || (OpexV190Active()', econ)
        self.assertIn('AICargo.GetCargoIncome(cargo, distance, paidDays)', econ)
        self.assertIn('oneWayDays + dwellDays / 2 + perTrain * 15.0 / offered', econ)
        self.assertIn('OpexV163CandidateSecondary(candidate), OpexV233LIs(candidate)', source("builder_rail.nut"))
        complete = body("builder_rail.nut", "OpexCompleteRailRouteAfterSearch")
        self.assertIn('candidate.distance = tariffDistance', complete)
        self.assertIn('candidate.v233RouteDistance <- routeDistance', complete)
        execute = body("builder_rail.nut", "OpexV190ExecuteRailPlan")
        self.assertLess(execute.index('!OpexV233LRecheck'), execute.index('OpexQuoteRailCapital'))
        self.assertLess(execute.index('OpexV233LIs(candidate) && !okD'), execute.index('local started = []'))
        self.assertIn('result.reason = "DOUBLEFAIL"', execute)

    def test_whole_platform_acceptance_and_optional_share_use_good_rating(self):
        code = body("v233_long_good.nut", "OpexV233LCargoValue")
        self.assertIn('horizontal ? length : 1, horizontal ? 1 : length', code)
        plans = body("v233_long_good.nut", "OpexV233LPlatformPlans")
        self.assertIn('OpexV233LTouches(p, industry, true', plans)
        self.assertIn('AIStation.GetCargoRating(station, candidate.cargo)', plans)
        self.assertIn('goodRating >= candidate.stationRating', plans)
        self.assertIn('p.stationId <- station', plans)
        self.assertIn('AIRail.BuildRailStation', plans)
        self.assertIn('end == "A" && line.originB == candidate.src', body("v233_long_good.nut", "OpexV233LSourceNeighbour"))

    def test_site_admission_precedes_publication_in_both_producers(self):
        for filename in ("candidates.nut", "po01c_generators.nut"):
            code = source(filename)
            start = code.index('candidate.v233LongGood <- true;')
            end = code.index('out.append(candidate);', start)
            guarded = code[start:end]
            self.assertLess(guarded.index('OpexV233LPreflight(catalog, candidate)'),
                            guarded.index('OpexV233LLog("CANDIDATE"'))
            self.assertIn('if (!siteCheck.ready)', guarded)
            self.assertIn('stats.unsitable++;', guarded)
            self.assertIn('stats.accepted--;', guarded)
            self.assertIn('if (siteCheck.pending) { longGood.visits--; break; }', guarded)
            self.assertIn('longGood.ops += OpexOpsMeasureEnd(siteMark)', guarded)
            self.assertNotIn('OpexV233LPreflight', off_source(filename, code))

    def test_site_b_has_own_budget_and_incomplete_scan_is_resumable(self):
        plans = body("v233_long_good.nut", "OpexV233LPlatformPlans")
        self.assertIn('OpexV233LSiteSearch(candidate.src', plans)
        self.assertIn('OpexV233LSiteSearch(candidate.dst', plans)
        self.assertNotIn('OpexOpsMeasureBegin', plans)  # Regression: shared A/B clock.
        scan = body("v233_long_good.nut", "OpexV233LSiteSearch")
        self.assertIn('local mark = OpexOpsMeasureBegin();', scan)
        self.assertIn('OpexOpsMeasureEnd(mark) < V233L_SLICE_OPS', scan)
        self.assertIn('!scan.done ? "budget" : "exhausted"', scan)
        self.assertIn('local r = scan.ring, pos = scan.pos;', scan)
        self.assertIn('scan.geometry = 7; scan.stats.terrain++', scan)
        self.assertIn('host == null ? STATION_SEARCH_RADIUS : host.spread', scan)
        self.assertIn('scan.ring > radius', scan)
        self.assertIn('pending ? "SITE_PENDING"', plans)
        self.assertIn('limited ? "SITE_LIMIT"', plans)
        self.assertNotIn('OpexStationPlans(', plans)

    def test_site_cache_revalidates_live_native_geometry_and_keeps_progress(self):
        scan = body("v233_long_good.nut", "OpexV233LSiteSearch")
        self.assertIn('V233L_SITE_CACHE.len() >= V233L_SITE_CACHE_MAX', scan)
        self.assertIn('now < old.used', scan)
        self.assertIn('old.done && old.hints.len() == 0', scan)
        self.assertIn('old.limited ? 180 : 30', scan)
        self.assertNotIn('now - old.used >', scan)
        self.assertIn('":pair:" + pair.src + ":" + pair.dst', scan)
        self.assertIn('AIRail.GetCurrentRailType()', scan)
        validation = scan[scan.index('foreach (hint in scan.hints)'):scan.index('while (plans.len()')]
        self.assertIn('OpexV233LSiteProbe(', validation)
        self.assertIn('scan.hints.clear(); scan.done = false;', validation)
        self.assertIn('V233L_SITE_CACHE.clear();', body("v233_long_good.nut", "OpexV233LLoad"))
        self.assertNotIn('V233L_SITE_CACHE', source("persist.nut"))

    def test_positive_sites_survive_admission_to_build_and_pending_never_expires(self):
        # Execute the actual TTL predicate, including July -> August regression.
        from types import SimpleNamespace
        scan = body("v233_long_good.nut", "OpexV233LSiteSearch")
        expr = scan.split('if (now < old.used || ', 1)[1].split(') delete V233L_SITE_CACHE[key]', 1)[0]
        expr = ('now < old.used || ' + expr).replace('&&', ' and ').replace('||', ' or ')
        expr = expr.replace('old.hints.len()', 'len(old.hints)')
        expr = expr.replace('(old.limited ? 180 : 30)', '(180 if old.limited else 30)')
        cases = [
            (True, [42], False, 51, False),  # ready July 5, build August 25
            (False, [], False, 455, False),  # sparse admissions cannot reset cursor
            (True, [], False, 31, True),
            (True, [], True, 179, False),
            (True, [], True, 181, True),
        ]
        for done, hints, limited, now, expired in cases:
            old = SimpleNamespace(done=done, hints=hints, limited=limited, used=0, date=0)
            self.assertEqual(eval(expr, {"__builtins__": {}, "len": len}, {"old": old, "now": now}), expired)

    def test_background_progress_is_fair_bounded_and_restores_rail_type(self):
        worker = body("v233_long_good.nut", "OpexV233LContinueSites")
        self.assertIn('if (scan.done) continue;', worker)
        self.assertIn('scan.worked < selected.worked', worker)
        self.assertEqual(worker.count('OpexV233LSiteSearch('), 1)
        self.assertIn('AIRail.SetCurrentRailType(selected.railType)', worker)
        self.assertIn('AIRail.SetCurrentRailType(railType)', worker)
        self.assertIn('OpexV233LContinueSites();', body("v233_long_good.nut", "OpexV233LTick"))
        scan = body("v233_long_good.nut", "OpexV233LSiteSearch")
        for token in ('scan.total + OpexOpsMeasureEnd(mark) < totalLimit',
                      'scan.total += ops; scan.slices++', 'scan.total >= totalLimit',
                      'scan.limited = true', '"total_budget"', 'entry.done && entry.used < date',
                      '"SITE_STEP"', '" from="', '" next="', '" total_ops="'):
            self.assertIn(token, scan)
        self.assertIn('const V233L_SITE_TOTAL_OPS = 240000;', source("v233_long_good.nut"))
        self.assertIn('const V233L_JOIN_TOTAL_OPS = 80000;', source("v233_long_good.nut"))

    def test_saved_site_cursors_are_validated_and_migrate_old_saves(self):
        self.assertIn('sites = V233L_SITE_CACHE', body("v233_long_good.nut", "OpexV233LNewState"))
        load = body("v233_long_good.nut", "OpexV233LLoad")
        self.assertIn('("sites" in data) ? OpexV233LLoadSites(data.sites) : {}', load)
        self.assertIn('data.sites <- V233L_SITE_CACHE', load)
        validation = body("v233_long_good.nut", "OpexV233LLoadSites")
        for token in ('data.len() > V233L_SITE_CACHE_MAX', 'typeof scan[field] != "integer"',
                      'typeof scan[field] != "bool"', 'scan.geometry > 7', 'scan.pos >=',
                      'scan.total < 0', 'scan.hints.len() > 4', 'typeof hint[field] != "integer"',
                      'scan.worked = -1', 'restored[key] <- scan'):
            self.assertIn(token, validation)
        self.assertNotIn('scan.ring = 0', validation)
        self.assertNotIn('scan.total = 0', validation)

    def test_ordered_rings_cover_every_anchor_once_and_airport_window_is_12_squared(self):
        # Read the along-position expression from production code; prove coverage,
        # no duplicate corners, near-edge-first order and the even-width window.
        scan = body("v233_long_good.nut", "OpexV233LSiteSearch")
        expr = scan.split('local along = ', 1)[1].split(';', 1)[0]
        expr = expr.replace('(order % 2 == 0 ? order / 2 : -(order + 1) / 2)',
                            '(order // 2 if order % 2 == 0 else -(order + 1) // 2)')
        all_points = {(0, 0)}
        for r in range(1, 13):
            points = []
            for edge in range(4):
                for order in range(2 * r):
                    along = eval(expr, {"__builtins__": {}}, {"r": r, "order": order})
                    points.append([(-r + along, -r), (r, -r + along),
                                   (r - along, r), (-r, r - along)][edge])
            self.assertEqual(points[0], (0, -r))
            self.assertEqual(len(set(points)), 8 * r)
            self.assertFalse(all_points.intersection(points))
            all_points.update(points)
            self.assertEqual(len(all_points), (2 * r + 1) ** 2)
        window = {(x, y) for x, y in all_points if -5 <= x <= 6 and -5 <= y <= 6}
        self.assertEqual(len(window), 144)
        self.assertIn('host.spread / 2', scan)
        self.assertIn('dx < -((host.spread - 1) / 2)', scan)

    def test_early_acceptance_skips_four_geometries_before_native_probe(self):
        scan = body("v233_long_good.nut", "OpexV233LSiteSearch")
        loop = scan[scan.index('while (plans.len()'):]
        self.assertLess(loop.index('OpexV233LFlat(anchor)'), loop.index('OpexV233LCargoValue('))
        self.assertLess(loop.index('OpexV233LCargoValue('), loop.index('OpexV233LSiteProbe('))
        self.assertIn('scan.geometry % 4 == 0', loop)
        self.assertIn('last < 0 || OpexV233LCargoValue', loop)
        self.assertIn('scan.geometry += 3; scan.stats.earlyAcceptance++; clear = false', loop)
        self.assertIn('scan.geometry++;', loop)
        self.assertIn('if (!clear) continue;', loop)
        probe = body("v233_long_good.nut", "OpexV233LSiteProbe")
        self.assertLess(probe.index('!OpexV233LJoinFits'), probe.index('OpexV233LFlat(lead)'))
        worker = body("v233_long_good.nut", "OpexV233LContinueSites")
        self.assertIn('result.cacheKey != selectedKey', worker)

    def test_both_quays_leads_acceptance_and_authority_checked_without_mutation(self):
        probe = body("v233_long_good.nut", "OpexV233LSiteProbe")
        for token in ('OpexV233LFlat(lead)', 'OpexV233LFlat(lead2)',
                      'OpexV233LOffset(anchor, ux * i, uy * i)',
                      'OpexV233LOffset(anchor2, ux * i, uy * i)',
                      '(!producing && value < 8)', 'OpexV233LTouches(p, industry, true',
                      'OpexStationEncroachesRival', 'AIError.ERR_LOCAL_AUTHORITY_REFUSES'):
            self.assertIn(token, probe)
        self.assertLess(probe.index('local test = AITestMode();'), probe.index('AIRail.BuildRailStation'))
        self.assertIn('host == null ? AIStation.STATION_NEW : host.station', probe)
        self.assertIn('BuildRailStation(first, direction, 2, length, station)', probe)
        self.assertNotIn('DemolishTile', probe)
        self.assertNotIn('LevelTiles', probe)
        plans = body("v233_long_good.nut", "OpexV233LPlatformPlans")
        self.assertIn('BuildRailStation(adjacent, p.direction, 2, p.length, station)', plans)

    def test_site_coordinates_do_not_wrap_and_geometry_has_both_exits(self):
        offset = body("v233_long_good.nut", "OpexV233LOffset")
        for condition in ('x < 0', 'y < 0', 'x >= AIMap.GetMapSizeX()', 'y >= AIMap.GetMapSizeY()'):
            self.assertIn(condition, offset)
        probe = body("v233_long_good.nut", "OpexV233LSiteProbe")
        self.assertIn('axis == 0 ? AIRail.RAILTRACK_NE_SW : AIRail.RAILTRACK_NW_SE', probe)
        self.assertIn('sign > 0 ? length - 1 : 0', probe)
        self.assertIn('sign > 0 ? length : -1', probe)
        self.assertIn('p.parallels <- [p.parallel]', probe)

    def test_platform_length_keeps_all_promised_wagons_and_tariff_pairs(self):
        plans = body("v233_long_good.nut", "OpexV233LPlatformPlans")
        self.assertIn('OpexRailPlatformLengthForWagons(candidate.wagons)', plans)
        self.assertNotIn('length--', plans)
        self.assertIn('distance < 150 || distance > 300', plans)
        self.assertIn('if (validB.len() > 0) { validA.append(p); break; }', plans)
        # The original transaction still checks actual vehicle length and rolls back.
        builder = source("builder_rail.nut")
        self.assertIn('local trainLengthLimit = platformLength * 16;', builder)
        self.assertIn('OpexV233LIs(candidate) && !okD', builder)

    def test_site_logs_separate_search_censoring_and_physical_refusals(self):
        log = body("v233_long_good.nut", "OpexV233LSiteLog")
        for field in ('side=', 'phase=', 'reason=', 'length=', 'ring=', 'ops=',
                      'terrain=', 'acceptance=', 'parallel=', 'authority=', 'native=',
                      'catchment=', 'error=', 'anchor=', 'cargo_value=', 'threshold='):
            self.assertIn(field, log)
        self.assertIn('OpexV233LLog("SITE_PLAN"', log)
        plans = body("v233_long_good.nut", "OpexV233LPlatformPlans")
        self.assertIn('site_a=', plans)
        self.assertIn('site_b=', plans)

    def test_airport_precedes_town_scan_even_while_town_is_budget_limited(self):
        plans = body("v233_long_good.nut", "OpexV233LPlatformPlans")
        self.assertLess(plans.index('OpexV233LJoinSearch('), plans.index('OpexV233LSiteSearch(candidate.dst'))
        self.assertIn('if (joined.plans.len() == 0 || !compatible)', plans)
        self.assertIn('joined.reason == "budget"', plans)
        self.assertNotIn('scanB.reason == "exhausted"', plans)
        self.assertIn('"SITE_WAIT"', plans)
        join = body("v233_long_good.nut", "OpexV233LJoinSearch")
        for token in ('AIStationList(AIStation.STATION_AIRPORT)',
                      'AIStation.GetNearestTown(id) == candidate.dstTown',
                      'V233L_JOIN_CURSOR[key] = index', 'reason == "budget"',
                      '"SITE_B_JOIN"', 'reason=no_airport', 'if (DECISION_LOG)'):
            self.assertIn(token, join)
        self.assertIn('V233L_JOIN_CURSOR.clear()', body("v233_long_good.nut", "OpexV233LLoad"))

    def test_composite_acceptance_uses_exact_union_and_actual_noai_api(self):
        host = body("v233_long_good.nut", "OpexV233LJoinHost")
        for token in ('AIStation.IsValidStation(station)',
                      'AITile.GetOwner(airport.Begin())', 'AICompany.COMPANY_SELF',
                      'AIStation.GetNearestTown(station) != town',
                      'AITileList_StationCoverage(station)',
                      'AITile.GetCargoAcceptance(t, cargo, 1, 1, 0)',
                      'host.acceptance >= 8', 'value < 0',
                      'station.modified_catchment', 'station.distant_join_stations'):
            self.assertIn(token, host)
        self.assertNotIn('AIStation.GetCargoAcceptance', uncomment(source("v233_long_good.nut")))
        self.assertIn('if (host != null) value = host.acceptance', body("v233_long_good.nut", "OpexV233LSiteProbe"))
        # Overlapping airport/stop catchments count each house tile once.
        airport, stop = {1, 2, 3}, {3, 4}
        values = {1: 0, 2: 2, 3: 3, 4: 2, 5: 1}
        self.assertEqual(sum(values[t] for t in airport | stop), 7)
        self.assertEqual(sum(values[t] for t in airport | stop | {5}), 8)
        self.assertEqual(sum(values[t] for t in airport) + sum(values[t] for t in stop), 10)

    def test_spread_includes_remote_stops_and_second_quay(self):
        host = body("v233_long_good.nut", "OpexV233LJoinHost")
        self.assertIn('AITileList_StationType(station, AIStation.STATION_ANY)', host)
        self.assertIn('AIGameSettings.GetValue("station.station_spread")', host)
        fits = body("v233_long_good.nut", "OpexV233LJoinFits")
        # Evaluate the real source predicate on synthetic coordinates (no VM).
        expr = fits.split('return ', 1)[1].split(';', 1)[0].replace('&&', ' and ')
        expr = expr.replace('AIMap.GetTileX(last)', 'last[0]').replace('AIMap.GetTileY(last)', 'last[1]')
        expr = expr.replace('AIMap.GetTileX(first)', 'first[0]').replace('AIMap.GetTileY(first)', 'first[1]')
        from types import SimpleNamespace
        cases = [
            ((10, 10, 15, 15), (18, 10), (21, 11), True),  # 6 + 2 gap + 4 = 12
            ((10, 10, 15, 15), (19, 10), (22, 11), False),
            ((9, 10, 15, 15), (18, 10), (21, 11), False),  # joined bus stop
            ((10, 10, 15, 15), (10, 21), (13, 22), False),  # second quay exceeds spread
            ((10, 10, 15, 15), (4, 10), (7, 11), True),
            ((10, 10, 15, 15), (10, 4), (11, 7), True),
        ]
        for bounds, first, last, expected in cases:
            host = SimpleNamespace(left=bounds[0], top=bounds[1], right=bounds[2], bottom=bounds[3], spread=12)
            with self.subTest(bounds=bounds, first=first, last=last):
                self.assertEqual(eval('(' + expr + ')', {"__builtins__": {}, "min": min, "max": max},
                                      {"host": host, "first": first, "last": last}), expected)

    def test_join_recheck_protects_airport_stops_roads_and_both_paths(self):
        recheck = body("v233_long_good.nut", "OpexV233LRecheck")
        self.assertIn('if ("v233Airport" in plan.planB)', recheck)
        self.assertIn('OpexV233LJoinRouteClear(candidate, plan)', recheck)
        guard = body("v233_long_good.nut", "OpexV233LJoinRouteClear")
        for token in ('OpexV233LJoinHost(', '[plan.tiles, plan.tiles2]', 'parts.HasItem(t)',
                      'AIRoad.IsRoadTile(t)', 'reason = "protected_route"', 'reason = "occupied"',
                      'OpexV233LJoinFits(host, first, last)', 'local test = AITestMode()',
                      'BuildRailStation(first, p.direction, 2, p.length, host.station)'):
            self.assertIn(token, guard)
        for forbidden in ('DemolishTile', 'RemoveAirport', 'RemoveRoadStation'):
            self.assertNotIn(forbidden, guard)
        execute = body("builder_rail.nut", "OpexV190ExecuteRailPlan")
        self.assertLess(execute.index('OpexV233LRecheck'), execute.index('OpexQuoteRailCapital'))
        self.assertIn('OpexV233LIs(candidate) && !okD', execute)
        rollback = body("builder_rail.nut", "OpexRollback")
        self.assertIn('AIRail.RemoveRailStationTileRectangle(t, t, false)', rollback)
        self.assertNotIn('RemoveAirport', rollback)

    def test_join_uses_host_station_tariff_at_admission_route_and_recheck(self):
        for filename, function in (("v233_long_good.nut", "OpexV233LPlatformPlans"),
                                   ("v233_long_good.nut", "OpexV233LRecheck"),
                                   ("builder_rail.nut", "OpexCompleteRailRouteAfterSearch")):
            self.assertIn('OpexV233LTariffTile(', body(filename, function))
        tariff = body("v233_long_good.nut", "OpexV233LTariffTile")
        self.assertIn('AIStation.GetLocation(platform.stationId)', tariff)
        self.assertIn(': platform.anchor', tariff)

    def test_growth_needs_persistent_stock_physics_margin_and_real_loop(self):
        backlog = body("v233_long_good.nut", "OpexV233LBacklog")
        for text in ('row.waiting.len() == 3', 'OpexV233LMin(row.waiting) >= required', 'row.month >= row.nextMonth'):
            self.assertIn(text, backlog)
        selection = body("v233_long_good.nut", "OpexV233LSelectGrowth")
        for text in ('line.vehicles.len() >= 14', 'line.v181Loop', 'line.doubleTrack != 1',
                     'OpexV233LFleetMargin', 'OpexV284Select(owner, year, true)', 'OpexV233LInputTarget(line)'):
            self.assertIn(text, selection)
        margin = body("v233_long_good.nut", "OpexV233LFleetMargin")
        self.assertIn('OpexRailEffectiveSpeed', margin)
        self.assertIn('delta <= 0', margin)
        self.assertIn('AICargo.GetCargoIncome', margin)
        self.assertIn('OpexAvailableCapital()', margin)
        self.assertNotRegex(margin, r'waiting\s*\*\s*12')
        v284 = body("task_v284.nut", "OpexV284Select")
        self.assertIn('!v233Input && (year < OPEX_START_YEAR', v284)
        self.assertIn('v233Input && !OpexV233LInputMargin', v284)

    def test_save_load_option_guards_scalar_state_and_idempotent_adoption(self):
        save = body("persist.nut", "OpexAI::Save")
        self.assertIn('if (V233_LONG_GOOD > 0) saveObj.v233LongGood <- V233L_STATE;', save)
        self.assertIn('key == "v233LongGood" && V233_LONG_GOOD <= 0', body("persist.nut", "OpexSaveProjectLine"))
        load = body("persist.nut", "OpexAI::Load")
        self.assertIn('this._v233LReload = data.v233LongGood', load)
        start = body("main.nut", "OpexAI::Start")
        self.assertIn('V233_LONG_GOOD > 0 ? OpexV233LLoad(this._v233LReload) : null', start)
        self.assertLess(start.index('OpexLoadSettings()'), start.index('OpexV233LLoad'))
        decode = body("v233_long_good.nut", "OpexV233LLoad")
        for text in ('row[key] != "integer"', 'pending[key] != "integer"', 'row[key].len() > V233L_WINDOW',
                     'row.waiting.len() > 3', 'pending.before == null'):
            self.assertIn(text, decode)
        transaction = body("v233_long_good.nut", "OpexV233LGrowthStep")
        self.assertLess(transaction.index('pending.phase = "building"'), transaction.index('AIVehicle.CloneVehicle'))
        self.assertLess(transaction.index('pending.phase = "starting"'), transaction.index('AIVehicle.StartStopVehicle'))
        self.assertIn('!OpexWaterContains(line.vehicles, pending.newVehicle)', transaction)
        self.assertIn('OpexFindLineForVehicle(owner._lines, v) == null', transaction)
        self.assertIn('pending.phase == "building"', body("v233_long_good.nut", "OpexV233LReconcile"))

    def test_bounds_measurements_log_guards_no_new_valuate_or_sleep(self):
        code = source("v233_long_good.nut")
        for text in ('const V233L_SLICE_OPS = 20000;', 'count < 8', 'state.rows.len() >= V233L_MAX_FACTORIES',
                     'growth.len() >= 128', 'OpexOpsMeasureEnd(mark)', '"OPS"', 'if (DECISION_LOG) OpexDecide'):
            self.assertIn(text, code)
        self.assertIn('k >= V233L_TOWNS', source("candidates.nut"))
        self.assertNotIn('longGood.mark', source("candidates.nut") + source("po01c_generators.nut"))
        self.assertIn('longGood.ops += OpexOpsMeasureEnd(v233Mark)', source("candidates.nut"))
        self.assertIn('workMark != null && OpexOpsMeasureEnd(workMark)', source("builder_rail.nut"))
        for token in ('.Valuate(', '.find(', 'Sleep(', 'function('):
            self.assertNotIn(token, uncomment(code))
        self.assertEqual(source("po01c_generators.nut"), generated())  # read-only, never regenerate.

    def test_new_module_balanced_and_no_reserved_identifiers(self):
        code = uncomment(source("v233_long_good.nut"))
        self.assertNotRegex(code, r'\blocal\s+(clone|base|parent|static|delegate|vargc|vargv|resume|yield)\b')
        stack = []
        pairs = {')': '(', ']': '[', '}': '{'}
        for token in re.findall(r'"(?:\\.|[^"\\])*"|[()\[\]{}]', code):
            if token.startswith('"'):
                continue
            if token in '([{':
                stack.append(token)
            else:
                self.assertTrue(stack)
                self.assertEqual(stack.pop(), pairs[token])
        self.assertEqual(stack, [])

    def test_rollback_keeps_existing_depot_traffic_and_tracks_new_identity(self):
        code = body("v233_long_good.nut", "OpexV233LGrowthStep")
        self.assertIn('OpexV257Discard(owner, pending.newVehicle)', code)
        self.assertIn('if (pending.before != null)', code)
        self.assertIn('!OpexWaterContains(pending.before, v)', code)
        self.assertIn('OpexFindLineForVehicle(owner._lines, v) == null', code)
        self.assertIn('vehicles.Count() > 2048', code)

    def test_input_growth_requires_our_live_output(self):
        code = body("v233_long_good.nut", "OpexV233LInputTarget")
        self.assertIn('row.exportLine < 0', code)
        self.assertIn('row.exportMonth < OpexV233LMonth() - 1', code)
        observe_code = body("v233_long_good.nut", "OpexV233LObserveBacklog")
        self.assertIn('AIVehicle.IsValidVehicle(line.vehicles[0])', observe_code)
        self.assertIn('V233L_STATE.rows[industry].exportMonth = month', observe_code)

    def test_opcode_meters_only_span_synchronous_work(self):
        code = body("v233_long_good.nut", "OpexV233LSourceEnd")
        self.assertIn('" ops=" + context.ops', code)
        self.assertNotIn('OpexOpsMeasureEnd(context.', code)
        candidate = body("candidates.nut", "OpexFreightCandidates")
        self.assertIn('longGood.ops >= V233L_SLICE_OPS', candidate)
        execute = body("v233_long_good.nut", "OpexV233LContinueGrowth")
        self.assertIn('OpexV233LGrowthStep(owner)', execute)
        self.assertIn('phase=growth_execute ops=', execute)
