"""ROAD100 V37: prospective source contracts and an independent route oracle.

Missing pieces of the concurrently developed opt-in are skipped explicitly.
Once a function appears, its contracts run. These Python checks cannot compile
Squirrel or certify that OpenTTD can build a complete road corridor.
"""

from __future__ import annotations

from dataclasses import dataclass
import heapq
import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
MODULE = AI / "road100_resumable_search.nut"


def src(filename: str) -> str:
    return (AI / filename).read_text(encoding="utf-8")


def module() -> str:
    if not MODULE.is_file():
        raise unittest.SkipTest("V37 road100_resumable_search.nut en cours d'edition")
    return MODULE.read_text(encoding="utf-8")


def nut_code(source: str) -> str:
    """Exclude strings and comments when checking executable Squirrel tokens."""
    pattern = r'/\*[\s\S]*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    return re.sub(pattern, lambda m: "\n" * m.group().count("\n") + " ", source)


def function(source: str, name: str) -> str:
    match = re.search(r"(?m)^\s*function\s+" + re.escape(name) + r"\s*\(", source)
    if match is None:
        raise unittest.SkipTest(f"V37 function {name} en attente")
    following = re.search(r"(?m)^\s*function\s+\w+\s*\(", source[match.end():])
    end = match.end() + following.start() if following else len(source)
    return source[match.start():end]


def function_by_suffix(source: str, suffixes: tuple[str, ...]) -> str:
    """Permit AStarStart/ResumableStart and Init aliases during integration."""
    names = re.findall(r"(?m)^\s*function\s+(OpexRoad100\w+)\s*\(", source)
    matching = [name for name in names if name.endswith(suffixes)]
    if not matching:
        raise unittest.SkipTest("V37 Start/Step function en attente")
    return function(source, matching[0])


def guarded_setting() -> str:
    settings = src("settings.nut")
    m = re.search(r"ROAD100_PAX_ASTAR_RESUME\s*=\s*(.*?);", settings, re.S)
    if m is None:
        raise unittest.SkipTest("V37 settings.nut en cours d'edition")
    return m.group(1)


class V37ConfigurationContracts(unittest.TestCase):
    def test_four_defaults_off_and_declared_global(self):
        info = src("info.nut")
        block = re.search(
            r'name\s*=\s*"road100_pax_astar_resume"\s*,(.*?)\}\s*\);',
            info, re.S,
        )
        if block is None:
            self.skipTest("V37 AddSetting en cours d'edition")
        for level in ("easy", "medium", "hard", "custom"):
            with self.subTest(level=level):
                self.assertRegex(block.group(1), rf"\b{level}_value\s*=\s*0\b")
        self.assertIn("AICONFIG_BOOLEAN", block.group(1))
        self.assertRegex(src("globals_pre.nut"),
                         r"ROAD100_PAX_ASTAR_RESUME\s*<-\s*false\b")

    def test_setting_requires_graph_and_road_only(self):
        guard = guarded_setting()
        for expected in (
            'AIController.GetSetting("road100_pax_astar_resume") == 1',
            "ROAD100_PAX_GRAPH_BRIDGE", "MODE_ROAD", "!MODE_AIR",
            "!MODE_RAIL", "!MODE_WATER",
        ):
            with self.subTest(required=expected):
                self.assertIn(expected, guard)
        # GRAPH itself requires LONG_BUILD and forbids other corridor modes.
        graph = re.search(r"ROAD100_PAX_GRAPH_BRIDGE\s*=\s*(.*?);",
                          src("settings.nut"), re.S)
        self.assertIsNotNone(graph)
        self.assertIn("ROAD100_LONG_BUILD", graph.group(1))


