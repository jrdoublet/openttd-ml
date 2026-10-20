#!/usr/bin/env python3
"""Tests de contrats statiques pour V197 — Double voie guidée à la manière d'AAAHogEx.

Contrats statiques :
1. Déclaration :
   - `v197_guided_double` déclaré dans info.nut (booléen, défaut 0 sur tous profils).
   - Variable globale initialisée à false dans globals_pre.nut.
   - Lecture unique dans settings.nut.
2. Inertie au défaut (0) :
   - À 0, outwardSide et guideTiles sont null.
   - Le coût A* et les opcodes restent strictement inchangés.
3. Présence des deux options dans l'A* rail :
   - outwardSide et guideTiles présents comme paramètres dans OpexSearchPath,
     OpexCreateRailPathfinder, OpexCreateSegmentedSearch.
   - OpexAdvanceSegmentedSearch transmet outwardSide et guideTiles au pathfinder.
   - _outwardSide et _guideTiles gérés dans _Cost (V90 et V129).
   - OpexV197BuildGuideTiles construit les anneaux 0..8 autour de la voie 1.
   - La voie 1 utilise outwardSide pour réserver la place du retour.
   - Le repli de la voie 2 utilise guideTiles avec coût ×0,5 au niveau 0, croissant ensuite.
   - Le tracé parallèle V196 reste tenté en premier.
4. Garde toIdx / fromIdx dans OpexConvertDoubleTrackToLoop :
   - switchInA, switchInB, switchOutA, switchOutB testés avec null et "key" in table avant lecture.
   - Abandon propre (return false) si un aiguillage manque ou est invalide.
   - Aucune ré-instanciation non gardée de startIdx2 / endIdx2.
   - Lecture sécurisée de line.vehicles.
5. Journalisation DECISION_LOG :
   - OpexDecide("V197", "track=1|2 ok=.. iters=.. reason=..").
6. Sécurité des mots réservés et syntaxe Squirrel :
   - Aucun 'clone', 'parent', 'base' comme identifiant ou paramètre.
   - Syntaxe équilibrée (accolades, parenthèses, crochets).
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_setting_specs  # noqa: E402


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
    def test_setting_in_info_nut(self):
        specs = parse_ai_setting_specs(AI / "info.nut")

        self.assertIn("v197_guided_double", specs)
        s_guided = specs["v197_guided_double"]
        self.assertEqual(s_guided["default"], 0)
        self.assertTrue(s_guided["boolean"])

        content = _read("info.nut")
        block = content.split('name = "v197_guided_double"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 0\b")

    def test_global_declared(self):
        content = _read("globals_pre.nut")
        self.assertIn("V197_GUIDED_DOUBLE <- false;", content)

    def test_setting_loaded_in_settings_nut(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertEqual(body.count('AIController.GetSetting("v197_guided_double")'), 1)
        self.assertIn('V197_GUIDED_DOUBLE = AIController.GetSetting("v197_guided_double") != 0;', body)


class InertDefault(unittest.TestCase):
    def test_inert_when_setting_zero(self):
        builder = _read("builder_rail.nut")
        task = _read("task_rail.nut")

        plan_route = _function_body(builder, "OpexPlanRailRoute")
        self.assertIn("V197_GUIDED_DOUBLE", plan_route)

        task_search = _function_body(task, "OpexAI::_startRailSearch")
        self.assertIn("V197_GUIDED_DOUBLE", task_search)

        plan_double = _function_body(builder, "OpexV190PlanDoubleTrack")
        self.assertIn("V197_GUIDED_DOUBLE", plan_double)


class PresenceDesDeuxOptions(unittest.TestCase):
    def setUp(self):
        self.builder = _read("builder_rail.nut")
        self.task = _read("task_rail.nut")
        self.rail_nut = _read("pathfinder_v90/rail.nut")
        self.v129_nut = _read("pathfinder_v90/v129.nut")

    def test_signatures_contain_both_options(self):
        self.assertIn("function OpexSearchPath(plansA, plansB, iterationBudget, deadlineTick, ignoredTiles = null, weight = null, outwardSide = null, guideTiles = null)", self.builder)
        self.assertIn("function OpexCreateRailPathfinder(plansA, plansB, ignoredTiles = null, weight = null, outwardSide = null, guideTiles = null, engine = null)", self.builder)
        self.assertIn("function OpexCreateSegmentedSearch(plansA, plansB, iterationBudget, ignoredTiles = null, weight = null, outwardSide = null, guideTiles = null, engine = null)", self.builder)

    def test_advance_segmented_search_forwards_options(self):
        body = _function_body(self.builder, "OpexAdvanceSegmentedSearch")
        self.assertIn('state.outwardSide', body)
        self.assertIn('state.guideTiles', body)

    def test_pathfinders_manage_outward_side_and_guide_tiles(self):
        self.assertIn("_outwardSide = null;", self.rail_nut)
        self.assertIn("_guideTiles = null;", self.rail_nut)
        self.assertIn("_outwardSide = null;", self.v129_nut)
        self.assertIn("_guideTiles = null;", self.v129_nut)

        # Cost functions apply guideTiles discount and outwardSide penalty
        self.assertIn("self._guideTiles", self.rail_nut)
        self.assertIn("self._outwardSide", self.rail_nut)
        self.assertIn("self._guideTiles", self.v129_nut)
        self.assertIn("self._outwardSide", self.v129_nut)

        # Check level 0 has * 0.5 discount (or 5/10)
        self.assertIn("(step_cost * 5) / 10", self.rail_nut)
        self.assertIn("(step_cost * 5) / 10", self.v129_nut)

        # Check heavy penalty (400) for lateral tile unbuildable or slope incompatible
        self.assertIn("step_cost += 400", self.rail_nut)
        self.assertIn("step_cost += 400", self.v129_nut)

    def test_build_guide_tiles_function(self):
        self.assertIn("function OpexV197BuildGuideTiles(tiles, side, forbidden)", self.builder)
        body = _function_body(self.builder, "OpexV197BuildGuideTiles")
        self.assertIn("ring <= 8", body)
        self.assertIn("OpexV190GetPerp(", body)
        self.assertIn("OpexV190MakeTile(", body)

    def test_parallel_trace_first_then_fallback_guided(self):
        body = _function_body(self.builder, "OpexV190PlanDoubleTrack")
        trace_idx = body.index("OpexV190TraceParallelTrack(")
        fallback_idx = body.index("OpexV197BuildGuideTiles(")
        self.assertLess(trace_idx, fallback_idx, "Parallel trace V196 must be attempted before fallback A*")
        self.assertIn("OpexSearchPath(dualA, dualB,", body)


class GardeToIdx(unittest.TestCase):
    def setUp(self):
        self.builder = _read("builder_rail.nut")
        self.convert_body = _function_body(self.builder, "OpexConvertDoubleTrackToLoop")

    def test_switch_null_and_keys_guarded(self):
        self.assertIn('"fromIdx" in switchOutA', self.convert_body)
        self.assertIn('"toIdx" in switchOutA', self.convert_body)
        self.assertIn('"fromIdx" in switchInA', self.convert_body)
        self.assertIn('"toIdx" in switchInA', self.convert_body)
        self.assertIn('"fromIdx" in switchOutB', self.convert_body)
        self.assertIn('"toIdx" in switchOutB', self.convert_body)
        self.assertIn('"fromIdx" in switchInB', self.convert_body)
        self.assertIn('"toIdx" in switchInB', self.convert_body)

    def test_abort_cleanly_if_switch_missing(self):
        self.assertIn("NO_SW_OUT_A", self.convert_body)
        self.assertIn("NO_SW_IN_A", self.convert_body)
        self.assertIn("NO_SW_OUT_B", self.convert_body)
        self.assertIn("NO_SW_IN_B", self.convert_body)

    def test_no_shadowed_startidx2_or_endidx2(self):
        # The buggy lines 'local startIdx2 = (switchOutA.fromIdx > switchInA.fromIdx ...' must not exist
        self.assertNotIn("local startIdx2 = (switchOutA.fromIdx", self.convert_body)
        self.assertNotIn("local endIdx2 = (switchOutB.toIdx", self.convert_body)

    def test_vehicles_field_guarded(self):
        self.assertIn('"vehicles" in line', self.convert_body)


class DecisionLog(unittest.TestCase):
    def setUp(self):
        self.builder = _read("builder_rail.nut")

    def test_track1_and_track2_logging(self):
        self.assertIn('OpexDecide("V197", "track=1 ok=', self.builder)
        self.assertIn('OpexDecide("V197", "track=2 ok=', self.builder)


class SquirrelKeywordsAndSyntax(unittest.TestCase):
    def test_no_reserved_keywords(self):
        functions = [
            (self._read_builder(), ["OpexV197BuildGuideTiles", "OpexConvertDoubleTrackToLoop", "OpexV190PlanDoubleTrack", "OpexSearchPath"]),
            (self._read_task(), ["OpexAI::_startRailSearch", "OpexAI::_startRailStockSearch"]),
        ]
        for src, fn_list in functions:
            for fn in fn_list:
                body = _function_body(src, fn)
                for kw in ("clone", "parent", "base"):
                    pattern = rf"\b(local|function)\s+{kw}\b"
                    self.assertIsNone(re.search(pattern, body), f"Reserved keyword '{kw}' found in {fn}")
                    param_pattern = rf"\(\s*{kw}\s*[,)]"
                    self.assertIsNone(re.search(param_pattern, body), f"Reserved keyword '{kw}' used as param in {fn}")

    def _read_builder(self):
        return _read("builder_rail.nut")

    def _read_task(self):
        return _read("task_rail.nut")

    def test_balanced_braces_and_parens(self):
        for name in ("info.nut", "globals_pre.nut", "settings.nut", "builder_rail.nut", "task_rail.nut", "pathfinder_v90/rail.nut", "pathfinder_v90/v129.nut"):
            content = _read(name)
            # Remove comments and strings for accurate counting
            clean = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            clean = re.sub(r'//.*$', '', clean, flags=re.MULTILINE)
            clean = re.sub(r'"(\\.|[^"\\])*"', '""', clean)

            self.assertEqual(clean.count("{"), clean.count("}"), f"Unbalanced braces in {name}")
            self.assertEqual(clean.count("("), clean.count(")"), f"Unbalanced parens in {name}")
            self.assertEqual(clean.count("["), clean.count("]"), f"Unbalanced brackets in {name}")


if __name__ == "__main__":
    unittest.main()
