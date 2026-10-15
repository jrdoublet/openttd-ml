#!/usr/bin/env python3
"""Contrats statiques de V214 : couts de virage du A* rail a la AAAHogEx.

Verifie :
1. Reglages v214_rail_turn_cost (0..2000, defaut 300) et v214_rail_tight_turn_cost (0..5000,
   defaut 1500 ; 0 = historique), declares dans info.nut, globals_pre.nut et settings.nut.
2. OpexRailPathFinderV129 lit les reglages une fois par recherche, avant le premier _Cost, et
   ramene le coude serre a 100 sous 40 tuiles de trajet (regle AAA).
3. _Cost : a 0, le cout historique `_cost_turn` est inchange ; sinon seule la sortie de diagonale
   paie (regle AAA `dirs[1] != dirs[2]`), et le coude serre exige 4 pas unitaires.
4. La recherche segmentee fixe la distance du trajet complet ; V214_PATH journalise la geometrie
   des traces trouves (resumable), quel que soit le reglage.
5. La geometrie journalisee suit les memes regles que le cout (portage Python ci-dessous).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI_DIR = ROOT / "ai" / "OpexAI"


def read_file(rel_path: str) -> str:
    return (AI_DIR / rel_path).read_text(encoding="utf-8")


def function_body(source: str, name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\(", source)
    if not match:
        raise AssertionError(f"Function {name} not found")
    start = source.index("{", match.end())
    depth = 0
    for pos in range(start, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1:pos]
    raise AssertionError(f"Unclosed function {name}")


def v129_class_body() -> str:
    source = read_file("pathfinder_v90/v129.nut")
    start = source.index("class OpexRailPathFinderV129 extends OpexRailPathFinderV90")
    return source[start:]


class TestV214Settings(unittest.TestCase):
    def test_declared_with_bounds_and_qualified_defaults(self):
        info = read_file("info.nut")
        for name, bounds, default in (("v214_rail_turn_cost", "min_value = 0, max_value = 2000", 300),
                                      ("v214_rail_tight_turn_cost", "min_value = 0, max_value = 5000", 1500)):
            block = re.search(rf'name\s*=\s*"{name}"[^}}]+', info)
            self.assertIsNotNone(block, name)
            text = block.group(0)
            self.assertIn(bounds, text)
            for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
                self.assertRegex(text, rf"{key}\s*=\s*{default},")

    def test_globals_and_reading(self):
        globals_pre = read_file("globals_pre.nut")
        self.assertIn("V214_RAIL_TURN_COST <- 300;", globals_pre)
        self.assertIn("V214_RAIL_TIGHT_TURN_COST <- 1500;", globals_pre)
        settings = read_file("settings.nut")
        self.assertIn("V214_RAIL_TURN_COST = (v214Turn != null && v214Turn >= 0 && v214Turn <= 2000) ? v214Turn : 300;",
                      settings)
        self.assertIn("V214_RAIL_TIGHT_TURN_COST = (v214Tight != null && v214Tight >= 0 && v214Tight <= 5000) ? v214Tight : 1500;",
                      settings)


class TestV214Pathfinder(unittest.TestCase):
    def setUp(self):
        self.cls = v129_class_body()
        self.init = function_body(self.cls, "InitializePath")
        self.cost = function_body(self.cls, "_Cost")

    def test_members_declared(self):
        for member in ("_v214Turn = 0;", "_v214Tight = 0;", "_v214RouteDist = -1;"):
            self.assertIn(member, self.cls)

    def test_settings_read_before_first_cost(self):
        read = self.init.index("this._v214Turn = V214_RAIL_TURN_COST;")
        self.assertLess(self.init.index("this._v214Tight = V214_RAIL_TIGHT_TURN_COST;"),
                        self.init.index("foreach (node in sources) {\n\t\t\tlocal p0"))
        self.assertLess(read, self.init.index("local c1 = this._Cost(p0, node[0], 0xFF, this);"))

    def test_short_route_tight_cost_is_100(self):
        self.assertIn("if (this._v214RouteDist >= 0 && this._v214RouteDist < 40 && this._v214Tight > 100) this._v214Tight = 100;",
                      self.init)

    def test_historical_turn_cost_kept_at_zero(self):
        self.assertIn("if (self._v214Turn <= 0) {\n\t\t\t\t\t\t\tstep_cost += self._cost_turn;", self.cost)

    def test_exit_only_turn_rule(self):
        self.assertIn("} else if (prev_tile - par_tile != par_tile - gp._tile) {", self.cost)
        self.assertIn("step_cost += self._v214Turn;", self.cost)

    def test_tight_turn_rule(self):
        self.assertIn("if (self._v214Tight > 0 && gp != null) {", self.cost)
        self.assertIn("AIMap.DistanceManhattan(new_tile, ggp._tile) == 4", self.cost)
        self.assertIn("new_tile - prev_tile == prev_tile - par_tile", self.cost)
        self.assertIn("par_tile - gp._tile == gp._tile - ggp._tile", self.cost)
        self.assertIn("prev_tile - par_tile != par_tile - gp._tile", self.cost)
        self.assertIn("step_cost += self._v214Tight;", self.cost)

    def test_bridge_and_tunnel_turns_unchanged(self):
        # Les branches pont/tunnel gardent le cout historique.
        self.assertEqual(self.cost.count("step_cost += self._cost_turn;"), 4)


class TestV214Wiring(unittest.TestCase):
    def test_segmented_search_uses_full_route_distance(self):
        body = function_body(read_file("builder_rail.nut"), "OpexAdvanceSegmentedSearch")
        self.assertIn('if (V214_RAIL_TIGHT_TURN_COST > 0 && ("_v214RouteDist" in pathfinder)) {', body)
        self.assertIn("state.v214RouteDist <- OpexV214RouteDistance(state.activeSources, state.goals);", body)
        self.assertLess(body.index("pathfinder._v214RouteDist = state.v214RouteDist;"),
                        body.index("pathfinder.InitializePath(state.activeSources, state.goals, ignored);"))

    def test_path_geometry_logged_after_resumable_search(self):
        task = read_file("task_rail.nut")
        search = task.index('OpexDecide("RAIL_SEARCH", "type=resumable outcome=" + slice.stop')
        geo = task.index('OpexDecide("V214_PATH"')
        self.assertLess(search, geo)
        self.assertIn("local v214Tiles = OpexResolveSearchTiles(slice);", task)


def geometry(tiles, width=256):
    """Portage de OpexV214PathGeometry (tuile = y * largeur + x)."""
    def manh(a, b):
        return abs(a % width - b % width) + abs(a // width - b // width)
    steps = sum(1 for i in range(len(tiles) - 1) if manh(tiles[i], tiles[i + 1]) == 1)
    turns = exits = tight = 0
    for i in range(len(tiles) - 3):
        if manh(tiles[i], tiles[i + 3]) != 3:
            continue
        s0, s1, s2 = tiles[i + 1] - tiles[i], tiles[i + 2] - tiles[i + 1], tiles[i + 3] - tiles[i + 2]
        if s0 != s2:
            turns += 1
            if s1 != s0:
                exits += 1
        if i + 4 < len(tiles) and manh(tiles[i], tiles[i + 4]) == 4:
            s3 = tiles[i + 4] - tiles[i + 3]
            if s0 == s1 and s2 == s3 and s1 != s2:
                tight += 1
    return steps, turns, exits, tight


def walk(start, moves, width=256):
    tiles = [start]
    for m in moves:
        tiles.append(tiles[-1] + {"x": 1, "y": width}[m])
    return tiles


class TestV214GeometryRules(unittest.TestCase):
    def test_portage_matches_squirrel_source(self):
        body = function_body(read_file("builder_rail.nut"), "OpexV214PathGeometry")
        self.assertIn("if (s0 != s2) {", body)
        self.assertIn("if (s1 != s0) exits++;", body)
        self.assertIn("if (s0 == s1 && s2 == s3 && s1 != s2) tight++;", body)

    def test_straight_line(self):
        self.assertEqual(geometry(walk(1000, "xxxxxx")), (6, 0, 0, 0))

    def test_tight_corner(self):
        # droite, coin, droite perpendiculaire : une entree (gratuite chez AAA), une sortie, un coude serre
        self.assertEqual(geometry(walk(1000, "xxxyyy")), (6, 2, 1, 1))

    def test_long_diagonal_is_one_entry_one_exit(self):
        self.assertEqual(geometry(walk(1000, "xxx" + "yx" * 5 + "yyy")), (16, 2, 1, 0))


if __name__ == "__main__":
    unittest.main()
