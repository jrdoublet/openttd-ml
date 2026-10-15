#!/usr/bin/env python3
"""Tests pour V184 — multi-creneaux de recherche A* rail (v184_rail_search_slots).

Contrats statiques :
1. Reglage `v184_rail_search_slots` declare (entier 1..4, defaut 1) dans info.nut.
2. Globale `V184_RAIL_SEARCH_SLOTS` initialisee a 1 dans globals_pre.nut.
3. Lu une seule fois dans OpexLoadSettings (settings.nut) avec bornes 1..4.
4. A N=1 (defaut), comportement historique strictement identique sans surcout.
5. A N>1, jusqu'a N recherches simultanees avec round-robin, garde MIN_SEPARATION,
   et verification de capital reserve couvrant tous les devis en cours plus le nouveau.
6. Journalisation `RAIL_SEARCH ... slot=k` sous DECISION_LOG quand N>1.
7. Sauvegarde/chargement : reinitialisation propre sans etat corrompu.
8. Aucun identifiant prohibe utilise.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path.cwd()
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
    def test_setting_declaration(self):
        spec = parse_ai_setting_specs(AI / "info.nut")["v184_rail_search_slots"]
        self.assertEqual(spec["default"], 1)
        self.assertFalse(spec["boolean"])
        self.assertEqual((spec["min_value"], spec["max_value"]), (1, 4))
        block = _read("info.nut").split('name = "v184_rail_search_slots"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 1\b")

    def test_global_declaration(self):
        self.assertIn("V184_RAIL_SEARCH_SLOTS <- 1;", _read("globals_pre.nut"))

    def test_settings_load_once_and_clamp(self):
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertEqual(body.count('AIController.GetSetting("v184_rail_search_slots")'), 1)
        self.assertIn("local railSlots = AIController.GetSetting(\"v184_rail_search_slots\");", body)
        self.assertIn("V184_RAIL_SEARCH_SLOTS = (railSlots != null && railSlots >= 1 && railSlots <= 4) ? railSlots : 1;", body)


class ClassMembersAndMethods(unittest.TestCase):
    def test_class_members_declared(self):
        main = _read("main.nut")
        self.assertIn("_v184RailSlots = null;", main)
        self.assertIn("_v184SlotCursor = 0;", main)

    def test_method_signatures_in_main(self):
        main = _read("main.nut")
        self.assertIn("function _v184InitRailSlots();", main)
        self.assertIn("function _v184CanStartRailSearch(candidate);", main)
        self.assertIn("function _v184FindFreeSlot();", main)
        self.assertIn("function _v184ActiveSearchCount();", main)
        self.assertIn("function _v184SelectNextSearchSlot();", main)
        self.assertIn("function _v184SyncRailSearch();", main)
        self.assertIn("function _v184FindSlotByPhase(targetPhase);", main)

    def test_init_in_start(self):
        body = _function_body(_read("main.nut"), "OpexAI::Start")
        self.assertIn("this._v184InitRailSlots();", body)


class SearchGuardAndMultiSlotLogic(unittest.TestCase):
    def setUp(self):
        self.rail = _read("task_rail.nut")
        self.projects = _read("task_projects.nut")
        self.scheduler = _read("scheduler.nut")

    def test_guard_uses_can_start_search_when_multi_slot(self):
        body = _function_body(self.rail, "OpexAI::_tryBuildRailProject")
        self.assertIn("local searchBlocked = (V184_RAIL_SEARCH_SLOTS > 1)", body)
        self.assertIn("? !this._v184CanStartRailSearch(candidate)", body)
        self.assertIn(": (this._railSearch != null);", body)

    def test_can_start_search_checks_min_separation(self):
        body = _function_body(self.rail, "OpexAI::_v184CanStartRailSearch")
        self.assertIn("MIN_SEPARATION", body)
        self.assertIn("local dSrcSrc = AIMap.DistanceManhattan(candidate.src, other.src);", body)
        self.assertIn("local dDstDst = AIMap.DistanceManhattan(candidate.dst, other.dst);", body)
        self.assertIn("dSrcSrc < MIN_SEPARATION || dDstDst < MIN_SEPARATION", body)

    def test_can_start_search_checks_capital_reserve(self):
        body = _function_body(self.rail, "OpexAI::_v184CanStartRailSearch")
        self.assertIn("OpexAvailableCapital() < totalNeed", body)

    def test_round_robin_advance_in_scheduler(self):
        body = _function_body(self.scheduler, "OpexAI::_advanceRailSearchSliceWithLedgers")
        self.assertIn("if (V184_RAIL_SEARCH_SLOTS > 1) {", body)
        self.assertIn("this._v184SelectNextSearchSlot();", body)
        self.assertIn("this._v184SyncRailSearch();", body)

    def test_multi_slot_consumption_loop_at_pass_start(self):
        body = _function_body(self.projects, "OpexAI::_tryBuildProjects")
        self.assertIn("if (V184_RAIL_SEARCH_SLOTS > 1) {", body)
        self.assertIn('local buildSlot = this._v184FindSlotByPhase("build");', body)
        self.assertIn("this._consumeResumableRailAtPassStart", body)

    def test_decision_log_slot_format(self):
        body = _function_body(self.rail, "OpexAI::_continueRailSearch")
        self.assertIn('local slotStr = (V184_RAIL_SEARCH_SLOTS > 1 && ("slotIndex" in state)) ? (" slot=" + state.slotIndex) : "";', body)
        self.assertIn('OpexDecide("RAIL_SEARCH", "type=resumable outcome=" + slice.stop + " iters=" + state.spent + " budget=" + state.iterationBudget + slotStr);', body)


class PersistenceContract(unittest.TestCase):
    def test_reconcile_cleans_multi_slots(self):
        body = _function_body(_read("persist.nut"), "OpexAI::_reconcileAfterLoad")
        self.assertIn("if (V184_RAIL_SEARCH_SLOTS > 1 && this._v184RailSlots != null) {", body)
        self.assertIn("this._v184InitRailSlots();", body)


class ForbiddenIdentifiers(unittest.TestCase):
    def test_no_forbidden_identifiers_in_v184_methods(self):
        rail = _read("task_rail.nut")
        v184_section = rail[rail.index("/* V184 : gestion des créneaux"):]
        forbidden = ["p" + "arent", "c" + "lone", "b" + "ase"]
        for word in forbidden:
            self.assertNotIn(word, v184_section.lower())


if __name__ == "__main__":
    unittest.main()
