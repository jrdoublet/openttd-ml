"""Source contracts for experimental ROAD100 sparse corridors.

No OpenTTD gameplay runs here. The engine smoke and physical preflight
remain necessary before an opt-in path can be used for construction.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
SOURCE = (ROOT / "road100_sparse_corridor.nut").read_text(encoding="utf-8")
BUILDER = (ROOT / "builder_road.nut").read_text(encoding="utf-8")


def body(name):
    start = SOURCE.index("function " + name + "(")
    end = SOURCE.find("\nfunction ", start + len("function "))
    return SOURCE[start:end if end >= 0 else len(SOURCE)]


class SparseCorridorContracts(unittest.TestCase):
    def test_squirrel_delimiters_and_reserved_identifiers(self):
        # This catches source-edit slips but is not a Squirrel compilation.
        clean = re.sub(r"/\*.*?\*/|//[^\n]*|\"(?:\\.|[^\"\\])*\"",
                       "", SOURCE, flags=re.S)
        stack = []
        matching = {")": "(", "]": "[", "}": "{"}
        for char in clean:
            if char in "([{":
                stack.append(char)
            elif char in matching:
                self.assertTrue(stack)
                self.assertEqual(stack.pop(), matching[char])
        self.assertFalse(stack)
        self.assertNotRegex(clean, r"\b(?:const|clone|resume|yield|base)\s*=")

    def test_entrypoint_is_isolated_and_matches_existing_edge_contract(self):
        entry = body("OpexRoad100SparseCorridorTrace")
        self.assertIn("siteA, siteB, mark, limitOps", entry)
        self.assertIn("trace = null, reason =", entry)
        self.assertIn("ops = 0", entry)
        self.assertIn("stats = {", entry)
        self.assertIn("out.trace = bestTrace;", entry)
        self.assertIn("trace.append({ from = path[p - 1], to = path[p] })",
                      body("OpexRoad100SparseTrial"))
        self.assertIn("function OpexRoad100LongVerifyTrace(trace, siteA, siteB, mark, limitOps)",
                      BUILDER)
        self.assertIn("if (trace == null || trace.len() < 80 || trace.len() > 190)",
                      BUILDER)

    def test_builder_calls_sparse_only_via_optin_and_revalidates(self):
        self.assertIn('require("road100_sparse_corridor.nut");', BUILDER)
        self.assertIn("ROAD100_SPARSE_CORRIDOR ? -2", BUILDER)
        self.assertIn("if (shape == -2)", BUILDER)
        self.assertIn("OpexRoad100SparseCorridorTrace(pair.a, pair.b,", BUILDER)
        self.assertIn("checked = OpexRoad100LongVerifyTrace(trace, pair.a, pair.b,",
                      BUILDER)
        self.assertIn("OpexRoad100LongDepotPreflight(trace, pair.a, pair.b,",
                      BUILDER)
        self.assertIn("road100Sparse = shape == -2", BUILDER)

    def test_fronts_need_actual_two_way_connectivity_and_axial_exit(self):
        entry = body("OpexRoad100SparseCorridorTrace")
        for fragment in (
            "AIMap.DistanceManhattan(siteA.tile, siteA.front) != 1",
            "AIMap.DistanceManhattan(siteB.tile, siteB.front) != 1",
            "AIRoad.AreRoadTilesConnected(siteA.tile, siteA.front)",
            "AIRoad.AreRoadTilesConnected(siteA.front, siteA.tile)",
            "AIRoad.AreRoadTilesConnected(siteB.front, siteB.tile)",
            "AIRoad.AreRoadTilesConnected(siteB.tile, siteB.front)",
        ):
            self.assertIn(fragment, entry)
        trial = body("OpexRoad100SparseTrial")
        for fragment in (
            "local startStep = siteA.front - siteA.tile;",
            "local finishStep = siteB.front - siteB.tile;",
            "local launch = siteA.front + startStep;",
            "local approach = siteB.front + finishStep;",
            "AIMap.DistanceManhattan(siteA.front, launch) != 1",
            "AIMap.DistanceManhattan(siteB.front, approach) != 1",
            "local path = [siteA.tile, siteA.front, launch];",
            "path.append(siteB.front);",
            "path.append(siteB.tile);",
            "path[path.len() - 3] != approach",
        ):
            self.assertIn(fragment, trial)

    def test_sparse_search_has_small_bounded_subproblems_and_no_cycles(self):
        entry = body("OpexRoad100SparseCorridorTrace")
        gap = body("OpexRoad100SparseGap")
        trial = body("OpexRoad100SparseTrial")
        self.assertIn("for (local scan = 0; scan < 48; scan++)", gap)
        self.assertIn("if (current.depth >= 19) continue;", gap)
        self.assertIn("local stateKey = next * 4 + d;", gap)
        self.assertIn("if (next in banned", gap)
        self.assertIn("next in occupied", gap)
        self.assertIn("path.len() - 1 > 190", trial)
        self.assertIn("if (next in occupied || path.len() >= 189", trial)
        self.assertIn("occupied.rawset(next, true)", trial)
        self.assertIn("local gaps = (distance + 9) / 10;", trial)
        self.assertIn("if (gaps > 18)", trial)
        self.assertIn("for (local variant = 0; variant < 4; variant++)", entry)
        self.assertIn("local banned = {};", entry)
        self.assertIn("for (local attempt = 0; attempt < 2; attempt++)", entry)

    def test_flat_turns_and_test_only_construction(self):
        self.assertIn("AITile.GetSlope(current) == AITile.SLOPE_FLAT",
                      body("OpexRoad100SparseTurn"))
        self.assertIn("AITile.GetSlope(current.tile) != AITile.SLOPE_FLAT",
                      body("OpexRoad100SparseGap"))
        self.assertIn("!OpexRoad100SparseTurn(path[path.len() - 2],",
                      body("OpexRoad100SparseTrial"))
        self.assertIn("!OpexRoad100SparseTurn(approach, siteB.front,",
                      body("OpexRoad100SparseTrial"))
        self.assertIn("AITile.IsBuildable(tile)", body("OpexRoad100SparseUsable"))
        check = body("OpexRoad100SparseTestTrace")
        self.assertIn("local test = AITestMode(); allowed = AIRoad.BuildRoad(", check)
        self.assertIn("if (!allowed)", check)
        self.assertIn("out.bad_tile = edge.to;", check)
        self.assertEqual(len(re.findall(r"\bAIRoad\.BuildRoad\s*\(", SOURCE)), 1)
        for disallowed in (
            "AIVehicle.", "AIRoad.BuildRoadDepot", "AIRoad.BuildRoadStation",
            "AIRoad.BuildDriveThroughRoadStation", "Pathfinder.",
            "AIRoad.SetCurrentRoadType", "function(", ".find(",
        ):
            # Comments document the forbidden real operations; only examine
            # actual source statements here.
            clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", SOURCE, flags=re.S)
            self.assertNotIn(disallowed, clean)

    def test_strict_opcode_budget_and_quoted_route_only(self):
        entry = body("OpexRoad100SparseCorridorTrace")
        trial = body("OpexRoad100SparseTrial")
        check = body("OpexRoad100SparseTestTrace")
        self.assertIn("local globalAtEntry = OpexOpsMeasureEnd(mark);", entry)
        self.assertIn("local ceiling = globalAtEntry + 100000;", entry)
        self.assertIn("if (ceiling > limitOps - 65000) ceiling = limitOps - 65000;", entry)
        self.assertIn("if (ceiling <= globalAtEntry)", entry)
        self.assertIn("if (OpexOpsMeasureEnd(startMark) >= 105000", entry)
        self.assertIn("out.ops <= 110000", entry)
        self.assertIn("OpexOpsMeasureEnd(mark) >= ceiling", trial)
        self.assertIn("OpexOpsMeasureEnd(mark) >= ceiling", check)
        self.assertIn("OpexOpsMeasureEnd(mark) >= ceiling", body("OpexRoad100SparseGap"))
        self.assertNotIn("OpexRoad100LongVerifyTrace(", SOURCE)
        self.assertNotIn("OpexRoad100LongDepotPreflight(", SOURCE)
        self.assertNotIn("OpexRoad100LongQuotedEconomics(", SOURCE)
        self.assertNotIn("OpexBuildRoadRoute(", SOURCE)

    def test_global_builder_counter_does_not_exhaust_local_budget_before_start(self):
        """Two site scans may spend >110k before this module is entered."""
        for spent, limit in ((140_000, 400_000), (190_000, 400_000),
                             (90_000, 180_000), (340_000, 400_000)):
            ceiling = min(spent + 100_000, limit - 65_000)
            if spent < limit - 65_000:
                self.assertGreater(ceiling, spent)
                self.assertLessEqual(ceiling - spent, 100_000)
                self.assertLessEqual(ceiling, limit - 65_000)
            else:
                self.assertLessEqual(ceiling, spent)


if __name__ == "__main__":
    unittest.main()