class V37ProspectiveModuleContracts(unittest.TestCase):
    def test_source_delimiters_and_reserved_squirrel_identifiers(self):
        code = nut_code(module())
        stack: list[str] = []
        matching = {")": "(", "]": "[", "}": "{"}
        for ch in code:
            if ch in "([{":
                stack.append(ch)
            elif ch in matching:
                self.assertTrue(stack, f"unmatched {ch}")
                self.assertEqual(stack.pop(), matching[ch])
        self.assertFalse(stack, f"unclosed delimiters {stack}")
        reserved = ("parent", "clone", "base", "static", "delegate", "vargc",
                    "vargv", "resume", "yield", "constructor", "instanceof")
        self.assertNotRegex(code,
                            r"\b(?:local|const)\s+(?:" + "|".join(reserved) + r")\b")
        self.assertNotRegex(code,
                            r"(?<!\w)(?:" + "|".join(reserved) + r")\s*(?:=|<-)")
        self.assertNotRegex(code, r"\bfunction\s*\(")
        self.assertNotIn(".find(", code)  # Not a Squirrel array method.

    def test_pathfinder_has_start_and_step_interfaces(self):
        source = module()
        start = nut_code(function_by_suffix(source, ("Start", "Init")))
        step = nut_code(function_by_suffix(source, ("Step", "Advance")))
        # V37 receives bounded (siteA, siteB) pairs; both endpoints are
        # validated by its normalizer before any search state is created.
        self.assertRegex(start, r"\bsitePairs\b")
        self.assertRegex(start, r"\bOpexRoad100V37SitePair\b")
        self.assertIn("siteA = null, siteB = null", start)
        self.assertRegex(start, r"\b(?:pairs|nodes|searchLimit)\b")
        self.assertRegex(step, r"\b(?:s|state|search)\b")
        self.assertRegex(step, r"\b(?:CONT|PENDING|FOUND|TRACE|NO_PATH|OPCAP|done|reason)\b")

    def test_search_never_builds_or_claims_a_speculative_link(self):
        code = nut_code(module())
        for forbidden in (
            "AITestMode(", "AIRoad.BuildRoad(", "AIRoad.RemoveRoad(",
            "AIRoad.BuildRoadDepot(", "AIRoad.BuildRoadStation(",
            "AIRoad.BuildDriveThroughRoadStation(", "AIVehicle.Build",
            "AIOrder.AppendOrder(", "AITile.DemolishTile(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)
        self.assertNotRegex(code, r"\bverified\s*(?:<-|=)\s*true\b")

    def test_existing_links_require_two_way_road_connectivity(self):
        source = module()
        code = nut_code(source)
        if "OpexRoad100GBRoadEdge(" in code:
            # Reuse of existing shared helper is allowed only if its proof is real.
            proof = nut_code(function(src("road100_graph_bridge.nut"),
                                      "OpexRoad100GBRoadEdge"))
            self.assertIn("AIRoad.AreRoadTilesConnected(fromTile, toTile)", proof)
            self.assertIn("AIRoad.AreRoadTilesConnected(toTile, fromTile)", proof)
        else:
            self.assertGreaterEqual(code.count("AIRoad.AreRoadTilesConnected("), 2)
        # Merely two adjacent road tiles are never a proven connection.
        self.assertRegex(code, r"OpexRoad100GBRoadEdge|AIRoad\.AreRoadTilesConnected")

    def test_foreign_stations_depots_cycles_and_map_edges_are_checked(self):
        code = nut_code(module())
        self.assertRegex(code, r"OpexRoad100GBOccupied|IsRoadStationTile|IsStationTile")
        self.assertRegex(code, r"OpexRoad100GBOccupied|IsRoadDepotTile")
        self.assertRegex(code, r"\b(?:seen|visited|closed|occupied|bestByKey|cheapest)\b")
        self.assertRegex(code, r"AIMap\.IsValidTile|GetMapSizeX|OpexRoadInMap")
        self.assertRegex(code, r"\b(?:direction|step|incoming|axis)\b")

    def test_node_length_and_opcode_limits_are_explicit(self):
        code = nut_code(module())
        self.assertRegex(code, r"\b(?:maxNodes|maxStates|nodeCap|stateCap|NODE_CAP|STATE_CAP|ROAD100_V37_MAX_STATES)\b")
        self.assertRegex(code, r"\b(?:sliceOps|maxSliceOps|opsBudget|budgetOps|OPCAP|budget)\b")
        self.assertRegex(code, r"OpexOpsMeasureEnd|GetOpsTillSuspend|OpexOpsClock")
        self.assertRegex(code, r"\b190\b|MAX_ROUTE|MAX_LENGTH")
        self.assertRegex(code, r"\b43\b|MIN_ROUTE|MIN_LENGTH")


class V37ProspectiveCallerContracts(unittest.TestCase):
    def test_v37_reference_is_gated_and_reverified_by_common_builder(self):
        if not MODULE.is_file():
            self.skipTest("V37 integration en cours; nouveau module absent")
        builder = src("builder_road.nut")
        generator = src("candidates.nut")
        po01c = src("po01c_regen.nut")
        combined = builder + generator + po01c
        if "ROAD100_PAX_ASTAR_RESUME" not in combined:
            self.skipTest("V37 caller en cours d'edition")
        self.assertIn("ROAD100_PAX_ASTAR_RESUME", combined)
        entry = function(builder, "OpexRoad100LongConstructPlan")
        self.assertIn("OpexRoad100LongVerifyTrace(", entry)
        self.assertIn("OpexRoad100LongDepotPreflight(", entry)
        self.assertIn("missing * catalog.costRoadPerTile * 3", entry)
        self.assertIn("quoteTotal = capital + capital / 4 + 50000", entry)
        self.assertIn("OpexRoadBuildTrace(plan.trace, added)",
                      function(builder, "OpexBuildRoadRoute"))
        self.assertIn("OpexRoadRollback(", function(builder, "OpexBuildRoadRoute"))
        self.assertIn("OpexRoad100LongTraceHash", generator)
        self.assertIn("yield null;", generator)
        self.assertIn("OpexRoad100SiteFirstGenerator", po01c)


@dataclass(frozen=True)
class Macro:
    """A proposed corridor edge; only bidirectional old links are physical."""

    start: tuple[int, int]
    end: tuple[int, int]
    tiles: tuple[tuple[int, int], ...]
    forward: bool = False
    backward: bool = False
    buildable: bool = True


def oracle_route(
    starts: tuple[tuple[int, int], ...],
    goals: tuple[tuple[int, int], ...],
    macros: tuple[Macro, ...],
    occupied: frozenset[tuple[int, int]] = frozenset(),
    max_nodes: int = 96,
    expansions_per_slice: int = 4,
    cost_per_expansion: int = 1301,
    slice_budget: int = 8000,
    total_budget: int = 42000,
) -> dict:
    """Independent tiny graph oracle with resumable macro-edges, no game calls.

    It models the semantic gates, not the Squirrel implementation. Callers may
    change slice size without changing selection when budgets permit.
    """
    assert expansions_per_slice > 0 and slice_budget > 0 and max_nodes > 0
    outgoing: dict[tuple[int, int], list[Macro]] = {}
    for link in macros:
        outgoing.setdefault(link.start, []).append(link)
    heap: list[tuple[int, int, int, tuple[int, int], tuple[tuple[int, int], ...]]] = []
    order = 0
    for source_id, site in enumerate(starts):
        heapq.heappush(heap, (0, order, source_id, site, (site,)))
        order += 1
    best = {}
    expanded = 0
    spent = 0
    slices = 0
    goals_set = set(goals)
    while heap:
        remaining = min(expansions_per_slice, slice_budget // cost_per_expansion)
        if remaining < 1:
            return {"reason": "SLICE_TOO_SMALL", "expanded": expanded, "ops": spent}
        slices += 1
        while heap and remaining:
            if spent + cost_per_expansion > total_budget:
                return {"reason": "OPCAP", "expanded": expanded, "ops": spent,
                        "slices": slices}
            cost, _, source_id, tile, path = heapq.heappop(heap)
            key = (source_id, tile, len(path))
            if cost > best.get(key, cost):
                continue
            expanded += 1
            spent += cost_per_expansion
            remaining -= 1
            if tile in goals_set and tile != starts[source_id] and 43 <= len(path) - 1 <= 190:
                return {"reason": "TRACE_NEEDS_VERIFY", "path": path,
                        "source": source_id, "goal": tile, "expanded": expanded,
                        "ops": spent, "slices": slices, "verified": False}
            if expanded >= max_nodes:
                return {"reason": "NODE_CAP", "expanded": expanded, "ops": spent,
                        "slices": slices}
            for link in outgoing.get(tile, ()):
                if not link.buildable and not (link.forward and link.backward):
                    continue
                if link.tiles[0] != tile or link.tiles[-1] != link.end:
                    continue
                if any(p in occupied or p in path for p in link.tiles[1:]):
                    continue
                if any(abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1
                       for a, b in zip(link.tiles, link.tiles[1:])):
                    continue
                full = path + link.tiles[1:]
                if len(full) - 1 > 190:
                    continue
                real = link.forward and link.backward
                proposed = cost + (1 if real else 5) * (len(link.tiles) - 1)
                next_key = (source_id, link.end, len(full))
                if proposed >= best.get(next_key, float("inf")):
                    continue
                best[next_key] = proposed
                heapq.heappush(heap, (proposed, order, source_id, link.end, full))
                order += 1
    return {"reason": "NO_PATH", "expanded": expanded, "ops": spent,
            "slices": slices}


class V37IndependentOracleTests(unittest.TestCase):
    @staticmethod
    def line(a: int, b: int, y: int = 0, **kw) -> Macro:
        return Macro((a, y), (b, y), tuple((x, y) for x in range(a, b + 1)), **kw)

    def test_multi_source_and_goal_skip_unbuildable_high_rank_site(self):
        links = (self.line(0, 20), self.line(20, 45), self.line(1, 20),
                 self.line(45, 70), self.line(70, 85))
        outcome = oracle_route(((0, 0), (1, 0)), ((85, 0), (150, 0)), links)
        self.assertEqual(outcome["reason"], "TRACE_NEEDS_VERIFY")
        self.assertEqual(outcome["source"], 1)  # Starts from shorter site 1.
        self.assertEqual(outcome["goal"], (85, 0))
        self.assertFalse(outcome["verified"])
        self.assertEqual(len(set(outcome["path"])), len(outcome["path"]))

    def test_two_road_tiles_without_link_do_not_become_a_real_edge(self):
        # `forward` alone means no physical connectivity in both directions.
        unbuildable = (self.line(0, 44, forward=True, backward=False, buildable=False),)
        self.assertEqual(oracle_route(((0, 0),), ((44, 0),), unbuildable)["reason"],
                         "NO_PATH")
        proposed = (self.line(0, 44, forward=True, backward=False),)
        self.assertEqual(oracle_route(((0, 0),), ((44, 0),), proposed)["reason"],
                         "TRACE_NEEDS_VERIFY")

    def test_occupied_foreign_station_and_depot_veto(self):
        road = (self.line(0, 45),)
        for tile in ((12, 0), (40, 0)):
            with self.subTest(tile=tile):
                self.assertEqual(oracle_route(((0, 0),), ((45, 0),), road,
                        occupied=frozenset({tile}))["reason"], "NO_PATH")

    def test_incremental_slices_do_not_reset_total_opcode_cap(self):
        links = (self.line(0, 15), self.line(15, 30), self.line(30, 45))
        small = oracle_route(((0, 0),), ((45, 0),), links,
                             expansions_per_slice=2)
        wide = oracle_route(((0, 0),), ((45, 0),), links,
                            expansions_per_slice=5)
        self.assertEqual(small["reason"], "TRACE_NEEDS_VERIFY")
        self.assertEqual(small["path"], wide["path"])
        self.assertGreater(small["slices"], wide["slices"])
        for got in (small, wide):
            self.assertLessEqual(got["ops"], 42000)
        budget = oracle_route(((0, 0),), ((45, 0),), links,
                              expansions_per_slice=2, total_budget=3903)
        self.assertEqual(budget["reason"], "OPCAP")
        self.assertLessEqual(budget["ops"], 3903)

    def test_bounds_and_oversize_corridor_do_not_publish_a_trace(self):
        too_short = (self.line(0, 42),)
        too_long = (self.line(0, 191),)
        self.assertEqual(oracle_route(((0, 0),), ((42, 0),), too_short)["reason"],
                         "NO_PATH")
        self.assertEqual(oracle_route(((0, 0),), ((191, 0),), too_long)["reason"],
                         "NO_PATH")

    def test_no_teleport_or_cycle_and_expansion_cap(self):
        diagonal = (Macro((0, 0), (45, 1), ((0, 0), (45, 1))),)
        self.assertEqual(oracle_route(((0, 0),), ((45, 1),), diagonal)["reason"],
                         "NO_PATH")
        cycle = (self.line(0, 20), self.line(20, 40),
                 Macro((40, 0), (20, 0), tuple((x, 0) for x in range(40, 19, -1))))
        self.assertEqual(oracle_route(((0, 0),), ((65, 0),), cycle)["reason"],
                         "NO_PATH")
        capped = oracle_route(((0, 0),), ((45, 0),),
                              (self.line(0, 15), self.line(15, 30), self.line(30, 45)),
                              max_nodes=2)
        self.assertEqual(capped["reason"], "NODE_CAP")


if __name__ == "__main__":
    unittest.main()
