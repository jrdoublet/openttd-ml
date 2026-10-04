#!/usr/bin/env python3
"""Contrat statique AIR 03/10 4 : sonde C1 <= budget < C2, defaut 0.

probe_air0310_n1_fallback vaut 0 aux quatre difficultes. Les helpers
retournent avant toute ecriture ou AILog si le drapeau est faux. Les
branches de decision (choix N=1/N=2, continue, cash, clone) restent
celles d'avant la sonde. Aucune partie n'est lancee.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EMITTED_KEYS = (
    "plan=",
    "n_chosen=",
    "c1=",
    "c2=",
    "budget=",
    "p1=",
    "p2=",
    "stage=",
    "outcome=",
    "wait=",
)

DECISION_UNCHANGED = (
    "if (score2 > score1 || (score2 == score1 && profit2 > profit1)) chosen = econ2;",
    "return { initial = chosen, full = chosen };",
    "if (financeCapital > capitalBudget) continue;",
)


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _setting_block(info, name):
    start = info.index(f'name = "{name}"')
    return info[start:info.index("});", start)]


def _function_body(source, signature):
    start = source.index(signature)
    nxt = source.find("\nfunction ", start + 1)
    if nxt < 0:
        nxt = len(source)
    return source[start:nxt]


class TestAir0310_4N1FallbackProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.probes = _read("ai/OpexAI/probes.nut")
        cls.econ = _read("ai/OpexAI/air_economics_c121.nut")
        cls.planning = _read("ai/OpexAI/air_planning.nut")
        cls.selection = _read("ai/OpexAI/projects_selection.nut")
        cls.task_air = _read("ai/OpexAI/task_air.nut")
        cls.construction = _read("ai/OpexAI/air_construction.nut")
        cls.keep = _function_body(
            cls.probes, "function OpexAir0310KeepN1N2(plan, econ1, econ2, chosen)"
        )
        cls.copy = _function_body(
            cls.probes, "function OpexAir0310CopyN1N2(from, to)"
        )
        cls.probe = _function_body(
            cls.probes, "function OpexAir0310N1FallbackProbe(source, budget, stage, outcome)"
        )
        cls.winner = _function_body(
            cls.econ, "function OpexC121OneOrTwoWinner(catalog, plan, plane, engineContext)"
        )
        cls.fused = _function_body(
            cls.econ, "function OpexC121OneOrTwoFused(catalog, plan, plane)"
        )
        cls.select = _function_body(
            cls.selection, "function OpexProjectSelectAffordable(alternatives, capitalBudget, limit)"
        )
        cls.build_air = _function_body(
            cls.construction, "function OpexBuildAirRoute(catalog, budget, plan, lines = null)"
        )
        cls.try_project = _function_body(
            cls.task_air,
            "function OpexAI::_tryBuildAirProject(year, project, rank, builtCount, passDiscards, anchor, yy)",
        )
        cls.try_direct = _function_body(
            cls.task_air, "function OpexAI::_tryBuildAir(year)"
        )

    def test_setting_declared_inert_in_info_nut(self):
        block = _setting_block(self.info, "probe_air0310_n1_fallback")
        self.assertIn(
            "AIR 03/10 4 probe: log C121 air plans lost or deferred when "
            "C1 <= budget < C2 after N=2 wins; 0 = off (default)",
            block,
        )
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1", block)
        self.assertIn("step_size = 1", block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 0", block)
        self.assertNotIn("easy_value = 1", block)
        self.assertEqual(self.info.count('name = "probe_air0310_n1_fallback"'), 1)

    def test_global_loaded_like_air0310_one_two_fused(self):
        self.assertIn("PROBE_AIR0310_N1_FALLBACK <- false;", self.globals)
        self.assertEqual(self.globals.count("PROBE_AIR0310_N1_FALLBACK <-"), 1)
        self.assertIn("AIR0310_ONE_TWO_FUSED <- false;", self.globals)
        fused_load = (
            'AIR0310_ONE_TWO_FUSED = AIController.GetSetting("air0310_one_two_fused") != 0;'
        )
        probe_load = (
            'PROBE_AIR0310_N1_FALLBACK = AIController.GetSetting("probe_air0310_n1_fallback") != 0;'
        )
        self.assertIn(fused_load, self.settings)
        self.assertIn(probe_load, self.settings)
        self.assertEqual(
            self.settings.count('AIController.GetSetting("probe_air0310_n1_fallback")'), 1
        )
        self.assertLess(self.settings.index(fused_load), self.settings.index(probe_load))
        self.assertNotIn("PROBE_AIR0310_N1_FALLBACK <-", self.settings)
        self.assertNotIn("probe_air0310_n1_fallback", self.persist)
        self.assertNotIn("PROBE_AIR0310_N1_FALLBACK", self.persist)

    def test_helpers_return_before_any_work_when_disabled(self):
        for body, label in (
            (self.keep, "keep"),
            (self.copy, "copy"),
            (self.probe, "probe"),
        ):
            guard = body.index("if (!PROBE_AIR0310_N1_FALLBACK")
            self.assertEqual(guard, body.index("if (!PROBE_AIR0310_N1_FALLBACK"), label)
            self.assertLess(guard, body.index("return;"), label)
        self.assertLess(
            self.keep.index("if (!PROBE_AIR0310_N1_FALLBACK || plan == null) return;"),
            self.keep.index("plan.c121N1C <-"),
        )
        self.assertLess(
            self.copy.index("if (!PROBE_AIR0310_N1_FALLBACK || from == null || to == null) return;"),
            self.copy.index("to.c121N1C <-"),
        )
        self.assertLess(
            self.probe.index("if (!PROBE_AIR0310_N1_FALLBACK) return;"),
            self.probe.index("AILog.Info"),
        )
        self.assertLess(
            self.probe.index("if (!PROBE_AIR0310_N1_FALLBACK) return;"),
            self.probe.index("AIDate.GetCurrentDate()"),
        )
        self.assertNotIn("OpexC121EngineEconomics", self.keep)
        self.assertNotIn("OpexC121EngineEconomics", self.copy)
        self.assertNotIn("OpexC121EngineEconomics", self.probe)
        self.assertNotIn("OpexC121OneOrTwoDepth", self.keep + self.copy + self.probe)

    def test_emitted_line_format_and_gap_guard(self):
        info = self.probe.index("AILog.Info(")
        emitted = self.probe[info:]
        self.assertIn('"OPEX "', emitted)
        self.assertIn('" AIR_N1_FALLBACK plan="', emitted)
        cursor = 0
        for key in EMITTED_KEYS:
            found = emitted.find('"' + key, cursor)
            if found < 0:
                found = emitted.find(key, cursor)
            self.assertGreaterEqual(found, 0, key)
            cursor = found + len(key)
        self.assertIn('c1 <= budget && budget < c2', self.probe)
        self.assertIn('stage=" + stage', emitted)
        self.assertIn('outcome=" + outcome', emitted)
        self.assertIn("n_chosen=", emitted)
        # Pas d'emission si une economie manque.
        self.assertIn("if (c1 < 0 || c2 < 0 || budget == null) return;", self.probe)

    def test_keep_after_choice_does_not_change_winner(self):
        keep_call = "if (PROBE_AIR0310_N1_FALLBACK) OpexAir0310KeepN1N2(plan, econ1, econ2, chosen);"
        self.assertEqual(self.econ.count(keep_call), 2)
        for body in (self.winner, self.fused):
            choice = body.index(
                "if (score2 > score1 || (score2 == score1 && profit2 > profit1)) chosen = econ2;"
            )
            keep = body.index(keep_call)
            ret = body.index("return { initial = chosen, full = chosen };")
            self.assertLess(choice, keep)
            self.assertLess(keep, ret)
        self.assertNotIn("chosen = econ1", self.keep)
        self.assertNotIn("chosen = econ2", self.keep)
        # Le chemin 3b historique reste deux appels complets hors fusion.
        legacy = self.winner[self.winner.index("  local econ1"):]
        self.assertIn("OpexC121EngineEconomics(catalog, plan, plane, 1, false)", legacy)
        self.assertIn("OpexC121EngineEconomics(catalog, plan, plane, 2, false)", legacy)

    def test_no_decision_branch_modified(self):
        for token in DECISION_UNCHANGED:
            self.assertIn(token, self.econ + self.selection + self.task_air)
        # La porte de selection historique est conservee au bit pres.
        self.assertIn(
            "    if (financeCapital > capitalBudget) continue;\n", self.select
        )
        # La sonde s'ajoute AVANT le continue, sans le conditionner.
        gate = self.select.index(
            "if (PROBE_AIR0310_N1_FALLBACK && financeCapital > capitalBudget)\n"
            '      OpexAir0310N1FallbackProbe(project, capitalBudget, "select", "lost");\n'
            "    if (financeCapital > capitalBudget) continue;"
        )
        self.assertGreaterEqual(gate, 0)
        self.assertIn('"select"', self.select)
        self.assertIn('"lost"', self.select)
        # Financement : le `if (money < need)` d'origine suit la sonde.
        self.assertIn(
            "if (PROBE_AIR0310_N1_FALLBACK && money < need)\n"
            '        OpexAir0310N1FallbackProbe(plan, money, "finance", "deferred");\n'
            "      if (money < need) {",
            self.try_project,
        )
        self.assertIn(
            "if (PROBE_AIR0310_N1_FALLBACK && money < need)\n"
            "      OpexAir0310N1FallbackProbe(plan, money, \"finance\", \"deferred\");\n"
            "    if (money < need) {",
            self.try_direct,
        )
        # Construction : le premier avion et le clone manquant, sans changer
        # reason=PLANE ni le break du second avion.
        self.assertIn('result.reason = "PLANE";', self.build_air)
        self.assertIn("OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, []);",
                      self.build_air)
        self.assertIn("built.append(extra);", self.build_air)
        plane_fail = self.build_air.index("result.error = AIError.GetLastError();")
        probe_plane = self.build_air.index(
            "if (PROBE_AIR0310_N1_FALLBACK && result.error == AIError.ERR_NOT_ENOUGH_CASH)"
        )
        reason_plane = self.build_air.index('result.reason = "PLANE";')
        self.assertLess(plane_fail, probe_plane)
        self.assertLess(probe_plane, reason_plane)
        extra_probe = self.build_air.index(
            'OpexAir0310N1FallbackProbe(plan, AICompany.GetBankBalance(AICompany.COMPANY_SELF), "build", "built");'
        )
        extra_break = self.build_air.index("break;", extra_probe)
        self.assertLess(extra_probe, extra_break)
        # C121 ne substitue toujours pas d'equipement apres classement.
        self.assertIn("if (C121_AIR_ECONOMICS) return unchanged;",
                      _read("ai/OpexAI/air_engine_choice.nut"))

    def test_emission_sites_cover_the_loss(self):
        # Selection : le projet N=2 est jete du vivier finançable.
        self.assertEqual(self.selection.count("OpexAir0310N1FallbackProbe("), 1)
        self.assertIn('"select", "lost"', self.select)
        # Financement : selectionne puis caisse insuffisante, y compris le
        # chemin direct hors portefeuille.
        self.assertEqual(self.task_air.count("OpexAir0310N1FallbackProbe("), 2)
        self.assertIn('"finance", "deferred"', self.try_project)
        self.assertIn('"finance", "deferred"', self.try_direct)
        # Construction : premier avion refuse pour caisse, ou second avion
        # non clone (achat partiel N=2 -> 1).
        self.assertEqual(self.construction.count("OpexAir0310N1FallbackProbe("), 2)
        self.assertIn('"build", "lost"', self.build_air)
        self.assertIn('"build", "built"', self.build_air)
        self.assertIn("ERR_NOT_ENOUGH_CASH", self.build_air)

    def test_cache_and_choice_reuse_stored_scalars(self):
        copy_call = "if (PROBE_AIR0310_N1_FALLBACK) OpexAir0310CopyN1N2("
        self.assertIn("OpexAir0310CopyN1N2(plan, routeChoice);", self.econ)
        self.assertEqual(self.planning.count("OpexAir0310CopyN1N2(routeChoice, plan);"), 3)
        self.assertEqual(self.econ.count(copy_call), 1)
        self.assertEqual(self.planning.count(copy_call), 3)
        # Les scalaires copient capital/profit deja calcules, pas un nouvel appel.
        self.assertIn("plan.c121N1C <-", self.keep)
        self.assertIn("plan.c121N1P <-", self.keep)
        self.assertIn("plan.c121N2C <-", self.keep)
        self.assertIn("plan.c121N2P <-", self.keep)
        self.assertIn("plan.c121NChosen <-", self.keep)
        self.assertIn('if (!("c121N1Date" in plan)) plan.c121N1Date <- AIDate.GetCurrentDate();',
                      self.keep)


if __name__ == "__main__":
    unittest.main()
