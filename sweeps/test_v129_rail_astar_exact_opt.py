#!/usr/bin/env python3
"""Contrats statiques V129 : A* rail a exploration identique, moins couteux en opcodes.

Verifie, sans lancer OpenTTD :
1. reglages v129_rail_astar_exact_opt / v129_rail_astar_check declares (booleens, quatre *_value a 0) ;
2. globales declarees dans globals_pre.nut et lues une seule fois dans settings.nut ;
3. a 0, les sites d'instanciation retombent sur le code V90 existant et la boucle FindPath(1) historique reste ;
4. v129.nut charge apres rail.nut, classes distinctes de V90, aucun if dans la boucle chaude du tas / de l'A* ;
5. points d'optimisation presents (tas parallele, cout sans GetParent, voisins sans tableau intermediaire,
   cache d'heuristique, table de ponts en cache, consommation d'iterations) ;
6. verification pas a pas V129_CHECK ;
7. champ search_ops sur RAIL_ATTEMPT, calcule seulement sous DECISION_LOG.
"""

from __future__ import annotations

import re
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]

try:
    import openttdlab  # noqa: F401
except ImportError:
    fake_lab = types.ModuleType("openttdlab")
    fake_lab.bananas_ai = mock.MagicMock()
    fake_lab.bananas_ai_library = mock.MagicMock()
    fake_lab.local_folder = mock.MagicMock()
    fake_lab.run_experiments = mock.MagicMock()
    sys.modules["openttdlab"] = fake_lab

sys.path.insert(0, str(ROOT / "sweeps"))
from campaign_freeze import parse_ai_settings, parse_ai_setting_specs  # noqa: E402


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _body(src: str, start_marker: str, end_marker: str) -> str:
    start = src.index(start_marker)
    return src[start:src.index(end_marker, start)]


class TestV129Settings(unittest.TestCase):
    def test_settings_declared_default_zero(self):
        info = _read("ai/OpexAI/info.nut")
        for name, want in (("v129_rail_astar_exact_opt", 1), ("v129_rail_astar_check", 0)):
            start = info.index(f'name = "{name}"')
            block = info[start:info.index("});", start)]
            self.assertIn("flags = AICONFIG_BOOLEAN", block)
            for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
                self.assertIn(f"{key} = {want}", block)

    def test_parsed_defaults(self):
        info_path = ROOT / "ai/OpexAI/info.nut"
        defaults = parse_ai_settings(info_path)
        specs = parse_ai_setting_specs(info_path)
        for name, want in (("v129_rail_astar_exact_opt", 1), ("v129_rail_astar_check", 0)):
            self.assertEqual(defaults[name], want)
            self.assertTrue(specs[name]["boolean"])

    def test_globals_and_single_read(self):
        glob = _read("ai/OpexAI/globals_pre.nut")
        self.assertIn("V129_RAIL_ASTAR_EXACT_OPT <- true;", glob)
        self.assertIn("V129_RAIL_ASTAR_CHECK <- false;", glob)
        settings = _read("ai/OpexAI/settings.nut")
        for name, glob_name in (("v129_rail_astar_exact_opt", "V129_RAIL_ASTAR_EXACT_OPT"),
                                ("v129_rail_astar_check", "V129_RAIL_ASTAR_CHECK")):
            self.assertIn(f'{glob_name} = AIController.GetSetting("{name}") != 0;', settings)
            total = sum(_read(str(p.relative_to(ROOT))).count(f'GetSetting("{name}")')
                        for p in (ROOT / "ai/OpexAI").rglob("*.nut"))
            self.assertEqual(total, 1)


class TestV129ZeroPathUnchanged(unittest.TestCase):
    def test_instantiation_sites_keep_v90_branch(self):
        src = _read("ai/OpexAI/builder_rail.nut")
        self.assertEqual(src.count("pathfinder = OpexNewRailPathfinderV129();"), 2)
        self.assertEqual(src.count("pathfinder = OpexRailPathfinderCheckerV90();"), 2)
        self.assertEqual(src.count("pathfinder = OpexRailPathFinderV90();"), 2)
        self.assertEqual(src.count("pathfinder = RailPathFinder();"), 2)

    def test_historical_loop_kept_and_batch_is_outside_it(self):
        src = _read("ai/OpexAI/builder_rail.nut")
        self.assertIn("state.segmentPath = state.pathfinder.FindPath(1);", src)
        gate = "if (V129_RAIL_ASTAR_EXACT_OPT && V90_FAST_PATHFINDER && sleepTicks <= 0) {"
        self.assertEqual(src.count(gate), 1)
        # le groupage est borne par toutes les limites de la boucle historique
        batch = _body(src, gate, "state.segmentPath = state.pathfinder.FindPath(1);")
        for limit in ("state.currentSegmentLimit - state.segmentUsed",
                      "state.iterationBudget - state.iterations",
                      "state.timeSafe - state.iterations",
                      "sliceIters - sliceSpent",
                      "state.pathfinder.LastConsumed()"):
            self.assertIn(limit, batch)

    def test_v90_files_untouched_hot_paths(self):
        for f in ("aystar.nut", "binary_heap.nut", "rail.nut"):
            self.assertNotIn("V129", _read(f"ai/OpexAI/pathfinder_v90/{f}"))

    def test_load_order(self):
        main = _read("ai/OpexAI/main.nut")
        self.assertLess(main.index('require("pathfinder_v90/rail.nut");'),
                        main.index('require("pathfinder_v90/v129.nut");'))
        self.assertLess(main.index('require("pathfinder_v90/v129.nut");'),
                        main.index('require("builder_rail.nut");'))


