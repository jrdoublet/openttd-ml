"""ROAD100 graph-bridge: executable contracts, with NO engine or old fixture writes.

The tiny Python maps below are a *reference oracle* for rejection cases, not a
Squirrel emulator. When worker-9's independent .nut module is available,
additional source contracts are enabled automatically. Only a paired OpenTTD
run can prove a corridor is physically buildable and profitable.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
GRAPH = AI / "road100_graph_bridge.nut"


def read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def body(name: str, filename: str) -> str:
    source = read(filename)
    match = re.search(r"(?m)^function\s+" + re.escape(name) + r"\s*\(", source)
    if match is None:
        raise AssertionError(f"Missing {name} in {filename}")
    later = source.find("\nfunction ", match.end())
    return source[match.start():later if later >= 0 else len(source)]


def graph_source() -> str:
    if not GRAPH.is_file():
        raise unittest.SkipTest("worker-9 road100_graph_bridge.nut not yet available")
    return GRAPH.read_text(encoding="utf-8")


def graph_setting() -> str:
    info = read("info.nut")
    match = re.search(r'name\s*=\s*"road100_pax_graph_bridge"\s*,(.*?)\}\s*\);',
                      info, re.S)
    if match is None:
        raise unittest.SkipTest("graph-bridge AddSetting not yet wired by prime")
    return match.group(1)


def edge(a: tuple[int, int], b: tuple[int, int]) -> frozenset:
    """An unordered mock physical road/buildable edge (NOT two road tiles)."""
    return frozenset((a, b))


def mock_trace_check(
    tiles: list[tuple[int, int]],
    site_a: tuple[int, int],
    front_a: tuple[int, int],
    site_b: tuple[int, int],
    front_b: tuple[int, int],
    physical: set[frozenset],
    buildable: set[frozenset],
    blocked: set[tuple[int, int]] | None = None,
    nonflat: set[tuple[int, int]] | None = None,
    minimum_trace: int = 80,
) -> str:
    """Conservative behavior oracle: no identity, connectivity or slope fiction.

    Treat a missing road edge as provisional only if *that exact edge* can be
    constructed. Never infer a connection from two adjacent road tiles. The
    production trace is still subject to NoAI AITest and cumulative building.
    """
    blocked = blocked or set()
    nonflat = nonflat or set()
    if len(tiles) - 1 < minimum_trace or len(tiles) - 1 > 190:
        return "LENGTH"
    if (tiles[:2] != [site_a, front_a] or
            tiles[-2:] != [front_b, site_b] or site_a == site_b):
        return "DT_ENDPOINT"
    if (edge(site_a, front_a) not in physical or
            edge(site_b, front_b) not in physical):
        return "DT_FRONT_LINK"
    if len(set(tiles)) != len(tiles):
        return "CYCLE"
    for i, tile in enumerate(tiles):
        if i not in (0, len(tiles) - 1) and tile in blocked:
            return "OCCUPIED_STATION"
        if not i:
            continue
        prev = tiles[i - 1]
        if abs(tile[0] - prev[0]) + abs(tile[1] - prev[1]) != 1:
            return "NONCARDINAL"
        link = edge(prev, tile)
        if link not in physical and link not in buildable:
            return "UNBUILDABLE_EDGE"
        if 1 < i < len(tiles) - 1:
            before = tiles[i - 2]
            if ((prev[0] - before[0], prev[1] - before[1]) !=
                    (tile[0] - prev[0], tile[1] - prev[1]) and prev in nonflat):
                # A corner on a slope is admissible only when BOTH native road
                # bits exist; new road bits at a corner are speculative.
                if edge(before, prev) not in physical or link not in physical:
                    return "UNBUILDABLE_TURN"
    return "SPECULATIVE_TRACE_ONLY"


class GraphBridgeSyntheticBehavior(unittest.TestCase):
    """In-memory negative fixtures independent of existing saved fixtures."""

    def setUp(self) -> None:
        self.tiles = [(x, 0) for x in range(83)]
        self.site_a, self.front_a = self.tiles[:2]
        self.front_b, self.site_b = self.tiles[-2:]
        self.physical = {edge(self.site_a, self.front_a),
                         edge(self.front_b, self.site_b)}
        self.buildable = {edge(self.tiles[i], self.tiles[i + 1])
                          for i in range(1, len(self.tiles) - 2)}

    def check(self, tiles=None, physical=None, buildable=None, blocked=None,
              nonflat=None):
        return mock_trace_check(
            self.tiles if tiles is None else tiles,
            self.site_a, self.front_a, self.site_b, self.front_b,
            self.physical if physical is None else physical,
            self.buildable if buildable is None else buildable,
            blocked=blocked, nonflat=nonflat,
        )

    def test_long_straight_is_only_a_speculative_candidate(self):
        self.assertEqual(self.check(), "SPECULATIVE_TRACE_ONLY")

    def test_no_false_join_from_two_neighbouring_road_tiles(self):
        # Adjacent road tiles are not a native road link, even if each
        # possesses its own road bits towards another neighbour.
        no_bridge = self.buildable - {edge((25, 0), (26, 0))}
        self.assertEqual(self.check(buildable=no_bridge), "UNBUILDABLE_EDGE")

    def test_no_third_party_station_or_depot_on_internal_path(self):
        for station_tile in ((2, 0), (37, 0), (80, 0)):
            with self.subTest(tile=station_tile):
                self.assertEqual(self.check(blocked={station_tile}),
                                 "OCCUPIED_STATION")

    def test_no_collision_or_backtracking_inside_a_trace(self):
        loop = self.tiles[:15] + [(13, 0)] + self.tiles[15:]
        self.assertEqual(self.check(tiles=loop), "CYCLE")

    def test_no_diagonal_teleport_or_wrong_station_front(self):
        jumped = self.tiles.copy()
        jumped[20] = (20, 1)
        self.assertEqual(self.check(tiles=jumped), "NONCARDINAL")
        swapped = self.tiles.copy()
        swapped[1] = (1, 1)
        self.assertEqual(self.check(tiles=swapped), "DT_ENDPOINT")
        self.assertEqual(self.check(physical=set()), "DT_FRONT_LINK")

    def test_sloped_new_corner_rejected_existing_connected_corner_allowed(self):
        valid = ([(x, 0) for x in range(41)] +
                 [(40, y) for y in range(1, 3)] +
                 [(x, 2) for x in range(41, 81)] +
                 [(80, 1), (80, 0), (81, 0), (82, 0)])
        all_edges = {edge(valid[i], valid[i + 1])
                     for i in range(len(valid) - 1)}
        base_physical = {edge(valid[0], valid[1]),
                         edge(valid[-2], valid[-1])}
        # Invalid detours are rejected, not silently credited as road links.
        self.assertEqual(len(valid), len(set(valid)))
        self.assertEqual(
            self.check(tiles=valid, physical=base_physical,
                       buildable=all_edges - base_physical,
                       nonflat={(40, 0)}), "UNBUILDABLE_TURN"
        )
        connected_turn = base_physical | {
            edge((39, 0), (40, 0)), edge((40, 0), (40, 1))}
        self.assertEqual(
            self.check(tiles=valid, physical=connected_turn,
                       buildable=all_edges - connected_turn,
                       nonflat={(40, 0)}), "SPECULATIVE_TRACE_ONLY"
        )

    def test_local_and_pair_opcode_guard_arithmetic(self):
        for used, total in ((24_000, 180_000), (77_000, 180_000),
                            (110_000, 180_000), (120_000, 180_000)):
            hard_stop = min(used + 42_000, total - 66_000)
            if hard_stop > used:
                self.assertLess(hard_stop, total - 65_000)
                self.assertLessEqual(hard_stop - used, 42_000)
            else:
                self.assertLessEqual(hard_stop, used)
        self.assertEqual(400_000 - 180_000 - 180_000, 40_000)

    def test_graph_43_edges_only_when_explicitly_requested(self):
        path = [(x, 0) for x in range(45)]
        source = path[0]
        source_front = path[1]
        sink_front = path[-2]
        sink = path[-1]
        end_links = {edge(source, source_front), edge(sink_front, sink)}
        future = {edge(path[i], path[i + 1])
                  for i in range(1, len(path) - 2)}
        common = (path, source, source_front, sink, sink_front, end_links, future)
        self.assertEqual(mock_trace_check(*common), "LENGTH")
        self.assertEqual(mock_trace_check(*common, minimum_trace=43),
                         "SPECULATIVE_TRACE_ONLY")


class GraphBridgeExistingBuilderContracts(unittest.TestCase):
    def test_global_pair_caps_and_po01c_share_one_generator(self):
        candidates = read("candidates.nut")
        po01c = read("po01c_regen.nut")
        build = body("OpexRoad100LongConstructPlan", "builder_road.nut")
        self.assertIn("local longCap = ROAD100_LONG_BUILD ? 400000 : 250000;", candidates)
        self.assertIn("attemptLimit = 180000;", candidates)
        self.assertIn("longOps += pairOps;", candidates)
        self.assertIn("OpexRoad100LongConstructPlan(catalog, preliminaryLong,", candidates)
        self.assertIn("yield null;", candidates)
        self.assertIn("OpexRoad100SiteFirstGenerator", po01c)
        self.assertIn("if (OpexOpsMeasureEnd(mark) >= limitOps - 50000)", build)
        self.assertIn("OpexRoad100LongVerifyTrace(trace, pair.a, pair.b,", build)

    def test_physical_validator_never_treats_adjacent_roads_as_connected(self):
        verify = body("OpexRoad100LongVerifyTrace", "builder_road.nut")
        self.assertIn("trace.len() < 80 || trace.len() > 190", verify)
        self.assertIn("ROAD100_PAX_GRAPH_BRIDGE", verify)
        self.assertIn("trace.len() < 43 || trace.len() > 190", verify)
        self.assertIn("AIRoad.IsRoadStationTile(edge.to)", verify)
        self.assertIn("AIRoad.IsRoadDepotTile(edge.to)", verify)
        self.assertIn("AITile.IsStationTile(edge.to)", verify)
        self.assertIn("AIRoad.AreRoadTilesConnected(edge.from, edge.to)", verify)
        self.assertIn("local test = AITestMode();", verify)
        self.assertIn("allowed = AIRoad.BuildRoad(edge.from, edge.to)", verify)
        self.assertIn('out.reason = "EDGES_TESTED"', verify)
        build = body("OpexRoad100LongConstructPlan", "builder_road.nut")
        self.assertIn("ROAD100_PAX_GRAPH_BRIDGE", verify)
        self.assertIn("trace.len() < 43 || trace.len() > 190", verify)

    def test_depot_stop_cost_cash_and_rollback_are_not_optional(self):
        planner = body("OpexRoad100LongConstructPlan", "builder_road.nut")
        executor = body("OpexBuildRoadRoute", "builder_road.nut")
        exact = read("opcode_exact.nut")
        self.assertIn("OpexRoad100LongDepotPreflight(trace, pair.a, pair.b,", planner)
        self.assertIn("AIRoad.BuildDriveThroughRoadStation(pair.a.tile,", planner)
        self.assertIn("AIRoad.BuildDriveThroughRoadStation(pair.b.tile,", planner)
        self.assertIn("missing * catalog.costRoadPerTile * 3", planner)
        self.assertIn("quoteTotal = capital + capital / 4 + 50000", planner)
        self.assertIn('reason = "CASH"', planner)
        self.assertIn("OpexRoadBuildTrace(plan.trace, added)", executor)
        self.assertIn("OpexRoadRollback(", executor)
        self.assertIn("OpexRoad100LongTraceHash(longPlan.trace)", exact)
        self.assertIn("longPlan.stopA.front != candidate.road100GenFrontA", exact)
        self.assertIn("longPlan.stopB.front != candidate.road100GenFrontB", exact)
        self.assertIn("longPlan.roadQuoteCost > candidate.road100GenRoadQuote", exact)

    def test_current_off_path_is_not_a_second_graph_generator(self):
        candidate = read("candidates.nut")
        self.assertEqual(candidate.count("function OpexRoad100SiteFirstGenerator("), 1)
        self.assertIn("if (ROAD100_LONG_BUILD)", candidate)
        self.assertIn("if (ROAD100_PORTAL_STITCH && attemptLimit > 180000)",
                      candidate)
        self.assertIn("if (ROAD100_PAX_GRAPH_BRIDGE && attemptLimit > 180000)",
                      candidate)
        self.assertIn("OpexRoadPhysicalVehicleCap(1, 1)", read("economy.nut"))
        self.assertIn("return 2 * nMin;", read("economy.nut"))


class GraphBridgeFutureModuleContracts(unittest.TestCase):
    """Skip only missing worker-9/prime integration, never modify their files."""

    def test_new_module_is_speculative_and_has_bounded_resource_guard(self):
        source = graph_source()
        self.assertRegex(source, r"function\s+OpexRoad100Graph\w*\s*\(")
        self.assertIn("OpexOpsMeasureEnd", source)
        self.assertIn("limitOps", source)
        self.assertRegex(source, r"\btrace\b")
        for forbidden in (
            "AIRoad.BuildRoad(", "AIRoad.BuildRoadDepot(",
            "AIRoad.BuildDriveThroughRoadStation(",
            "AIVehicle.Build", "AIOrder.AppendOrder(",
            "AICargo.GetCargoWaiting(", "Pathfinder.",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_new_module_distinguishes_road_tiles_from_connected_edges(self):
        source = graph_source()
        self.assertIn("AIRoad.AreRoadTilesConnected", source)
        self.assertIn("AIRoad.IsRoadTile", source)
        self.assertIn("AIMap.DistanceManhattan", source)
        self.assertRegex(source, r"(?i)(seen|visited|occupied|collision)")
        self.assertRegex(source, r"(?i)(stationtile|roadstationtile|isstationtile)")
        self.assertRegex(source, r"(?i)(slope|flat|turn)")

    def test_graph_algorithm_hard_caps_and_no_false_verified_claim(self):
        source = graph_source()
        for contract in (
            "function OpexRoad100GraphBridgeTrace(",
            "function OpexRoad100GBRoadEdge(",
            "function OpexRoad100GBOccupied(",
            "for (local count = 0; count < 42; count++)",
            "cur.depth >= 14", "hop < 20", "cursor < 20",
            "pairCeiling = limitOps < 180000 ? limitOps : 180000",
            "local attemptCeiling = 38000;",
            "out.ops >= 38000", "out.ops >= 42000",
            "pairCeiling - 50000",
            "trace = null", "verified = false",
            "OpexRoad100GBRoadEdge(cur.tile, next, cache)",
            "AIRoad.AreRoadTilesConnected(fromTile, toTile)",
            "AIRoad.AreRoadTilesConnected(toTile, fromTile)",
            "AIRoad.IsRoadStationTile(tile)",
            "AIRoad.IsRoadDepotTile(tile)",
            "AITile.IsStationTile(tile)",
            "next in used", "next in protectedB",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, source)
        self.assertNotRegex(source, r"out\.verified\s*=\s*true")
        self.assertIn('out.reason = "CANDIDATE_NEEDS_VERIFY"', source)

    def test_cached_graph_preserves_physical_edges_and_orientation_states(self):
        source = graph_source()
        self.assertIn("function OpexRoad100GBCache()", source)
        self.assertIn("function OpexRoad100GBRoadTile(tile, cache)", source)
        self.assertIn("AIRoad.AreRoadTilesConnected(fromTile, toTile)", source)
        self.assertIn("AIRoad.AreRoadTilesConnected(toTile, fromTile)", source)
        self.assertIn("cache.edges.rawset(key, connected)", source)
        self.assertIn("cache.edges.rawset(toTile * 4 + reverse, connected)", source)
        self.assertIn("local key = next * 8 + direction * 2 + (real ? 1 : 0)", source)
        self.assertIn("if (key in cheapest && cheapest[key] <= newCost)", source)
        self.assertIn("occupied.rawset(next, true)", source)
        self.assertIn("if (joinA >= 0)", source)
        self.assertIn("if (routeLength < 43 || routeLength > 190", source)

    def test_graph_log_cannot_precede_publication_budget_gate(self):
        source = graph_source()
        publish = source.index("if (out.ops >= 38000 ||")
        log = source.index('OpexDecide("ROAD100_GRAPH_BRIDGE"')
        self.assertLess(publish, log)
        self.assertIn("out.trace = null;", source[publish:log])
        self.assertIn('out.reason = "OPCAP"', source[publish:log])

    def test_fast_orthogonal_candidate_remains_speculative_and_bounded(self):
        source = graph_source()
        start = source.index("function OpexRoad100GBFastTrace(")
        end = source.index("function OpexRoad100GraphBridgeTrace(")
        fast = source[start:end]
        self.assertIn("OpexOpsMeasureEnd(started) >= 6000", fast)
        self.assertIn("result.ops >= 8000", fast)
        self.assertIn("result.trace = null;", fast)
        self.assertIn("result.reason = \"FAST_CANDIDATE\"", fast)
        self.assertIn("bridgeLength", fast)
        self.assertIn("next in seen", fast)
        self.assertIn("OpexRoadOnDtAxis", fast)
        self.assertNotRegex(fast, r"\bAIRoad\.BuildRoad\s*\(")
        self.assertNotRegex(fast, r"\bAITestMode\s*\(")
        planner = body("OpexRoad100LongConstructPlan", "builder_road.nut")
        self.assertIn("OpexRoad100LongVerifyTrace(trace, pair.a, pair.b,", planner)
        self.assertLess(source.index("local fast = OpexRoad100GBFastTrace("),
                        source.index("for (local hop = 0; hop < 20"))

    def test_fast_tiles_have_no_native_occupancy_scan_and_explain_rejects(self):
        source = graph_source()
        fast = source[source.index("function OpexRoad100GBFastTrace("):
                      source.index("function OpexRoad100GraphBridgeTrace(")]
        walk = fast[fast.index("for (local j = 0; j < steps; j++)"):
                    fast.index("if (rejected) {", fast.index("for (local j = 0; j < steps; j++)"))]
        self.assertNotIn("OpexRoad100GBFastOccupied(next,", walk)
        self.assertNotIn("OpexRoad100GBFastOccupied(current,", walk)
        self.assertIn("OpexRoad100GBFastOccupied(current,", fast)
        self.assertNotIn("AIRoad.IsRoadTile(", walk)
        self.assertIn("j % 32 == 0", walk)
        self.assertNotIn("seen.rawset(next, true)", walk)
        self.assertIn("bridgeLength != span", fast)
        self.assertIn('result.rejections += variant + ":" + result.reason', fast)
        self.assertIn("fast_rejections=" + '" + out.fast_rejections', source)
        self.assertIn("OpexRoad100LongVerifyTrace(trace, pair.a, pair.b,",
                      body("OpexRoad100LongConstructPlan", "builder_road.nut"))

    def test_fast_prefilters_sleeve_crossing_before_long_tile_walk(self):
        source = graph_source()
        fast = source[source.index("function OpexRoad100GBFastTrace("):
                      source.index("function OpexRoad100GraphBridgeTrace(")]
        helper = body("OpexRoad100GBFastOnSegment", "road100_graph_bridge.nut")
        self.assertIn("tile % width", helper)
        self.assertIn("(tile - x) / width", helper)
        self.assertNotIn("AITestMode", helper)
        self.assertNotIn("AIRoad.", helper)
        self.assertLess(fast.index("local sleeveCollision = false"),
                        fast.index("local seen = {};"))
        self.assertIn("OpexRoad100GBFastOnSegment(siteA.tile,", fast)
        self.assertIn("OpexRoad100GBFastOnSegment(siteB.tile,", fast)
        self.assertIn("OpexRoad100GBFastOnSegment(sleeveA.tiles[sa],", fast)
        self.assertIn("OpexRoad100GBFastOnSegment(sleeveB.tiles[sb],", fast)
        self.assertIn('result.rejections += variant + ":SLEEVE_CROSS;"', fast)
        self.assertIn("if (next == siteB.tile)", fast)
        self.assertIn("if (bxTile in seen)", fast)
        self.assertIn("if (next in seen)", fast)  # real B sleeve only
        self.assertNotIn("local path = [", fast)
        self.assertEqual(fast.count("local trace = [];"), 1)
        self.assertIn("trace.append({ from = current, to = next });", fast)
        self.assertIn("trace.append({ from = fromTile, to = tile });", fast)
        self.assertIn("trace.append({ from = fromTile, to = siteB.tile });", fast)
        self.assertIn("if (trace.len() != length ||", fast)

    def test_graph_front_dogleg_preserves_exact_physical_verifier(self):
        src = graph_source()
        bypass = body("OpexRoad100GBFrontDoglegTrace",
                      "road100_graph_bridge.nut")
        planner = body("OpexRoad100LongConstructPlan", "builder_road.nut")
        self.assertIn("blockedIndex < 1 || blockedIndex > 20", bypass)
        self.assertIn("flatBackoff < 4", bypass)
        self.assertIn("begin > 1", bypass)
        self.assertIn("original[begin - 1].to - original[begin - 1].from == direction", bypass)
        self.assertIn("offset < 1 || offset > 3", bypass)
        self.assertIn("result.len() < 43 || result.len() > 190", bypass)
        self.assertIn("OpexRoadOnDtAxis(siteA.tile", bypass)
        self.assertIn("OpexRoadOnDtAxis(siteB.tile", bypass)
        self.assertIn("edge.to in visited", bypass)
        self.assertIn("OpexRoadIsFlat(edge.from)", bypass)
        self.assertNotIn("AITestMode", bypass)
        self.assertNotIn("AIRoad.BuildRoad(", bypass)
        self.assertIn("checked.blocked_error == 260", planner)
        self.assertIn("AIRoad.ERR_ROAD_CANNOT_BUILD_ON_TOWN_ROAD", planner)
        self.assertIn("checked.blocked_index <= 20", planner)
        self.assertIn('diagnostic.reason = "STRAIGHT_WINDOW"', bypass)
        self.assertIn('diagnostic.reason = "NONFLAT_FIRST"', bypass)
        self.assertIn('diagnostic.reason = "NONFLAT_LAST"', bypass)
        self.assertIn('diagnostic.reason = "NONFLAT_BYPASS_A"', bypass)
        self.assertIn('diagnostic.reason = "NONFLAT_BYPASS_B"', bypass)
        self.assertIn('" town_road_error=" + AIRoad.ERR_ROAD_CANNOT_BUILD_ON_TOWN_ROAD', planner)
        self.assertIn('diagnostic.reason = "CYCLE"', bypass)
        self.assertIn('diagnostic.reason = "OK"', bypass)
        self.assertIn('"phase=detour_geometry width=" + graphWidth', planner)
        self.assertIn("OpexRoad100GBFrontDoglegTrace(", planner)
        self.assertIn("graphWidth = 3; graphWidth >= 1", planner)
        self.assertIn('"phase=detour width=" + graphWidth', planner)
        self.assertIn('" from=" + graphRetest.blocked_from', planner)
        self.assertIn("OpexRoad100LongVerifyTrace(", planner)
        self.assertIn("graphRetest.ok", planner)
        self.assertIn("limitOps - 50000", planner)
        self.assertIn('" detours=" + graphDetours', planner)
        self.assertIn("function OpexRoad100GraphBridgeTrace(", src)

    def test_graph_only_near_markets_and_non_eliminating_front_access_rank(self):
        graph = graph_source()
        candidates = read("candidates.nut")
        planner = body("OpexRoad100LongConstructPlan", "builder_road.nut")
        front = body("OpexRoad100GBFrontAccessScore", "builder_road.nut")
        self.assertIn("function OpexRoad100GBMarketBetter(", graph)
        self.assertIn("a.distance >= 43 && a.distance <= 80", graph)
        self.assertIn("OpexRoad100GBSelectDiverseMarkets(longPool)", candidates)
        self.assertIn("if (ROAD100_PAX_GRAPH_BRIDGE)\n"
                      "        longBest = OpexRoad100GBSelectDiverseMarkets(longPool);", candidates)
        self.assertIn("else\n        longBest = OpexRoad100LongSelectDiverse(longPool);", candidates)
        self.assertIn("ROAD100_PAX_GRAPH_BRIDGE && shortlist.len() > 1", planner)
        self.assertIn("OpexOpsMeasureEnd(mark) + 6000", planner)
        self.assertIn("exitCeiling > limitOps - 80000", planner)
        self.assertIn("graphExitScore <-", planner)
        self.assertIn('OpexDecide("ROAD100_GRAPH_SITE"', planner)
        self.assertIn("AIRoad.AreRoadTilesConnected(site.front, next)", front)
        self.assertIn("AIRoad.AreRoadTilesConnected(next, site.front)", front)
        self.assertIn("AITestMode()", front)
        self.assertIn("AIRoad.BuildRoad(site.front, next)", front)
        self.assertNotIn("RemoveRoad", front)
        self.assertIn("OpexRoad100LongVerifyTrace(trace, pair.a, pair.b,", planner)

    def test_rail_style_two_hop_site_rank_precedes_top3_without_faking_roads(self):
        graph = graph_source()
        planner = body("OpexRoad100LongConstructPlan", "builder_road.nut")
        scorer = body("OpexRoad100GBExistingExit", "road100_graph_bridge.nut")
        self.assertIn("Station->front is already proven", scorer)
        self.assertIn("ax >= ay ? [horizontal, vertical] : [vertical, horizontal]", scorer)
        self.assertIn("if (step == 0) continue", scorer)
        self.assertIn("OpexRoad100GBRoadEdge(site.front, next, cache)", scorer)
        self.assertIn("OpexRoad100GBRoadEdge(next, second, cache)", scorer)
        self.assertIn("AIMap.DistanceManhattan(site.front, next) != 1", scorer)
        self.assertIn("AIMap.DistanceManhattan(next, second) == 1", scorer)
        self.assertIn("OpexRoad100GBOccupied(next,", scorer)
        self.assertIn("OpexRoad100GBOccupied(second,", scorer)
        self.assertNotIn("AITestMode", scorer[scorer.index("{\n"):])
        self.assertNotIn("AIRoad.BuildRoad(", scorer)
        self.assertIn("return -1;", scorer)  # censored, not an impossibility
        self.assertIn("graphSiteRankCache = ROAD100_PAX_GRAPH_BRIDGE ?", planner)
        self.assertIn("OpexOpsMeasureEnd(mark) + 4000", planner)
        self.assertIn("graphSiteRankLimit = limitOps - 90000", planner)
        rank = planner.index("OpexRoad100GBExistingExit(pair.a, pair.b,")
        prune = planner.index("if (at >= 3) continue;")
        self.assertLess(rank, prune)
        self.assertIn("shortlist[at].graphRoadScore > pair.graphRoadScore", planner)
        self.assertIn("graphRoadScore ==\n            shortlist[j - 1].graphRoadScore", planner)
        self.assertIn("pre_top3_road=", planner)
        self.assertIn("site_rank_ops=", planner)
        self.assertIn("OpexRoad100LongVerifyTrace(trace, pair.a, pair.b,", planner)

    def test_rail_style_local_repair_is_bounded_and_must_reverify_entire_trace(self):
        repair = body("OpexRoad100GBRepairLocal", "road100_graph_bridge.nut")
        planner = body("OpexRoad100LongConstructPlan", "builder_road.nut")
        for guard in (
            "blockedIndex < 2", "original.len() < 43",
            "OpexOpsMeasureEnd(repairMark) >= 18000",
            "OpexOpsMeasureEnd(mark) >= limitOps - 50000",
            "expanded < 24", "nodes.len() >= 96", "current.depth >= 18",
            "nx < 0 || ny < 0 || nx >= width || ny >= height",
            "sourceDist > 11 || goalDist > 11",
            "current.tile == original[blockedIndex].from",
            "next == original[blockedIndex].to",
            "result.len() < 43 || result.len() > 190",
            "OpexRoadOnDtAxis(siteA.tile", "OpexRoadOnDtAxis(siteB.tile",
            "edge.to in visited", "UNBUILDABLE_TURN",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, repair)
        for forbidden in ("AITestMode(", "AIRoad.BuildRoad(",
                          "AIRoad.RemoveRoad(", "AIExecMode(",
                          "parent ="):
            self.assertNotIn(forbidden, repair)
        self.assertNotIn("OpexRoad100GBRoadEdge(current.tile, next, cache)", repair)
        self.assertNotIn("OpexRoad100GBOccupied(current.tile,", repair)
        self.assertIn("local dx = [1, -1, 0, 0]", repair)
        self.assertIn("local dy = [0, 0, 1, -1]", repair)
        self.assertIn("newCost = current.cost + 5", repair)
        self.assertNotRegex(repair, r"\.parent\b")
        attempt = planner.index("OpexRoad100GBRepairLocal(trace,")
        verify = planner.index("OpexRoad100LongVerifyTrace(graphRepair.trace,", attempt)
        accept = planner.index("if (repairRetest.ok)", verify)
        self.assertLess(attempt, verify)
        self.assertLess(verify, accept)
        self.assertIn('phase=local_repair reason=', planner)
        self.assertIn("checked.blocked_error == 260", planner)
        self.assertIn("checked.blocked_index < 40", planner)

    def test_graph_setting_is_zero_in_four_profiles_and_road_only(self):
        setting = graph_setting()
        for profile in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting, rf"\b{profile}_value\s*=\s*0\b")
        self.assertIn("AICONFIG_BOOLEAN", setting)
        self.assertIn("ROAD100_PAX_GRAPH_BRIDGE <- false;", read("globals_pre.nut"))
        settings = read("settings.nut")
        match = re.search(r"ROAD100_PAX_GRAPH_BRIDGE\s*=([^;]+);", settings)
        self.assertIsNotNone(match)
        for guard in (
            'GetSetting("road100_pax_graph_bridge") == 1',
            "ROAD100_LONG_BUILD", "MODE_ROAD", "!MODE_AIR",
            "!MODE_RAIL", "!MODE_WATER", "!ROAD100_SEGMENTED_CORRIDOR",
            "!ROAD100_SPARSE_CORRIDOR", "!ROAD100_PORTAL_STITCH",
        ):
            self.assertIn(guard, match.group(1))

    def test_dispatch_only_under_optin_and_existing_physical_gates(self):
        graph_source()
        graph_setting()
        planner = body("OpexRoad100LongConstructPlan", "builder_road.nut")
        self.assertIn("ROAD100_PAX_GRAPH_BRIDGE", planner)
        self.assertRegex(planner, r"OpexRoad100Graph\w*\(")
        self.assertIn("OpexRoad100LongVerifyTrace(trace, pair.a, pair.b,", planner)
        self.assertIn("mark, limitOps);", planner)
        self.assertIn("OpexRoad100LongDepotPreflight(trace, pair.a, pair.b,", planner)
        self.assertIn("quoteTotal = capital + capital / 4 + 50000", planner)
        self.assertIn("if (ROAD100_PAX_GRAPH_BRIDGE && shape != -3) break;", planner)
        self.assertIn("road100Graph = shape == -3 && ROAD100_PAX_GRAPH_BRIDGE", planner)


if __name__ == "__main__":
    unittest.main()
