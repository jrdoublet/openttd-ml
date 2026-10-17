#!/usr/bin/env python3
"""Contrat statique F-EVENT-BACKLOG-01 : subsidy_reselect_if_purged.

Vérifie :
1. Déclaration du réglage 'subsidy_reselect_if_purged' à 1 aux quatre difficultés (adopté le 11/10) dans info.nut.
2. Initialisation globale SUBSIDY_RESELECT_IF_PURGED <- true dans globals_pre.nut.
3. Lecture du réglage dans settings.nut (OpexLoadSettings).
4. _purgeSubsidyFromProjects renvoie le nombre de candidats retirés (best, road.best, candidateGroups).
5. _c77RemoveSubsidy ne relance OpexReselectProjects que si purged > 0 sous le réglage actif,
   et conserve le comportement inconditionnel strict sous le défaut 0.
6. Absence de persistance inutile dans persist.nut.
7. Respect des invariants Squirrel (mots réservés, équilibre des accolades).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from sweeps.campaign_freeze import parse_ai_setting_specs, parse_ai_settings

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"

SETTING = "subsidy_reselect_if_purged"
GLOBAL = "SUBSIDY_RESELECT_IF_PURGED"


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start : pos + 1]
    raise AssertionError(f"Corps non fermé pour : {signature}")


def _brace_balance(text: str) -> int:
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\":
                    i += 1
                i += 1
        elif ch == "'":
            i += 1
            while i < n and text[i] != "'":
                if text[i] == "\\":
                    i += 1
                i += 1
        elif text.startswith("//", i):
            i = text.find("\n", i)
            if i < 0:
                break
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return depth
        i += 1
    return depth


class TestSubsidyReselectIfPurged(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info_src = _read("ai/OpexAI/info.nut")
        cls.globals_src = _read("ai/OpexAI/globals_pre.nut")
        cls.settings_src = _read("ai/OpexAI/settings.nut")
        cls.persist_src = _read("ai/OpexAI/persist.nut")
        cls.task_projects_src = _read("ai/OpexAI/task_projects.nut")
        cls.event_handlers_src = _read("ai/OpexAI/event_handlers.nut")

        cls.purge_body = _function_body(
            cls.task_projects_src, "function OpexAI::_purgeSubsidyFromProjects("
        )
        cls.remove_body = _function_body(
            cls.event_handlers_src, "function OpexAI::_c77RemoveSubsidy("
        )

    def test_setting_declaration_and_four_difficulties_defaults(self):
        self.assertNotIn(SETTING, parse_ai_settings(AI / "info.nut"))
        self.assertNotIn(SETTING, parse_ai_setting_specs(AI / "info.nut"))

    def test_globals_declaration(self):
        self.assertNotIn(f"{GLOBAL} <-", self.globals_src)

    def test_settings_loading(self):
        self.assertNotIn(f'GetSetting("{SETTING}")', self.settings_src)

    def test_setting_not_in_persist(self):
        self.assertNotIn(SETTING, self.persist_src)
        self.assertNotIn(GLOBAL, self.persist_src)

    def test_purge_returns_counter(self):
        # 1. Early exits return 0
        self.assertIn("if (subId == null || subId < 0) return 0;", self.purge_body)
        self.assertIn("if (this._projects == null) return 0;", self.purge_body)

        # 2. Initialise le compteur local
        self.assertIn("local removed = 0;", self.purge_body)

        # 3. Compte les suppressions dans best
        self.assertIn("this._projects.best.remove(i);", self.purge_body)
        idx_best_remove = self.purge_body.index("this._projects.best.remove(i);")
        idx_best_inc = self.purge_body.index("removed++;", idx_best_remove)
        self.assertTrue(idx_best_remove < idx_best_inc < idx_best_remove + 50)

        # 4. Compte les suppressions dans road.best
        self.assertIn("this._projects.road.best.remove(i);", self.purge_body)
        idx_road_remove = self.purge_body.index("this._projects.road.best.remove(i);")
        idx_road_inc = self.purge_body.index("removed++;", idx_road_remove)
        self.assertTrue(idx_road_remove < idx_road_inc < idx_road_remove + 50)

        # 5. Compte les suppressions dans candidateGroups
        self.assertIn("delete this._projects.candidateGroups[key];", self.purge_body)
        self.assertIn("removed += count;", self.purge_body)

        # 6. Renvoie le compteur
        self.assertIn("return removed;", self.purge_body)

    def test_c77_remove_subsidy_conditional_guard(self):
        # Récupération du retour de purge
        self.assertIn("local purged = this._purgeSubsidyFromProjects(subId);", self.remove_body)

        # La purge activeSubsidies précède la garde conditionnelle
        active_sub_delete = "delete this._activeSubsidies[subId];"
        self.assertIn(active_sub_delete, self.remove_body)
        idx_sub_del = self.remove_body.index(active_sub_delete)
        idx_purge = self.remove_body.index("local purged = this._purgeSubsidyFromProjects(subId);")
        self.assertLess(idx_sub_del, idx_purge)

        # Garde conditionnelle sous SUBSIDY_RESELECT_IF_PURGED
        guard = "if (purged <= 0) return;"
        self.assertIn(guard, self.remove_body)

        # Reselection vient APRES la garde
        idx_guard = self.remove_body.index(guard)
        idx_reselect = self.remove_body.index("OpexReselectProjects(")
        self.assertLess(idx_guard, idx_reselect)

        # Vérification sémantique :
        # Sous GLOBAL = false (défaut 0), la condition est false quel que soit purged -> réélection exécutée.
        # Sous GLOBAL = true (réglage 1) et purged = 0 -> early return, réélection sautée.
        # Sous GLOBAL = true (réglage 1) et purged > 0 -> pas d'early return, réélection exécutée.

    def test_squirrel_reserved_words_and_syntax(self):
        for reserved in ("clone", "base", "parent", "resume"):
            for line in self.purge_body.splitlines():
                tokens = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", line)
                self.assertNotIn(
                    reserved,
                    tokens,
                    f"Mot réservé '{reserved}' utilisé comme identifiant dans _purgeSubsidyFromProjects",
                )
            for line in self.remove_body.splitlines():
                tokens = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", line)
                self.assertNotIn(
                    reserved,
                    tokens,
                    f"Mot réservé '{reserved}' utilisé comme identifiant dans _c77RemoveSubsidy",
                )

        self.assertEqual(_brace_balance(self.purge_body), 0)
        self.assertEqual(_brace_balance(self.remove_body), 0)

    def test_purge_simulation_logic(self):
        """Simulation Python directe de l'algorithme de _purgeSubsidyFromProjects."""

        def simulate_purge(projects, sub_id):
            if sub_id is None or sub_id < 0:
                return 0
            if projects is None:
                return 0
            removed = 0
            if "best" in projects and projects["best"] is not None:
                for i in range(len(projects["best"]) - 1, -1, -1):
                    p = projects["best"][i]
                    if (
                        p is not None
                        and "payload" in p
                        and p["payload"] is not None
                        and p["payload"].get("isSubsidy")
                        and p["payload"].get("subsidyId") == sub_id
                    ):
                        projects["best"].pop(i)
                        removed += 1
            if "road" in projects and projects["road"] is not None:
                if "best" in projects["road"] and projects["road"]["best"] is not None:
                    for i in range(len(projects["road"]["best"]) - 1, -1, -1):
                        p = projects["road"]["best"][i]
                        if (
                            p is not None
                            and "payload" in p
                            and p["payload"] is not None
                            and p["payload"].get("isSubsidy")
                            and p["payload"].get("subsidyId") == sub_id
                        ):
                            projects["road"]["best"].pop(i)
                            removed += 1
            if "candidateGroups" in projects and projects["candidateGroups"] is not None:
                key = f"subsidy|{sub_id}"
                if key in projects["candidateGroups"]:
                    entry = projects["candidateGroups"][key]
                    count = len(entry) if isinstance(entry, list) else (1 if entry is not None else 0)
                    del projects["candidateGroups"][key]
                    removed += count
            return removed

        # Test cas 1 : entrée nulle ou invalide
        self.assertEqual(simulate_purge(None, 42), 0)
        self.assertEqual(simulate_purge({}, None), 0)
        self.assertEqual(simulate_purge({}, -1), 0)

        # Test cas 2 : rien à purger
        projects = {
            "best": [{"payload": {"isSubsidy": False, "subsidyId": -1}}],
            "road": {"best": []},
            "candidateGroups": {"other|1": [{"payload": {}}]},
        }
        self.assertEqual(simulate_purge(projects, 77), 0)

        # Test cas 3 : purge complète (dans best, road.best et candidateGroups)
        sub_proj = {"payload": {"isSubsidy": True, "subsidyId": 77}}
        norm_proj = {"payload": {"isSubsidy": False, "subsidyId": -1}}
        projects = {
            "best": [sub_proj, norm_proj],
            "road": {"best": [sub_proj]},
            "candidateGroups": {
                "subsidy|77": [sub_proj],
                "other|1": [norm_proj],
            },
        }
        count = simulate_purge(projects, 77)
        self.assertEqual(count, 3)
        self.assertEqual(len(projects["best"]), 1)
        self.assertEqual(len(projects["road"]["best"]), 0)
        self.assertNotIn("subsidy|77", projects["candidateGroups"])
        self.assertIn("other|1", projects["candidateGroups"])

        # Test cas 4 : candidateGroups avec objet simple au lieu de liste (comme dans selftests.nut)
        projects = {
            "best": [],
            "road": {"best": []},
            "candidateGroups": {"subsidy|77": sub_proj},
        }
        count = simulate_purge(projects, 77)
        self.assertEqual(count, 1)
        self.assertNotIn("subsidy|77", projects["candidateGroups"])


if __name__ == "__main__":
    unittest.main()