class TestV129Implementation(unittest.TestCase):
    def setUp(self):
        self.v129 = _read("ai/OpexAI/pathfinder_v90/v129.nut")

    def test_distinct_class_names(self):
        for cls in ("OpexBinaryHeapV129", "OpexAyStarV129", "OpexRailPathFinderV129",
                    "OpexRailPathfinderCheckerV129"):
            self.assertIn(f"class {cls}", self.v129)
        self.assertIn("class OpexRailPathFinderV129 extends OpexRailPathFinderV90", self.v129)

    def test_no_v129_flag_test_in_hot_loops(self):
        for marker, end in (("function OpexAyStarV129::FindPath", "function OpexAyStarV129::_CleanPath"),
                            ("function OpexBinaryHeapV129::Insert", "function OpexBinaryHeapV129::Peek"),
                            ("function _Cost(", "function _Neighbours("),
                            ("function _Neighbours(", "function _TunnelsBridgesInto(")):
            body = _body(self.v129, marker, end)
            self.assertNotIn("V129_RAIL_ASTAR", body)

    def test_heap_parallel_arrays_same_comparisons(self):
        self.assertIn("priority <= prios[hole / 2]", self.v129)
        self.assertIn("prios[child] <= prios[child - 1]", self.v129)
        self.assertIn("if (childPrio > tmpPrio) break;", self.v129)
        self.assertNotIn("[item, priority]", self.v129)

    def test_cost_uses_locals_not_getparent(self):
        cost = _body(self.v129, "function _Cost(", "function _Neighbours(")
        self.assertNotIn("GetParent()", cost)
        self.assertIn("local par = path._prev;", cost)

    def test_neighbours_single_pass(self):
        nb = _body(self.v129, "function _Neighbours(", "function _TunnelsBridgesInto(")
        self.assertIn("self._dirIdx", nb)
        self.assertNotIn("local bridges", nb)
        self.assertNotIn("self._GetTunnelsBridges(", nb)
        self.assertIn("_TunnelsBridgesInto(par_tile, cur_node, gp._tile, tiles)", nb)

    def test_estimate_cache_and_direction_independence(self):
        # l'estimation V90 ne lit jamais cur_direction : precondition du cache par tuile
        rail = _read("ai/OpexAI/pathfinder_v90/rail.nut")
        for fn, nxt in (("function OpexRailPathFinderV90::_Estimate(", "function OpexRailPathFinderV90::_EstimateWeighted("),
                        ("function OpexRailPathFinderV90::_EstimateWeighted(", "function OpexRailPathFinderV90::_Neighbours(")):
            self.assertNotIn("cur_direction", _body(rail, fn, nxt).split("{", 1)[1])
        self.assertEqual(self.v129.count("if (cur_tile in cache) return cache[cur_tile];"), 2)
        # remise a zero a l'initialisation et au changement de poids
        self.assertGreaterEqual(self.v129.count("this._estCache = {};"), 2)

    def test_bridge_table_rebuilt_not_cached(self):
        # cache global retire (divergence mesuree) : table reconstruite a chaque recherche, comme V90
        self.assertNotIn("V129_BRIDGE_TABLE_CACHE", self.v129)
        self.assertIn("AIBridgeList_Length(i + 1)", self.v129)
        self.assertIn("bridge_table_diff", self.v129)

    def test_consumed_iteration_contract(self):
        self.assertIn("this._consumed = (pops == 0) ? 1 : pops;", self.v129)
        self.assertEqual(self.v129.count("this._consumed = pops;"), 2)
        self.assertIn("function LastConsumed()", self.v129)

    def test_goal_set_shortcut(self):
        self.assertIn("if (cur_tile in goalSet) {", self.v129)

    def test_checker_logs_and_compares_priority(self):
        self.assertIn('OpexC56TaskLog("V129_CHECK", "step_diff"', self.v129)
        self.assertIn('OpexC56TaskLog("V129_CHECK", "finish"', self.v129)
        self.assertIn("o129.PeekPriority()", self.v129)
        self.assertIn("if (V129_RAIL_ASTAR_CHECK) return OpexRailPathfinderCheckerV129();", self.v129)

    def test_frontier_uses_parallel_arrays_only_under_flag(self):
        src = _read("ai/OpexAI/builder_rail.nut")
        self.assertIn("open._prios[candidates[0]] : open._queue[candidates[0]][1]", src)
        self.assertIn("open._items[heapIndex] : open._queue[heapIndex][0]", src)


class TestV129SearchOps(unittest.TestCase):
    def test_search_ops_field_in_rail_attempt(self):
        src = _read("ai/OpexAI/task_rail.nut")
        self.assertIn('" search_ops=" + (("searchOps" in candidate) ? candidate.searchOps : -1)', src)
        self.assertLess(src.index('" ops=" + result.opcodes'), src.index('" search_ops="'))

    def test_accumulation_only_under_decision_log(self):
        task = _read("ai/OpexAI/task_rail.nut")
        self.assertIn("if (DECISION_LOG && state.candidate != null) OpexAddRailSearchOps(state.candidate, searchSliceOps);", task)
        builder = _read("ai/OpexAI/builder_rail.nut")
        self.assertIn("if (DECISION_LOG) OpexAddRailSearchOps(candidate, searchOps);", builder)
        self.assertEqual(len(re.findall(r"OpexAddRailSearchOps\(", builder + task)), 3)


if __name__ == "__main__":
    unittest.main()
