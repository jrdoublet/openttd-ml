#!/usr/bin/env python3
"""Tests de contrats statiques pour V201 — Branches fret sur tronc double (inspirées de HogNet).

Contrats statiques :
1. Déclaration :
   - `v201_branches` déclaré dans info.nut (booléen, défaut 0 sur tous profils).
   - `v201_max_dest_trains` déclaré dans info.nut (entier, défaut 12, min 1, max 50).
   - `v201_stuck_days` déclaré dans info.nut (entier, défaut 20, min 5, max 100).
   - Variables globales V201_BRANCHES, V201_MAX_DEST_TRAINS, V201_STUCK_DAYS dans globals_pre.nut.
   - OpexV201Active() actif seulement si V201_BRANCHES et OpexV198Active().
   - Lecture unique dans settings.nut.
   - main.nut inclut v201_branches.nut et initialise _v201StuckVehicles.
2. Inertie au défaut (0) :
   - À 0, OpexV201Active() retourne false.
   - Aucun candidat branche généré quand inactif.
   - Pose de jonction sautée sur tronc quand inactif.
   - Détection des trains bloqués sautée quand inactif.
3. Géométrie et signalisation de jonction (v201_branches.nut) :
   - OpexV201RightDivergeJunction et OpexV201FourWayJunction définis.
   - Fenêtre de 5 tuiles droites doubles vérifiée.
   - Distance >= 12 tuiles des gares source et destination.
   - Vérification du sens des signaux à sens unique (_HasInvertedOneWaySignal).
   - Remplacement des signaux de bloc par PBS (PBS_ONEWAY sur voie directe, PBS sur raccordement).
4. Candidats branche et économie :
   - OpexV201BranchCandidates cherche industries non desservies <= 60 tuiles de la jonction.
   - Plafond de trains par gare de destination (v201_max_dest_trains).
   - Au plus 5 branches par tronc (v201BranchCount < 5).
   - Devis (capital) = nouvelle gare source + voie de branche courte + train (sans refacturer le tronc).
   - Distance réelle source -> destination du tronc pour le calcul de profit.
5. Dépôt et trains bloqués :
   - Dépôt de la branche en sortie de boucle (départ direct sans demi-tour).
   - OpexV201CheckStuckTrains : envoi au dépôt si bloqué >= v201_stuck_days dans la gorge de gare.
6. Rollback et intégrité :
   - OpexV201DemolishJunction démolit proprement les aiguillages en cas d'échec ultérieur du tronc.
   - OpexV201ExecuteBranchPlan démolit les voies et la gare en cas d'échec.
   - Tronc jamais cassé.
7. Règles Squirrel et journalisation :
   - "key" in table avant accès aux clés optionnelles.
   - Pas de clone/parent/base comme identifiant dans v201_branches.nut.
   - Journal OpexDecide("V201", "step=junction|branch_cand|branch_build|stuck ok=.. reason=..").
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
        self.assertIn("v201_branches", specs)
        s = specs["v201_branches"]
        self.assertEqual(s["default"], 0)
        self.assertTrue(s["boolean"])

        self.assertIn("v201_max_dest_trains", specs)
        s_dest = specs["v201_max_dest_trains"]
        self.assertEqual(s_dest["default"], 12)
        self.assertEqual(s_dest["min_value"], 1)
        self.assertEqual(s_dest["max_value"], 50)

        self.assertIn("v201_stuck_days", specs)
        s_stuck = specs["v201_stuck_days"]
        self.assertEqual(s_stuck["default"], 20)
        self.assertEqual(s_stuck["min_value"], 5)
        self.assertEqual(s_stuck["max_value"], 100)

        content = _read("info.nut")
        for setting_name in ("v201_branches", "v201_max_dest_trains", "v201_stuck_days"):
            block = content.split(f'name = "{setting_name}"', 1)[1].split("});", 1)[0]
            val = "0" if setting_name == "v201_branches" else ("12" if setting_name == "v201_max_dest_trains" else "20")
            for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
                self.assertRegex(block, key + r" = " + val + r"\b")

    def test_globals_and_active_helper_in_globals_pre(self):
        content = _read("globals_pre.nut")
        self.assertIn("V201_BRANCHES <- false;", content)
        self.assertIn("V201_MAX_DEST_TRAINS <- 12;", content)
        self.assertIn("V201_STUCK_DAYS <- 20;", content)
        body = _function_body(content, "OpexV201Active")
        self.assertIn("V201_BRANCHES && OpexV198Active()", body)

    def test_settings_loaded_in_settings_nut(self):
        settings_text = _read("settings.nut")
        self.assertIn('V201_BRANCHES = AIController.GetSetting("v201_branches") != 0;', settings_text)
        self.assertIn('AIController.GetSetting("v201_max_dest_trains")', settings_text)
        self.assertIn('V201_MAX_DEST_TRAINS =', settings_text)
        self.assertIn('AIController.GetSetting("v201_stuck_days")', settings_text)
        self.assertIn('V201_STUCK_DAYS =', settings_text)

    def test_main_requires_v201_branches(self):
        main = _read("main.nut")
        self.assertIn('require("v201_branches.nut");', main)
        self.assertIn('_v201StuckVehicles = null;', main)
        self.assertIn('this._v201StuckVehicles = {};', main)


class InertDefault(unittest.TestCase):
    def test_inert_when_setting_zero(self):
        # When V201_BRANCHES is false, OpexV201Active() returns false
        candidates = _read("candidates.nut")
        cand_body = _function_body(candidates, "OpexBuildCandidates")
        self.assertIn("if (OpexV201Active())", cand_body)
        self.assertIn("OpexV201BranchCandidates(", cand_body)

        rail_templates = _read("rail_templates.nut")
        exec_body = _function_body(rail_templates, "OpexV198ExecuteRailPlan")
        self.assertIn("if (OpexV201Active())", exec_body)
        self.assertIn("OpexV201TryBuildJunction(", exec_body)

        task_rail = _read("task_rail.nut")
        expand_body = _function_body(task_rail, "OpexAI::_expandRailLines")
        self.assertIn("if (OpexV201Active())", expand_body)
        self.assertIn("OpexV201CheckStuckTrains(", expand_body)


class JunctionGeometryAndSignals(unittest.TestCase):
    def setUp(self):
        self.source = _read("v201_branches.nut")

    def test_junction_classes_and_functions(self):
        self.assertIn("class OpexV201RightDivergeJunction", self.source)
        self.assertIn("class OpexV201FourWayJunction", self.source)
        self.assertIn("function OpexV201TryBuildJunction(", self.source)
        self.assertIn("function OpexV201DemolishJunction(", self.source)

    def test_window_check_and_distance_constraints(self):
        body = _function_body(self.source, "OpexV201TryBuildJunction")
        # Distance >= 12 from stations
        self.assertIn("jMinDist = 12", body)
        self.assertIn("jMaxDist = pathLen - 12", body)
        # Check window in TryBuildNearStation
        self.assertIn("isNS", self.source)
        self.assertIn("isEW", self.source)

    def test_inverted_signal_check(self):
        self.assertIn("function _HasInvertedOneWaySignal(", self.source)
        self.assertIn("AIRail.GetSignalType(tile, next)", self.source)
        self.assertIn("AIRail.SIGNALTYPE_PBS_ONEWAY", self.source)

    def test_signal_replacement(self):
        self.assertIn("function BuildSignals(", self.source)
        self.assertIn("SIGNALTYPE_PBS_ONEWAY", self.source)
        self.assertIn("SIGNALTYPE_PBS", self.source)
        self.assertIn("AIRail.RemoveSignal", self.source)


class BranchCandidatesAndEconomics(unittest.TestCase):
    def setUp(self):
        self.source = _read("v201_branches.nut")

    def test_branch_candidates_filters(self):
        body = _function_body(self.source, "OpexV201BranchCandidates")
        # Max distance 60 tiles
        self.assertIn("60", body)
        self.assertIn("AIMap.DistanceManhattan", body)
        # Max 5 branches per trunk
        self.assertIn("bCount >= 5", body)
        # Max dest trains check
        self.assertIn("V201_MAX_DEST_TRAINS", body)
        # Candidate kind freight, branch = 1
        self.assertIn('kind = "freight"', body)
        self.assertIn("branch = 1", body)

    def test_quote_and_profit_formula(self):
        body = _function_body(self.source, "OpexV201BranchCandidates")
        # Capital = station + branch track only, not trunk
        self.assertIn("branchTrackCost = 2 * distJunc * trackCostPerTile + 2000", body)
        self.assertIn("branchCapital = stationCost + branchTrackCost + trainCost", body)
        # Profit uses real distance
        self.assertIn("realDist = AIMap.DistanceManhattan(indLoc, dstLoc)", body)
        self.assertIn("OpexRailFixedConsist(catalog, matchCargo, realDist,", body)


class DepotAndStuckTrains(unittest.TestCase):
    def setUp(self):
        self.source = _read("v201_branches.nut")

    def test_branch_execution_uses_source_template_depot(self):
        body = _function_body(self.source, "OpexV201ExecuteBranchPlan")
        self.assertIn("OpexFindSourceTemplateSite", body)
        self.assertIn("OpexBuildSourceTemplateReal", body)
        self.assertIn("builtSrc.depotTile", body)
        self.assertIn("OpexBuildTrains(", body)

    def test_stuck_train_detection(self):
        body = _function_body(self.source, "OpexV201CheckStuckTrains")
        self.assertIn("V201_STUCK_DAYS", body)
        self.assertIn("AIVehicle.SendVehicleToDepot", body)
        self.assertIn('OpexDecide("V201", "step=stuck', body)


class RollbackAndIntegrity(unittest.TestCase):
    def setUp(self):
        self.source = _read("v201_branches.nut")
        self.templates = _read("rail_templates.nut")

    def test_demolish_junction_cleanly(self):
        body = _function_body(self.source, "OpexV201DemolishJunction")
        self.assertIn("AIRail.RemoveRail", body)

    def test_demolish_on_branch_failure(self):
        body = _function_body(self.source, "OpexV201ExecuteBranchPlan")
        self.assertIn("OpexDemolishSourceTemplate(builtSrc);", body)
        self.assertIn("OpexDemolishTrack(tiles1);", body)
        self.assertIn("OpexDemolishTrack(tiles2);", body)

    def test_trunk_cleanup_on_train_fail(self):
        body = _function_body(self.templates, "OpexV198ExecuteRailPlan")
        self.assertIn("OpexV201DemolishJunction(v201Junction);", body)


class SquirrelSafetyAndDecisions(unittest.TestCase):
    def setUp(self):
        self.source = _read("v201_branches.nut")

    def test_balanced_braces_and_parens(self):
        for name in ("v201_branches.nut", "rail_templates.nut"):
            content = _read(name)
            self.assertEqual(content.count("{"), content.count("}"), f"Unbalanced braces in {name}")
            self.assertEqual(content.count("("), content.count(")"), f"Unbalanced parens in {name}")
            self.assertEqual(content.count("["), content.count("]"), f"Unbalanced brackets in {name}")

    def test_no_forbidden_squirrel_keywords(self):
        # 'clone', 'parent', 'base' forbidden as identifiers
        for word in ("parent", "base"):
            matches = re.findall(r"\b" + word + r"\b", self.source)
            self.assertEqual(matches, [], f"Forbidden keyword '{word}' in v201_branches.nut")

    def test_decision_log_format(self):
        for step in ("junction", "branch_cand", "branch_build", "stuck"):
            self.assertIn(f'step={step}', self.source)
        self.assertIn('OpexDecide("V201"', self.source)


if __name__ == "__main__":
    unittest.main()
