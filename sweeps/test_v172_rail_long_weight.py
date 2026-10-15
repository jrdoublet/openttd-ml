#!/usr/bin/env python3
"""Tests pour V172 — poids heuristique A* rail adaptatif a la distance.

Contexte : AAAHogEx utilise un poids heuristique A* de 2,0 (_estimate_rate = 2),
OpexAI 1,2 (V91_ASTAR_WEIGHT_PCT = 120). Sur les liaisons longues (>140 tuiles),
les recherches A* s'epuisent en ABND.

V172 introduit :
- v172_rail_long_weight_pct (0..300, defaut 200 depuis le 16/10 ; 0 = inerte)
- v172_rail_long_weight_dist (0..512, defaut 100)
Si v172_rail_long_weight_pct > 0 et distance Manhattan >= v172_rail_long_weight_dist,
le poids utilise vaut v172_rail_long_weight_pct au lieu de V91_ASTAR_WEIGHT_PCT.
S'applique a la voie principale ET a la seconde voie (upgrade double voie).
Consomme par V129 (pathfinder par defaut) et V90 via cost.astar_weight_pct / SetWeight.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_settings, parse_ai_setting_specs  # noqa: E402


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("unterminated " + name)


class Declaration(unittest.TestCase):
    def test_setting_pct(self):
        specs = parse_ai_setting_specs(AI / "info.nut")
        self.assertIn("v172_rail_long_weight_pct", specs)
        spec = specs["v172_rail_long_weight_pct"]
        self.assertEqual(spec["default"], 200)
        self.assertFalse(spec["boolean"])
        self.assertEqual((spec["min_value"], spec["max_value"]), (0, 300))
        block = _read("info.nut").split('name = "v172_rail_long_weight_pct"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 200\b")

    def test_setting_dist(self):
        specs = parse_ai_setting_specs(AI / "info.nut")
        self.assertIn("v172_rail_long_weight_dist", specs)
        spec = specs["v172_rail_long_weight_dist"]
        self.assertEqual(spec["default"], 100)
        self.assertFalse(spec["boolean"])
        self.assertEqual((spec["min_value"], spec["max_value"]), (0, 512))
        block = _read("info.nut").split('name = "v172_rail_long_weight_dist"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 100\b")

    def test_campaign_freeze_defaults(self):
        defaults = parse_ai_settings(AI / "info.nut")
        self.assertEqual(defaults["v172_rail_long_weight_pct"], 200)
        self.assertEqual(defaults["v172_rail_long_weight_dist"], 100)

    def test_globals_declared(self):
        globals_pre = _read("globals_pre.nut")
        self.assertIn("V172_RAIL_LONG_WEIGHT_PCT <- 200;", globals_pre)
        self.assertIn("V172_RAIL_LONG_WEIGHT_DIST <- 100;", globals_pre)

    def test_loaded_once_in_settings(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertEqual(body.count('AIController.GetSetting("v172_rail_long_weight_pct")'), 1)
        self.assertEqual(body.count('AIController.GetSetting("v172_rail_long_weight_dist")'), 1)
        self.assertIn("V172_RAIL_LONG_WEIGHT_PCT =", body)
        self.assertIn("V172_RAIL_LONG_WEIGHT_DIST =", body)


class WeightResolution(unittest.TestCase):
    def test_helper_defined_in_builder_rail(self):
        body = _function_body(_read("builder_rail.nut"), "OpexRailAstarWeight")
        self.assertIn("V172_RAIL_LONG_WEIGHT_PCT > 0", body)
        self.assertIn("dist >= V172_RAIL_LONG_WEIGHT_DIST", body)
        self.assertIn("return V172_RAIL_LONG_WEIGHT_PCT;", body)
        self.assertIn("return V91_ASTAR_WEIGHT_PCT;", body)
        self.assertIn("if (!V90_FAST_PATHFINDER) return 100;", body)

    def test_default_is_inert(self):
        # A defaut (V172_RAIL_LONG_WEIGHT_PCT == 0), la condition > 0 est fausse
        # et retombe sur V91_ASTAR_WEIGHT_PCT pour toute distance.
        body = _function_body(_read("builder_rail.nut"), "OpexRailAstarWeight")
        self.assertTrue("V172_RAIL_LONG_WEIGHT_PCT > 0" in body)


class ApplicationRailSearches(unittest.TestCase):
    def test_primary_rail_search_weight(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_startRailSearch")
        self.assertIn("local searchWeight = OpexRailAstarWeight(candidate.distance);", body)
        self.assertIn("candidate.searchWeight <- searchWeight;", body)
        self.assertIn("searchWeight", body)
        self.assertIn("weight = searchWeight", body)

    def test_upgrade_rail_search_weight(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_startRailUpgradeSearch")
        self.assertIn("local searchWeight = OpexRailAstarWeight(line.distance);", body)
        self.assertIn("line.searchWeight <- searchWeight;", body)
        self.assertIn("searchWeight", body)
        self.assertIn("weight = searchWeight", body)

    def test_stock_rail_search_weight(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_startRailStockSearch")
        self.assertIn("local searchWeight = OpexRailAstarWeight(candidate.distance);", body)
        self.assertIn("candidate.searchWeight <- searchWeight;", body)
        self.assertIn("weight = searchWeight", body)

    def test_segmented_search_applies_weight(self):
        create = _function_body(_read("builder_rail.nut"), "OpexCreateSegmentedSearch")
        self.assertIn("weight = weight", create)
        advance = _function_body(_read("builder_rail.nut"), "OpexAdvanceSegmentedSearch")
        self.assertIn("pathfinder.cost.astar_weight_pct = state.weight;", advance)

    def test_create_rail_pathfinder_applies_weight(self):
        body = _function_body(_read("builder_rail.nut"), "OpexCreateRailPathfinder")
        self.assertIn("pathfinder.cost.astar_weight_pct = weight;", body)


class ConsumedByV129AndV90(unittest.TestCase):
    def test_v129_cost_setter_forwards_weight(self):
        v129_src = _read("pathfinder_v90/v129.nut")
        self.assertIn("function SetWeight(weight)", v129_src)
        self.assertIn("this._weight = (weight >= 100) ? weight : 100;", v129_src)
        self.assertIn("this._EstimateWeighted", v129_src)

    def test_v129_estimate_weighted_uses_weight(self):
        v129_src = _read("pathfinder_v90/v129.nut")
        self.assertIn("(min_cost * self._weight) / 100", v129_src)

    def test_v90_cost_setter_handles_weight(self):
        rail_src = _read("pathfinder_v90/rail.nut")
        self.assertIn('case "astar_weight_pct":  this._main.SetWeight(val); break;', rail_src)
        self.assertIn("function OpexRailPathFinderV90::SetWeight(weight)", rail_src)

    def test_v129_instantiation_lines_preserved_for_contract(self):
        # Verifie que le contrat V129 strict (OpexNewRailPathfinderV129() sans args dans builder_rail)
        # est conserve intact pour test_v129_rail_astar_exact_opt.py
        src = _read("builder_rail.nut")
        self.assertEqual(src.count("pathfinder = OpexNewRailPathfinderV129();"), 2)


class Logging(unittest.TestCase):
    def test_rail_attempt_logs_weight(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_recordRailAttempt")
        self.assertIn('OpexDecide("RAIL_ATTEMPT"', body)
        self.assertIn('" weight="', body)

    def test_rail_search_end_logs_weight_used(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_continueRailSearch")
        self.assertIn('" weight=" + weightUsed', body)


class SquirrelSyntax(unittest.TestCase):
    @staticmethod
    def _strip_literals_and_comments(text: str) -> str:
        return re.sub(
            r'@"(?:""|[^"])*"|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/',
            lambda m: re.sub(r"[^\n]", " ", m.group()),
            text,
            flags=re.S,
        )

    @staticmethod
    def _balanced(text: str, open_ch: str, close_ch: str) -> bool:
        depth = 0
        for ch in text:
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth < 0:
                    return False
        return depth == 0

    def test_modified_nut_files_syntax(self):
        modified = ("info.nut", "globals_pre.nut", "settings.nut", "builder_rail.nut", "task_rail.nut")
        for filename in modified:
            code = self._strip_literals_and_comments(_read(filename))
            self.assertTrue(self._balanced(code, "{", "}"), f"{filename} balanced braces")
            self.assertTrue(self._balanced(code, "(", ")"), f"{filename} balanced parens")
            self.assertTrue(self._balanced(code, "[", "]"), f"{filename} balanced brackets")
            self.assertIsNone(re.search(r"\blocal\s+static\b", code), f"{filename} no local static")
            self.assertNotIn("in null", code, f"{filename} no in null")


if __name__ == "__main__":
    unittest.main()
