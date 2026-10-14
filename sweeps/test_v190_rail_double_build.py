#!/usr/bin/env python3
"""Tests de contrats statiques pour V190 — Lignes rail fret posées en double voie à sens unique dès la construction, plusieurs trains par ligne.

Contrats statiques :
1. Declaration :
   - `v190_rail_double_build` declare dans info.nut (booleen, defaut 0).
   - `v190_rail_max_trains` declare dans info.nut (entier 2..8, defaut 4).
   - Variables globales initialisees dans globals_pre.nut.
   - Lecture unique dans settings.nut.
2. Inertie au defaut (0) :
   - A 0, infraCost et trains dans economy.nut conservent leur comportement historique.
   - A 0, OpexV190PlanDoubleTrack n'est pas appele.
   - A 0, le garde de recherche dans _expandRailLines reste intact.
3. Presence des etapes :
   - Recherche de quais paralleles (OpexV190FindParallelPlatformPlans).
   - A* seconde voie avec interdiction des tuiles de la premiere voie.
   - Raccordement en boucle avec aiguillages et signaux a sens unique (OpexConvertDoubleTrackToLoop).
   - Ordres partages pour les convois.
   - Fallback gracieux en voie unique si la seconde voie echoue (jamais de ligne cassee).
   - Capital candidat tenant compte de la 2e voie et 2 trains predits dans economy.nut.
   - Ajout de trains dans _expandRailLines jusqu'a v190_rail_max_trains (> 6 mois ou profit > 0, demi-rame ou plein).
   - Non-blocage par _railSearch != null lors du clonage V190.
   - Journalisation DECISION_LOG V190 (build_double, fallback_single, add_train).
4. Securite des mots reserves Squirrel :
   - Aucun 'clone', 'parent', 'base' comme identifiant ou parametre.
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
    def test_settings_in_info_nut(self):
        specs = parse_ai_setting_specs(AI / "info.nut")

        self.assertIn("v190_rail_double_build", specs)
        s_double = specs["v190_rail_double_build"]
        self.assertEqual(s_double["default"], 0)
        self.assertTrue(s_double["boolean"])

        self.assertIn("v190_rail_max_trains", specs)
        s_max = specs["v190_rail_max_trains"]
        self.assertEqual(s_max["default"], 4)
        self.assertFalse(s_max["boolean"])
        self.assertEqual((s_max["min_value"], s_max["max_value"]), (2, 8))

        content = _read("info.nut")
        block_double = content.split('name = "v190_rail_double_build"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block_double, key + r" = 0\b")

        block_max = content.split('name = "v190_rail_max_trains"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block_max, key + r" = 4\b")

    def test_globals_declared(self):
        content = _read("globals_pre.nut")
        self.assertIn("V190_RAIL_DOUBLE_BUILD <- false;", content)
        self.assertIn("V190_RAIL_MAX_TRAINS <- 4;", content)

    def test_settings_loaded_in_settings_nut(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertEqual(body.count('AIController.GetSetting("v190_rail_double_build")'), 1)
        self.assertEqual(body.count('AIController.GetSetting("v190_rail_max_trains")'), 1)
        self.assertIn('V190_RAIL_DOUBLE_BUILD = AIController.GetSetting("v190_rail_double_build") != 0;', body)
        self.assertIn('local v190Max = AIController.GetSetting("v190_rail_max_trains");', body)
        self.assertIn('V190_RAIL_MAX_TRAINS = (v190Max != null && v190Max >= 2 && v190Max <= 8) ? v190Max : 4;', body)


class InertDefault(unittest.TestCase):
    def test_economy_inert_at_default(self):
        econ_body = _function_body(_read("economy.nut"), "OpexLineEconomics")
        self.assertIn('if (V190_RAIL_DOUBLE_BUILD && kind == "freight")', econ_body)
        self.assertIn('local startTrains = (V190_RAIL_DOUBLE_BUILD && kind == "freight") ? 2 : 1;', econ_body)

    def test_builder_inert_at_default(self):
        complete_body = _function_body(_read("builder_rail.nut"), "OpexCompleteRailRouteAfterSearch")
        self.assertIn('if (V190_RAIL_DOUBLE_BUILD && candidate.kind == "freight")', complete_body)

    def test_expand_inert_at_default(self):
        expand_body = _function_body(_read("task_rail.nut"), "OpexAI::_expandRailLines")
        self.assertIn("!V190_RAIL_DOUBLE_BUILD", expand_body)
        self.assertIn("if (V181_RAIL_MAX_TRAINS <= 0)", expand_body)


class PresenceDesEtapes(unittest.TestCase):
    def setUp(self):
        self.builder = _read("builder_rail.nut")
        self.task = _read("task_rail.nut")
        self.econ = _read("economy.nut")

    def test_parallel_platforms_discovery(self):
        self.assertIn("function OpexV190FindParallelPlatformPlans(platform)", self.builder)
        find_body = _function_body(self.builder, "OpexV190FindParallelPlatformPlans")
        self.assertIn("local probe = AITestMode();", find_body)
        self.assertIn("AIRail.BuildRailStation(", find_body)

    def test_double_track_planning_forbids_first_track(self):
        self.assertIn("function OpexV190PlanDoubleTrack(", self.builder)
        plan_body = _function_body(self.builder, "OpexV190PlanDoubleTrack")
        self.assertIn("forbidden[tile] <- true;", plan_body)
        self.assertIn("OpexSearchPath(dualA, dualB,", plan_body)

    def test_crossovers_and_one_way_signals(self):
        exec_body = _function_body(self.builder, "OpexV190ExecuteRailPlan")
        self.assertIn("OpexConvertDoubleTrackToLoop(loopLine)", exec_body)

    def test_fallback_to_single_track_on_failure(self):
        exec_body = _function_body(self.builder, "OpexV190ExecuteRailPlan")
        self.assertIn("OpexRollback(tiles2, planA2, planB2, depot2, null);", exec_body)
        self.assertIn('reason=LOOPFAIL', exec_body)

    def test_candidate_capital_and_predicted_trains(self):
        econ_body = _function_body(self.econ, "OpexLineEconomics")
        self.assertIn("2 * travelDist * effectiveTrackCost + 4 * platformLength * catalog.costStation", econ_body)
        self.assertIn("local startTrains = (V190_RAIL_DOUBLE_BUILD && kind == " + '"freight") ? 2 : 1;', econ_body)

    def test_expand_rail_cloning_and_conditions(self):
        expand_body = _function_body(self.task, "OpexAI::_expandRailLines")
        self.assertIn("V190_RAIL_MAX_TRAINS", expand_body)
        self.assertIn("stockHalf = (waiting > (trainCapacity / 2));", expand_body)
        self.assertIn('departFull = (line.kind == "freight");', expand_body)
        self.assertIn("CloneVehicle(", expand_body)

    def test_expand_not_blocked_by_rail_search(self):
        expand_body = _function_body(self.task, "OpexAI::_expandRailLines")
        self.assertIn("!V190_RAIL_DOUBLE_BUILD", expand_body)

    def test_decision_log_format(self):
        builder_code = self.builder
        task_code = self.task
        self.assertIn('OpexDecide("V190", "action=build_double', builder_code)
        self.assertIn('OpexDecide("V190", "action=fallback_single', builder_code)
        self.assertIn('OpexDecide("V190", "action=add_train', task_code)


class SquirrelKeywordSafety(unittest.TestCase):
    def test_no_reserved_keywords(self):
        files_to_check = [
            ("builder_rail.nut", ["OpexV190FindParallelPlatformPlans", "OpexV190PlanDoubleTrack", "OpexExecuteRailPlan"]),
            ("task_rail.nut", ["OpexAI::_expandRailLines", "OpexAI::_recordRailAttempt"]),
            ("economy.nut", ["OpexLineEconomics"]),
        ]
        for filename, functions in files_to_check:
            content = _read(filename)
            for fn in functions:
                body = _function_body(content, fn)
                for kw in ("clone", "parent", "base"):
                    pattern = rf"\b(local|function)\s+{kw}\b"
                    self.assertIsNone(re.search(pattern, body), f"Reserved Squirrel keyword '{kw}' used as variable in {filename}::{fn}")
                    param_pattern = rf"\(\s*{kw}\s*[,)]"
                    self.assertIsNone(re.search(param_pattern, body), f"Reserved Squirrel keyword '{kw}' used as param in {filename}::{fn}")


if __name__ == "__main__":
    unittest.main()
