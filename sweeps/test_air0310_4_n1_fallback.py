#!/usr/bin/env python3
"""Contrat statique AIR 03/10 4 : publier N=1 quand N=2 n'est pas finançable.

air0310_n1_fallback vaut 0 aux quatre difficultes. A 1, les deux economies
deja calculees sont conservees sans recalcul, meme si la sonde est a 0.
OpexProjectSelectAffordable reecrit le projet en place quand le capital de
financement de N=2 depasse le budget et que celui de N=1 tient. Une seule
place, ouverture a 1 avion. Si le budget couvre N=2, aucun ecrit vers N=1.
Aucune partie n'est lancee.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SETTING = "air0310_n1_fallback"
GLOBAL = "AIR0310_N1_FALLBACK"
PROBE_GLOBAL = "PROBE_AIR0310_N1_FALLBACK"

RECALC = (
    "OpexC121EngineEconomics",
    "OpexC121OneOrTwoDepth",
    "OpexC121OneOrTwoInvariants",
    "OpexC121AirEconomics",
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


def _word(name, text):
    return re.search(rf"\b{name}\b", text) is not None


class TestAir0310_4N1Fallback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.probes = _read("ai/OpexAI/probes.nut")
        cls.econ = _read("ai/OpexAI/air_economics_c121.nut")
        cls.planning = _read("ai/OpexAI/air_planning.nut")
        cls.builders = _read("ai/OpexAI/projects_builders.nut")
        cls.selection = _read("ai/OpexAI/projects_selection.nut")
        cls.task_air = _read("ai/OpexAI/task_air.nut")
        cls.construction = _read("ai/OpexAI/air_construction.nut")
        cls.retain = _function_body(
            cls.probes, "function OpexAir0310RetainN1N2(plan, econ1, econ2)"
        )
        cls.copy_retained = _function_body(
            cls.probes, "function OpexAir0310CopyRetained(from, to)"
        )
        cls.keep = _function_body(
            cls.probes, "function OpexAir0310KeepN1N2(plan, econ1, econ2, chosen)"
        )
        cls.winner = _function_body(
            cls.econ, "function OpexC121OneOrTwoWinner(catalog, plan, plane, engineContext)"
        )
        cls.fused = _function_body(
            cls.econ, "function OpexC121OneOrTwoFused(catalog, plan, plane)"
        )
        cls.choose = _function_body(
            cls.econ, "function OpexC121ChooseRoutePlane(catalog, plan, lines"
        )
        cls.finance = _function_body(
            cls.builders, "function OpexAir0310EconomyFinance(plan, economics)"
        )
        cls.write_plan = _function_body(
            cls.builders, "function OpexAir0310WritePlan(plan, economics, asN1)"
        )
        cls.write_project = _function_body(
            cls.builders, "function OpexAir0310WriteProject(project)"
        )
        cls.restore = _function_body(
            cls.builders, "function OpexAir0310RestoreWinner(plan)"
        )
        cls.from_air = _function_body(
            cls.builders, "function OpexProjectFromAir(catalog, plan, planningOps)"
        )
        cls.select_n1 = _function_body(
            cls.selection, "function OpexAir0310SelectN1(project, capitalBudget)"
        )
        cls.select = _function_body(
            cls.selection,
            "function OpexProjectSelectAffordable(alternatives, capitalBudget, limit)",
        )

    def test_setting_defaults_to_zero_and_is_not_persisted(self):
        block = _setting_block(self.info, SETTING)
        self.assertIn(
            "if the chosen N=2 opening is not fundable and the already computed "
            "N=1 opening is, publish that N=1 economy; 1 = on, 0 = drop the plan (default)",
            block,
        )
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1", block)
        self.assertIn("step_size = 1", block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 0", block)
        self.assertNotIn("easy_value = 1", block)
        self.assertEqual(self.info.count(f'name = "{SETTING}"'), 1)
        self.assertIn(f"{GLOBAL} <- false;", self.globals)
        self.assertEqual(len(re.findall(rf"(?<!\w){GLOBAL} <-", self.globals)), 1)
        self.assertNotIn(SETTING, self.persist)
        self.assertFalse(_word(GLOBAL, self.persist))

    def test_loaded_after_fused_and_probe_on_the_same_pattern(self):
        fused = 'AIR0310_ONE_TWO_FUSED = AIController.GetSetting("air0310_one_two_fused") != 0;'
        probe = (
            'PROBE_AIR0310_N1_FALLBACK = AIController.GetSetting("probe_air0310_n1_fallback") != 0;'
        )
        load = f'{GLOBAL} = AIController.GetSetting("{SETTING}") != 0;'
        self.assertIn(fused, self.settings)
        self.assertIn(probe, self.settings)
        self.assertIn(load, self.settings)
        self.assertLess(self.settings.index(fused), self.settings.index(probe))
        self.assertLess(self.settings.index(probe), self.settings.index(load))
        self.assertEqual(self.settings.count(f'GetSetting("{SETTING}")'), 1)
        self.assertNotIn(f"{GLOBAL} <-", self.settings)

    def test_both_economies_are_kept_without_recalc_even_if_the_probe_is_off(self):
        retain_call = f"if ({GLOBAL}) OpexAir0310RetainN1N2(plan, econ1, econ2);"
        keep_call = (
            f"if ({PROBE_GLOBAL}) OpexAir0310KeepN1N2(plan, econ1, econ2, chosen);"
        )
        self.assertEqual(self.econ.count(retain_call), 2)
        self.assertEqual(self.winner.count(retain_call), 1)
        self.assertEqual(self.fused.count(retain_call), 1)
        self.assertLess(self.winner.index(keep_call), self.winner.index(retain_call))
        self.assertLess(self.fused.index(keep_call), self.fused.index(retain_call))
        self.assertLess(
            self.winner.index(retain_call),
            self.winner.index("return { initial = chosen, full = chosen };"),
        )
        self.assertNotIn(f"if ({PROBE_GLOBAL}) OpexAir0310RetainN1N2", self.econ)
        self.assertNotIn(f"if ({PROBE_GLOBAL} && {GLOBAL})", self.econ)
        self.assertNotIn(f"if ({GLOBAL} && {PROBE_GLOBAL})", self.econ)
        self.assertIn(f"if (!{GLOBAL} || plan == null) return;", self.retain)
        self.assertNotIn(PROBE_GLOBAL, self.retain)
        self.assertIn('plan.rawset("c121EconN1", econ1);', self.retain)
        self.assertIn('plan.rawset("c121EconN2", econ2);', self.retain)
        self.assertNotIn("<-", self.retain)
        for token in RECALC:
            self.assertNotIn(token, self.retain)
        self.assertIn(f"if (!{PROBE_GLOBAL} || plan == null) return;", self.keep)

    def test_references_travel_plan_choice_plan_and_not_the_fallback_flag(self):
        to_choice = f"if ({GLOBAL}) OpexAir0310CopyRetained(plan, routeChoice);"
        to_plan = f"if ({GLOBAL}) OpexAir0310CopyRetained(routeChoice, plan);"
        self.assertEqual(self.choose.count(to_choice), 1)
        self.assertEqual(self.econ.count(to_choice), 1)
        self.assertEqual(self.planning.count(to_plan), 3)
        self.assertNotIn(to_choice, self.planning)
        self.assertIn(f"if (!{GLOBAL} || from == null || to == null) return;", self.copy_retained)
        self.assertNotIn(PROBE_GLOBAL, self.copy_retained)
        self.assertIn('to.rawset("c121EconN1", from.c121EconN1);', self.copy_retained)
        self.assertIn('to.rawset("c121EconN2", from.c121EconN2);', self.copy_retained)
        self.assertNotIn("c121Air0310N1", self.copy_retained)
        self.assertNotIn("clone", self.copy_retained)
        self.assertNotIn("<-", self.copy_retained)
        for token in RECALC:
            self.assertNotIn(token, self.copy_retained)

    def test_selection_rewrites_one_project_before_the_budget_drop(self):
        call = f"foreach (project in alternatives) OpexAir0310SelectN1(project, capitalBudget);"
        gate = self.select.index(f"if ({GLOBAL}) {{")
        call_at = self.select.index(call, gate)
        prepare = self.select.index("OpexC118PrepareSelection(alternatives, capitalBudget);")
        prepare120 = self.select.index("OpexC120PrepareSelection(alternatives, capitalBudget);")
        floor = self.select.index("if (PORTFOLIO_FLOOR_PCT > 0)")
        drop = self.select.index("if (financeCapital > capitalBudget) continue;")
        self.assertEqual(self.select.count(call), 1)
        self.assertLess(call_at, prepare)
        self.assertLess(call_at, prepare120)
        self.assertLess(call_at, floor)
        self.assertLess(call_at, drop)
        drops = [
            match.start()
            for match in re.finditer(
                r"if \(financeCapital > capitalBudget\) continue;", self.select
            )
        ]
        # Plancher, boucle principale, filet : le meme tableau deja reecrit.
        self.assertEqual(len(drops), 3)
        self.assertTrue(all(call_at < at for at in drops))
        probe = self.select.index(
            f"if ({PROBE_GLOBAL} && financeCapital > capitalBudget)"
        )
        self.assertLess(probe, drops[1])
        self.assertNotIn(f"if ({GLOBAL} || financeCapital", self.select)
        self.assertNotIn("if (financeCapital > capitalBudget &&", self.select)
        self.assertNotIn("alternatives.append", self.select_n1)
        self.assertNotIn("RememberAll", self.select_n1)
        self.assertNotIn("OpexBuildAir", self.select_n1)
        self.assertNotIn(PROBE_GLOBAL, self.select_n1)
        for token in RECALC:
            self.assertNotIn(token, self.select_n1)

    def test_n1_is_published_only_when_n2_financing_capital_does_not_fit(self):
        self.assertIn("OpexAirRequiredMargin(newAirports)", self.finance)
        self.assertIn("economics.immobilise", self.finance)
        self.assertNotIn("c121N1C", self.finance)
        self.assertNotIn("c121N2C", self.finance)
        fit2 = self.select_n1.index("if (finance2 <= capitalBudget)")
        restore = self.select_n1.index("OpexAir0310WritePlan(plan, econ2, false)", fit2)
        leave = self.select_n1.index("return;", restore)
        install = self.select_n1.index(
            "if (finance1 <= capitalBudget && !fellBack)", leave
        )
        write1 = self.select_n1.index("OpexAir0310WritePlan(plan, econ1, true)", install)
        self.assertLess(fit2, restore)
        self.assertLess(restore, leave)
        self.assertLess(leave, install)
        self.assertLess(install, write1)
        self.assertIn("plan.economics == econ2", self.select_n1)
        self.assertIn("econ1.planes != 1", self.select_n1)
        self.assertIn("econ2.planes != 2", self.select_n1)
        self.assertNotIn("c121EconN1", self.write_project)
        self.assertNotIn("c121EconN2", self.write_project)
        self.assertIn("project.budgetCapital = budgetCapital;", self.write_project)
        self.assertIn("project.profitAnnual = projectEconomics.profitAnnual;", self.write_project)
        self.assertIn("project.capital = economics.capital;", self.write_project)
        self.assertIn("local margin = OpexAirRequiredMargin(newAirports);", self.write_project)
        self.assertIn("plan.planes = economics.planes;", self.write_plan)
        self.assertIn("plan.economics = economics;", self.write_plan)
        self.assertIn("plan.targetPlanes = economics.planes;", self.write_plan)
        self.assertNotIn(".clone", self.write_plan)
        self.assertNotIn("OpexAvailableCapital", self.from_air)
        opening = self.from_air.index("{")
        first = self.from_air.index(f"if ({GLOBAL}) OpexAir0310RestoreWinner(plan);", opening)
        self.assertLess(first, self.from_air.index("C111_AIR_C100_DECISION_SHADOW"))
        self.assertIn("OpexAir0310WritePlan(plan, plan.c121EconN2, false);", self.restore)
        for body in (self.finance, self.write_plan, self.write_project, self.restore):
            for token in RECALC:
                self.assertNotIn(token, body)

    def test_construction_opens_with_plan_planes_and_ignores_the_setting(self):
        self.assertIn(
            'local wanted = ("planes" in plan) ? plan.planes : 1;',
            self.construction,
        )
        self.assertFalse(_word(GLOBAL, self.construction))
        self.assertFalse(_word(GLOBAL, self.task_air))
        self.assertIn(PROBE_GLOBAL, self.construction)
        self.assertIn(PROBE_GLOBAL, self.task_air)


if __name__ == "__main__":
    unittest.main()
