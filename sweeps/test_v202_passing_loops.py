#!/usr/bin/env python3
"""Tests de contrats statiques pour V202 — Voie unique avec évitements PBS pour 2-3 trains par ligne.

Contrats statiques :
1. Déclarations :
   - `v202_passing_loops` déclaré dans info.nut (booléen, défaut 0).
   - `v202_second_loop_dist` déclaré dans info.nut (entier, défaut 120, bornes 50..500).
   - Variables globales déclarées dans globals_pre.nut (V202_PASSING_LOOPS, V202_SECOND_LOOP_DIST, OpexV202Active).
   - Lecture dans settings.nut.
2. Inertie au défaut (0) :
   - À défaut 0, OpexV202Active() retourne false.
   - À défaut 0, aucun calcul ni appel V202 n'est effectué dans _expandRailLines (opcodes préservés).
3. Présence des fonctions et mécanismes V202 :
   - Recherche de fenêtre droite L+6 et voie d'évitement latérale L+4 (OpexV202FindPassingLoopWindow).
   - Pose réelle d'évitement (rails, 2 aiguillages, signaux PBS_ONEWAY, signaux PBS entrées de gares) (OpexV202BuildPassingLoop).
   - Démolition et restauration en cas d'échec (OpexV202RollbackPassingLoop).
   - Clonage de train avec ordres partagés (AIVehicle.CloneVehicle(depot, train, true)).
   - Mesure du coût réel par différence de solde bancaire (GetBankBalance).
   - Plafond de caisse : coût estimé (évitement + train) + OpexCashReserve().
   - Condition de déclenchement : fret, voie unique, âge >= 3 mois (90 jours), stock >= demi-rame OU départ plein.
   - Pas de réessai avant 1 an après échec (v202_next_retry).
   - Option 2e évitement + 3e train si ligne > v202_second_loop_dist.
   - Journalisation DECISION_LOG ("V202", "step=window|build|clone ok=..").
4. Sécurité Squirrel :
   - Aucun 'clone', 'parent', 'base' comme identifiant.
   - Clés de tables protégées par `"key" in table`.
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


class TestV202Declaration(unittest.TestCase):
    def test_settings_in_info_nut(self):
        specs = parse_ai_setting_specs(AI / "info.nut")

        self.assertIn("v202_passing_loops", specs)
        s_loop = specs["v202_passing_loops"]
        self.assertEqual(s_loop["default"], 0)
        self.assertTrue(s_loop["boolean"])

        self.assertIn("v202_second_loop_dist", specs)
        s_dist = specs["v202_second_loop_dist"]
        self.assertEqual(s_dist["default"], 120)
        self.assertFalse(s_dist["boolean"])
        self.assertEqual((s_dist["min_value"], s_dist["max_value"]), (50, 500))

        content = _read("info.nut")
        block_loop = content.split('name = "v202_passing_loops"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block_loop, key + r" = 0\b")

        block_dist = content.split('name = "v202_second_loop_dist"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block_dist, key + r" = 120\b")

    def test_globals_declared(self):
        content = _read("globals_pre.nut")
        self.assertIn("V202_PASSING_LOOPS <- false;", content)
        self.assertIn("V202_SECOND_LOOP_DIST <- 120;", content)
        self.assertIn("function OpexV202Active()", content)

    def test_settings_loaded_in_settings_nut(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertEqual(body.count('AIController.GetSetting("v202_passing_loops")'), 1)
        self.assertEqual(body.count('AIController.GetSetting("v202_second_loop_dist")'), 1)
        self.assertIn('V202_PASSING_LOOPS = AIController.GetSetting("v202_passing_loops") != 0;', body)
        self.assertIn('local v202Dist = AIController.GetSetting("v202_second_loop_dist");', body)
        self.assertIn('V202_SECOND_LOOP_DIST = (v202Dist != null && v202Dist >= 50 && v202Dist <= 500) ? v202Dist : 120;', body)


class TestV202InertDefault(unittest.TestCase):
    def test_active_guard_returns_false_by_default(self):
        body = _function_body(_read("globals_pre.nut"), "OpexV202Active")
        self.assertIn("return V202_PASSING_LOOPS;", body)

    def test_expand_rail_lines_guards_v202(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_expandRailLines")
        self.assertIn("OpexV202Active()", body)
        self.assertIn("this.OpexV202TryPassingLoop(line, year, false)", body)
        self.assertIn("this.OpexV202TryPassingLoop(line, year, true)", body)


class TestV202Mechanisms(unittest.TestCase):
    def setUp(self):
        self.builder = _read("builder_rail.nut")
        self.task = _read("task_rail.nut")

    def test_find_window_function_present(self):
        self.assertIn("function OpexV202FindPassingLoopWindow(tiles, trainLength, minIdx, maxIdx, forbiddenSpans = null)", self.builder)
        body = _function_body(self.builder, "OpexV202FindPassingLoopWindow")
        # Straight window L+6
        self.assertIn("local W = L + 6;", body)
        # Lateral L+4
        self.assertIn("for (local k = 1; k <= L + 4; k++)", body)
        # Check flat slope
        self.assertIn("AITile.GetSlope(tk) != AITile.SLOPE_FLAT", body)
        self.assertIn("AITile.GetSlope(pk) != AITile.SLOPE_FLAT", body)
        # Check buildable
        self.assertIn("AITile.IsBuildable(pk)", body)
        # Check under AITestMode
        self.assertIn("local testMode = AITestMode();", body)
        self.assertIn("OpexV181TryBuildSwitch", body)

    def test_build_passing_loop_function_present(self):
        self.assertIn("function OpexV202BuildPassingLoop(line, tiles, window, catalog, cashReserve)", self.builder)
        body = _function_body(self.builder, "OpexV202BuildPassingLoop")
        # 2 switches
        self.assertIn("OpexV181TryBuildSwitch", body)
        # One-way signals on loop branches
        self.assertIn("OpexV181BuildOneWaySignal", body)
        # PBS signals at station entrances
        self.assertIn("SIGNALTYPE_PBS", body)
        # Rollback on failure
        self.assertIn("OpexV202RollbackPassingLoop", body)

    def test_rollback_function_present(self):
        self.assertIn("function OpexV202RollbackPassingLoop(placedTracks, placedSignals, placedLateralTiles, tiles, window)", self.builder)
        body = _function_body(self.builder, "OpexV202RollbackPassingLoop")
        self.assertIn("AIRail.RemoveSignal", body)
        self.assertIn("AIRail.RemoveRail", body)
        self.assertIn("AITile.DemolishTile", body)
        self.assertIn("AIRail.AreTilesConnected", body)

    def test_try_passing_loop_present(self):
        self.assertIn("function OpexAI::OpexV202TryPassingLoop(line, year, isSecondLoop = false)", self.task)
        body = _function_body(self.task, "OpexAI::OpexV202TryPassingLoop")
        # Age check >= 3 months (90 days)
        self.assertIn("ageDays < 90", body)
        # Stock half or depart full
        self.assertIn("stockHalf", body)
        self.assertIn("departFull", body)
        # Cost check with OpexCashReserve
        self.assertIn("OpexCashReserve()", body)
        # Real cost measured by bank balance difference
        self.assertIn("local cashBefore = AICompany.GetBankBalance(AICompany.COMPANY_SELF);", body)
        self.assertIn("local cashAfter = AICompany.GetBankBalance(AICompany.COMPANY_SELF);", body)
        self.assertIn("local realCost = cashBefore - cashAfter;", body)
        # Shared orders clone
        self.assertIn("AIVehicle.CloneVehicle(targetDepot, modelTrain, true)", body)
        # StartStopVehicle
        self.assertIn("AIVehicle.StartStopVehicle(extraTrain)", body)
        # Retry cooldown 365 days / 1 year
        self.assertIn("v202_next_retry <- AIDate.GetCurrentDate() + 365", body)
        # 2nd loop check on V202_SECOND_LOOP_DIST
        self.assertIn("V202_SECOND_LOOP_DIST", body)
        # Decision logs
        self.assertIn('OpexDecide("V202"', body)


class TestV202SquirrelSafety(unittest.TestCase):
    def test_no_forbidden_identifiers(self):
        builder = _read("builder_rail.nut")
        task = _read("task_rail.nut")
        v202_sources = [
            _function_body(builder, "OpexV202FindPassingLoopWindow"),
            _function_body(builder, "OpexV202BuildPassingLoop"),
            _function_body(builder, "OpexV202RollbackPassingLoop"),
            _function_body(task, "OpexAI::OpexV202TryPassingLoop"),
        ]
        for src in v202_sources:
            matches = re.findall(r'\b(?:local|function)\s+(clone|parent|base)\b', src)
            self.assertEqual(matches, [], f"Forbidden keyword in V202 function: {matches}")

    def test_table_access_protected(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::OpexV202TryPassingLoop")
        for key in ("mode", "kind", "scrapping", "wagons", "loco", "doubleTrack", "buildDate", "v202_next_retry", "lastWaitingA", "tiles", "distance", "v202_loops", "platformLength", "depot", "depot2"):
            self.assertIn(f'"{key}" in line', body, f'Missing guard for "{key}" in line')


if __name__ == "__main__":
    unittest.main()
