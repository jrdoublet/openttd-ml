"""V296b static contracts; these do not compile Squirrel or qualify opcode savings."""
import re
import unittest
from pathlib import Path

from test_b5_rail_persistence import function_body

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def normalized(text):
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    return re.sub(r"\s+", "", text)


class TestV296Native(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = read("pathfinder_v90/v296.nut")
        cls.old = read("pathfinder_v90/v129.nut")
        cls.hot = function_body(cls.src, "function OpexRailPathFinderV296::_FindPathV296(iterations)")

    def test_setting_and_load_order(self):
        block = re.search(r'AddSetting\(\{\s*name = "v296_astar_native",(.*?)\}\);', read("info.nut"), re.S)
        self.assertIsNotNone(block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block[1], rf"{level}_value\s*=\s*1\b")
        self.assertIn("min_value = 0, max_value = 2", block[1])
        self.assertIn("V296_ASTAR_NATIVE <- 1;", read("globals_pre.nut"))
        settings = read("settings.nut")
        self.assertEqual(settings.count('GetSetting("v296_astar_native")'), 1)
        self.assertIn("v296Astar >= 0 && v296Astar <= 2", settings)
        main = read("main.nut")
        self.assertLess(main.index('require("pathfinder_v90/v129.nut")'), main.index('require("pathfinder_v90/v296.nut")'))
        self.assertLess(main.index('require("pathfinder_v90/v296.nut")'), main.index('require("builder_rail.nut")'))

    def test_factory_default_is_still_v129(self):
        body = function_body(self.old, "function OpexNewRailPathfinderV129()")
        self.assertEqual(normalized(body), normalized('''
            if (V296_ASTAR_NATIVE == 2) return OpexRailPathfinderCheckerV296();
            if (V296_ASTAR_NATIVE == 1) return OpexRailPathFinderV296();
            return OpexRailPathFinderV129();
        '''))

    def test_native_queue_and_fifo_ids(self):
        self.assertIn("this._pathfinder._open = AIList();", self.src)
        self.assertIn("Sort(AIList.SORT_BY_VALUE, true)", self.src)
        for fragment in ("local id = open.Begin();", "open.RemoveItem(id);",
                         "local nid = tiles.len();", "open.AddItem(nid, c + estimate);"):
            self.assertIn(fragment, self.hot)
        self.assertNotIn("OpexBinaryHeap", self.src)

    def test_hot_loop_has_no_callbacks_or_path_objects(self):
        for fragment in ("_Cost(", "_Neighbours(", "_Estimate(", "_EstimateWeighted(",
                         "_callback", ".Path(", "GetParent(", "[[", "function("):
            self.assertNotIn(fragment, self.hot)
        for array in ("tiles", "dirs", "costs", "parents", "blooms"):
            self.assertIn(f"{array}.append(", self.hot)

    def test_entire_inline_cost_is_v129_cost_with_array_reads(self):
        old_cost = function_body(self.old, "function _Cost(path, new_tile, new_direction, self)")
        expected = old_cost[old_cost.index("local step_cost"):old_cost.index("return path._cost")]
        for old, new in (("par._prev", "parents[par]"), ("gp._prev", "parents[gp]"),
                         ("ggp._tile", "tiles[ggp]"), ("gp._tile", "tiles[gp]"), ("par._tile", "tiles[par]")):
            expected = expected.replace(old, new)
        for name in ("par", "gp", "ggp"):
            expected = expected.replace(name + " != null", name + " >= 0")
        expected = re.sub(r"self\.(_(?:cost_\w+|v214\w+|guideTiles|outwardSide))", r"c\1", expected)
        expected = expected.replace("self.", "this.")
        actual = self.hot.split("// BEGIN V129 COST:", 1)[1].split("\n", 1)[1].split("// END V129 COST", 1)[0]
        self.assertEqual(normalized(actual), normalized(expected))

    def test_cost_locals_are_bound_outside_loop(self):
        prefix, loop = self.hot.split("while (!open.IsEmpty()", 1)
        for var in set(re.findall(r"\bc_\w+", loop)):
            self.assertIn(f"local {var} = this.{var[1:]};", prefix)

    def test_collision_and_max_cost_preserved(self):
        self.assertIn("(cd & direction) != 0", self.hot)
        self.assertIn("blooms[par] & (1 << (cur % 61))", self.hot)
        self.assertIn("while (scan >= 0 && tiles[scan] != cur) scan = parents[scan];", self.hot)
        self.assertIn("costs[id] >= maxCost", self.hot)
        self.assertNotIn("c + estimate >= maxCost", self.hot)
        check = function_body(read("pathfinder_v90/rail.nut"),
                              "function OpexRailPathFinderV90::_CheckDirection(tile, existing_direction, new_direction, self)")
        self.assertEqual(normalized(check), "returnfalse;")

    def test_neighbour_geometry_and_structure_tests(self):
        for fragment in ("new_tile == parTile", "offsets[slot] == blocked",
                         "AIRail.BuildRail(parTile, cur, new_tile)",
                         "AIRail.BuildRail(cur, nextAfter, nextAfter + offsets[slot])",
                         "this._GetDirection(parTile, cur, nextAfter, true)",
                         "this._GetDirection(tiles[grand], parTile, cur, true)",
                         "AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridgeTable[length], cur, new_tile)",
                         "AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur)",
                         "length >= maxTunnel", "before != parTile"):
            self.assertIn(fragment, self.hot)

    def test_structure_schedule_includes_tunnel_with_no_bridge_lengths(self):
        # Independent expected order of V129's bridge loop + final tunnel.
        for maximum in range(0, 24):
            stop = max(4, maximum + 2)
            actual = [slot - 2 if slot < stop else "tunnel" for slot in range(4, stop + 1)]
            self.assertEqual(actual, list(range(2, maximum)) + ["tunnel"])
        self.assertIn("local bridgeStop = max(4, maxBridge + 2);", self.hot)
        self.assertIn("slot <= bridgeStop", self.hot)

    def test_goal_exit_checked_before_closed_direction_filter(self):
        acceptance = self.hot.index('goal[1] == new_tile')
        self.assertLess(acceptance, self.hot.index('if ((new_tile in closed)'))
        finish = function_body(self.src, "function _Finish(id)")
        self.assertIn('goal[0] == result.GetTile()', finish)
        self.assertIn('this._Cost(result, goal[1], 0, this)', finish)

    def test_estimate_integer_clamp_and_single_goal(self):
        for fragment in ("local single = coords.len() == 1;", "if (single)", "foreach (g in coords)",
                         "lo * diag2 + (hi - lo) * c_cost_tile",
                         "weight > 100 && minCost < maxCost ? (minCost * weight) / 100 : minCost",
                         "cache[new_tile] <- estimate;"):
            self.assertIn(fragment, self.hot)

    def test_public_interface_and_path_output(self):
        self.assertIn("extends OpexRailPathFinderV129", self.src)
        for method in ("InitializePath", "FindPath", "SetWeight", "Materialize", "FrontierAlternatives"):
            self.assertIn("function " + method + "(", self.src)
        self.assertIn("function LastConsumed()", self.old)
        for method in ("GetTile", "GetParent", "GetCost", "GetDirection"):
            self.assertIn("function " + method + "()", self.old)
        materialize = function_body(self.src, "function Materialize(id)")
        self.assertIn("OpexAyStarV129.Path(", materialize)
        self.assertIn("n = this._parents[n]", materialize)
        self.assertIn("this._consumed = pops == 0 ? 1 : pops;", self.hot)
        self.assertIn("this._running = true;", self.hot)

    def test_frontier_does_not_mutate_native_queue(self):
        body = function_body(self.src, "function FrontierAlternatives(limit)")
        for fragment in ("open.Begin()", "open.Next()", "open.IsEnd()", "result.len() < limit", "this.Materialize(id)"):
            self.assertIn(fragment, body)
        self.assertNotIn("RemoveItem", body)
        self.assertNotIn("._items", body)
        self.assertIn('if ("FrontierAlternatives" in pathfinder)', read("builder_rail.nut"))

    def test_sources_import_complete_ancestry_and_rebuild_bloom(self):
        init = function_body(self.src, "function _InitializePathV296(sources, goals, ignored_tiles = [])")
        self.assertIn("n = n.GetParent()", init)
        self.assertIn("n.GetCost(), id", init)
        self.assertIn("this._pathfinder._open.AddItem(id, this._costs[id]);", init)
        self.assertNotIn(".Path(", init)
        append = function_body(self.src, "function _Append(tile, direction, cost, parentId)")
        self.assertIn("this._blooms[parentId]) | (1 << (tile % 61))", append)

    def test_no_squirrel_reserved_identifier(self):
        """`parent` est un mot reserve de la VM d'OpenTTD : echec de compilation au premier banc (21/10)."""
        self.assertIsNone(re.search(r"\bparent\b", self.src))
        # `base` n'existe pas dans la VM d'OpenTTD (smoke GitHub du 21/10) : appels explicites a la classe.
        self.assertIsNone(re.search(r"\bbase\.", self.src))
        self.assertIn("OpexRailPathFinderV129.constructor.call(this, weight);", self.src)
        # Aucun Classe.methode.call(this, ...) hors constructeur : le script ne peut pas se suspendre
        # dans un appel natif, et OpenTTD refuse alors les commandes de l'A* (banc VPS du 21/10).
        self.assertEqual(self.src.count(".call(this"), 1)
        for name in ("SetWeight", "InitializePath", "FindPath"):
            self.assertIn(f"this._{name}V296(", self.src)

    def test_checker_independent_completion_and_measurements(self):
        checker = self.src.split("class OpexRailPathfinderCheckerV296", 1)[1]
        for key in ("iters_v129", "iters_v296", "cost_v129", "cost_v296", "ops_v129", "ops_v296",
                    "found_v129", "found_v296", "complete_v129", "complete_v296", "cost_equal"):
            self.assertIn(key + "=", checker)
        for fragment in ("if (DECISION_LOG)", "OpexOpsMeasureBegin()", "OpexOpsMeasureEnd(mark)",
                         "AITestMode()", "this._referenceResult != false", "return result;",
                         "this._reference._v214RouteDist = this._v214RouteDist;"):
            self.assertIn(fragment, checker)
        # Every inherited Cost parameter must be copied to the reference.
        keys = set(re.findall(r'case "([a-z_0-9]+)":', read("pathfinder_v90/rail.nut")))
        for key in keys:
            self.assertIn('"' + key + '"', checker)

    def test_no_persistence_of_native_state(self):
        persist = read("persist.nut")
        save = function_body(persist, "function OpexAI::Save()")
        self.assertIn("railSearchPending = this._railSearch != null", save)
        self.assertNotRegex(save, r"=\s*this\._railSearch\s*[,;]")
        worker = function_body(persist, "function OpexSaveActiveWorker(worker)")
        self.assertIn('worker.kind == "rail_search" || worker.kind == "rail_stock"', worker)
        self.assertIn("state = {}", worker)

    def test_no_unsupported_squirrel_constructs(self):
        self.assertNotIn(".find(", self.src)
        self.assertNotRegex(self.src, r"function\s*\(")
        self.assertNotRegex(self.src, r"local\s+(?:clone|base|pass)\b")


if __name__ == "__main__":
    unittest.main()
