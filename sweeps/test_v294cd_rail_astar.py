#!/usr/bin/env python3
"""Contrats statiques V294c/d/f/i/j : paramètres A* ferroviaire alignés sur AAA.

Vérifie, sans lancer OpenTTD :
1. Déclaration de chaque réglage (défaut 0 sur les 4 niveaux, bornes exactes) ;
2. Lecture unique dans settings.nut vers les globales de globals_pre.nut ;
3. Gardes explicites `if (V294_... > 0)` autour de chaque nouveau chemin de code ;
4. Aucun global non déclaré dans globals_pre.nut ;
5. Absence totale de OpexDynamicHardCap et nettoyage des commentaires périmés.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read(rel: str) -> str:
    return (AI / rel).read_text(encoding="utf-8")


def function_body(source: str, name: str) -> str:
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:pos]
    raise AssertionError(f"Unclosed function: {name}")


class TestV294cRailWeightPct(unittest.TestCase):
    def test_setting_declared_default_zero(self):
        info = read("info.nut")
        match = re.search(r'AddSetting\(\{\s*name\s*=\s*"v294_rail_weight_pct"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(match, "v294_rail_weight_pct non déclaré dans info.nut")
        block = match.group(1)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{level}_value\s*=\s*0\b")
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 400", block)

    def test_global_declared_and_loaded_once(self):
        globals_pre = read("globals_pre.nut")
        self.assertIn("V294_RAIL_WEIGHT_PCT <- 0;", globals_pre)
        settings = read("settings.nut")
        self.assertEqual(settings.count('GetSetting("v294_rail_weight_pct")'), 1)
        self.assertIn("V294_RAIL_WEIGHT_PCT = railWeightPct;", settings)

    def test_guarded_in_builder_rail(self):
        body = function_body(read("builder_rail.nut"), "OpexRailAstarWeight")
        self.assertIn("if (V294_RAIL_WEIGHT_PCT > 0)", body)
        self.assertIn("return V294_RAIL_WEIGHT_PCT;", body)


class TestV294dRailAaaCosts(unittest.TestCase):
    def test_setting_declared_default_zero(self):
        info = read("info.nut")
        match = re.search(r'AddSetting\(\{\s*name\s*=\s*"v294_rail_aaa_costs"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(match, "v294_rail_aaa_costs non déclaré dans info.nut")
        block = match.group(1)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{level}_value\s*=\s*0\b")
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1", block)

    def test_global_declared_and_loaded_once(self):
        globals_pre = read("globals_pre.nut")
        self.assertIn("V294_RAIL_AAA_COSTS <- 0;", globals_pre)
        settings = read("settings.nut")
        self.assertEqual(settings.count('GetSetting("v294_rail_aaa_costs")'), 1)
        self.assertIn("V294_RAIL_AAA_COSTS = aaaCosts;", settings)

    def test_guarded_in_pathfinder_creation(self):
        builder = read("builder_rail.nut")
        create = function_body(builder, "OpexCreateRailPathfinder")
        self.assertIn("if (V294_RAIL_AAA_COSTS > 0)", create)
        self.assertIn("pathfinder.cost.diagonal_tile = 67;", create)
        self.assertIn("pathfinder.cost.bridge_per_tile = 100;", create)
        self.assertIn("pathfinder.cost.tunnel_per_tile = 0;", create)
        self.assertIn("pathfinder.cost.level_crossing = 900;", create)
        self.assertIn("pathfinder.cost.bridge_per_tile_ex = 200;", create)
        self.assertIn("pathfinder.cost.bridge_per_tile_ex2 = 400;", create)
        self.assertIn("pathfinder.cost.tunnel_per_tile_ex = 200;", create)
        self.assertIn("pathfinder.cost.tunnel_per_tile_ex2 = 300;", create)

        advance = function_body(builder, "OpexAdvanceSegmentedSearch")
        self.assertIn("if (V294_RAIL_AAA_COSTS > 0)", advance)

    def test_pathfinder_cost_fields_and_guards(self):
        rail = read("pathfinder_v90/rail.nut")
        self.assertIn("case \"level_crossing\":", rail)
        self.assertIn("case \"bridge_per_tile_ex\":", rail)
        self.assertIn("case \"tunnel_per_tile_ex\":", rail)
        cost_v90 = function_body(rail, "OpexRailPathFinderV90::_Cost")
        self.assertIn("if (self._cost_tunnel_per_tile_ex > 0 && distManhattan > 7)", cost_v90)
        self.assertIn("if (self._cost_bridge_per_tile_ex > 0 && distManhattan > 7)", cost_v90)
        self.assertIn("if (self._cost_level_crossing > 0 && AITile.HasTransportType(new_tile, AITile.TRANSPORT_ROAD))", cost_v90)

        v129 = read("pathfinder_v90/v129.nut")
        cost_v129 = function_body(v129, "_Cost")
        self.assertIn("if (self._cost_tunnel_per_tile_ex > 0 && distManhattan > 7)", cost_v129)
        self.assertIn("if (self._cost_bridge_per_tile_ex > 0 && distManhattan > 7)", cost_v129)
        self.assertIn("if (self._cost_level_crossing > 0 && AITile.HasTransportType(new_tile, AITile.TRANSPORT_ROAD))", cost_v129)


class TestV294fRailReverseProbe(unittest.TestCase):
    def test_setting_declared_default_zero(self):
        info = read("info.nut")
        match = re.search(r'AddSetting\(\{\s*name\s*=\s*"v294_rail_reverse_probe"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(match, "v294_rail_reverse_probe non déclaré dans info.nut")
        block = match.group(1)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{level}_value\s*=\s*0\b")
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 5000", block)

    def test_global_declared_and_loaded_once(self):
        globals_pre = read("globals_pre.nut")
        self.assertIn("V294_RAIL_REVERSE_PROBE <- 0;", globals_pre)
        settings = read("settings.nut")
        self.assertEqual(settings.count('GetSetting("v294_rail_reverse_probe")'), 1)
        self.assertIn("V294_RAIL_REVERSE_PROBE = revProbe;", settings)

    def test_guarded_in_start_rail_search(self):
        task_rail = read("task_rail.nut")
        start = function_body(task_rail, "OpexAI::_startRailSearch")
        self.assertIn("if (V294_RAIL_REVERSE_PROBE > 0)", start)
        self.assertIn("local revSlice = OpexV294fReverseProbe(plan.plansA, plan.plansB, clearanceTiles, searchWeight, candidate, V294_RAIL_REVERSE_PROBE);", start)

    def test_probe_helper_in_builder_rail(self):
        builder = read("builder_rail.nut")
        probe = function_body(builder, "OpexV294fReverseProbe")
        self.assertIn("local revPf = OpexCreateRailPathfinder(plansB, plansA, clearanceTiles, searchWeight, null, null);", probe)
        self.assertIn('OpexDecide("V294F_PROBE", "ok=" + (ok ? 1 : 0) + " iters=" + iters + " manh=" + manh);', probe)
        self.assertIn("local revTiles = OpexPathTiles(revRes);", probe)
        self.assertIn("revTiles.reverse();", probe)


class TestV294iRailDistDecouple(unittest.TestCase):
    def test_setting_declared_default_zero(self):
        info = read("info.nut")
        match = re.search(r'AddSetting\(\{\s*name\s*=\s*"v294_rail_dist_decouple"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(match, "v294_rail_dist_decouple non déclaré dans info.nut")
        block = match.group(1)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{level}_value\s*=\s*0\b")
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 500", block)

    def test_global_declared_and_loaded_once(self):
        globals_pre = read("globals_pre.nut")
        self.assertIn("V294_RAIL_DIST_DECOUPLE <- 0;", globals_pre)
        settings = read("settings.nut")
        self.assertEqual(settings.count('GetSetting("v294_rail_dist_decouple")'), 1)
        self.assertIn("V294_RAIL_DIST_DECOUPLE = distDecouple;", settings)

    def test_decouple_logic_in_candidates(self):
        cand = read("candidates.nut")
        refresh = function_body(cand, "OpexRefreshEpochBounds")
        self.assertIn("if (V294_RAIL_DIST_DECOUPLE > 0) railMax = V294_RAIL_DIST_DECOUPLE;", refresh)
        bounds = function_body(cand, "OpexCatalogBounds")
        self.assertIn("if (V294_RAIL_DIST_DECOUPLE > 0) railMax = V294_RAIL_DIST_DECOUPLE;", bounds)

    def test_opex_dynamic_hard_cap_absent_and_cleanups(self):
        for nut in ("builder_rail.nut", "task_rail.nut", "candidates.nut", "projects_builders.nut"):
            self.assertNotIn("OpexDynamicHardCap", read(nut))
        builder = read("projects_builders.nut")
        self.assertNotIn("HARD_ITERATION_CAP (10 000)", builder)
        self.assertIn("HARD_ITERATION_CAP (5 000)", builder)
        rail = read("builder_rail.nut")
        self.assertNotIn("15k", rail)
        self.assertNotIn("60k", rail)


if __name__ == "__main__":
    unittest.main()
