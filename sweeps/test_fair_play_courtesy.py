"""Contrats statiques pour FAIR-PLAY / JOURNAUX-NORMAL (fair_play_courtesy).

Exigences :
1. Le reglage fair_play_courtesy est declare dans info.nut avec easy/medium/hard/custom = 0.
2. La globale FAIR_PLAY_COURTESY est declaree a false dans globals_pre.nut.
3. Le reglage est lu dans les deux chargeurs de settings.nut (OpexLoadSettings et OpexLoadBusDistrictSettings).
4. Les gardes de panneaux et de courtoisie (OpexSignAllowed, OpexClearBudgetSigns, debug_signs = 2,
   budget_sign_overlay = 2) sont presentes dans difficulty.nut, probes.nut, task_report.nut et persist.nut.
5. Invariance stricte du chemin a 0 et respect des regles Squirrel (pas de mots reserves, pas de closures).
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
RESERVED_WORDS = (
    "clone", "base", "parent", "static", "delegate",
    "vargc", "vargv", "resume", "yield", "constructor", "instanceof",
)


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    match = re.search(r"\bfunction\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{", source)
    if match is None:
        raise AssertionError(f"fonction introuvable : {name}")
    brace = match.end() - 1
    depth = 0
    for token in re.finditer(r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\n]*|[{}]', source[brace:]):
        if token[0] == "{":
            depth += 1
        elif token[0] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():brace + token.end()]
    raise AssertionError(f"fonction non terminee : {name}")


class TestFairPlayCourtesy(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.info = _read("info.nut")
        cls.globals_pre = _read("globals_pre.nut")
        cls.settings = _read("settings.nut")
        cls.difficulty = _read("difficulty.nut")
        cls.probes = _read("probes.nut")
        cls.task_report = _read("task_report.nut")
        cls.persist = _read("persist.nut")

    def test_info_setting_has_four_zeros(self) -> None:
        match = re.search(r'name\s*=\s*"fair_play_courtesy"(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(match, "Reglage fair_play_courtesy manquant dans info.nut")
        block = match.group(1)
        self.assertRegex(block, r"\bmin_value\s*=\s*0\b")
        self.assertRegex(block, r"\bmax_value\s*=\s*1\b")
        self.assertRegex(block, r"\bflags\s*=\s*0\b")
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, rf"\b{key}\s*=\s*0\b")

    def test_global_declared_false_in_globals_pre(self) -> None:
        self.assertIn("FAIR_PLAY_COURTESY <- false;", self.globals_pre)

    def test_read_in_both_settings_loaders(self) -> None:
        stmt = 'FAIR_PLAY_COURTESY = AIController.GetSetting("fair_play_courtesy") == 1;'
        load_main = _function_body(self.settings, "OpexLoadSettings")
        load_bus = _function_body(self.settings, "OpexLoadBusDistrictSettings")
        self.assertIn(stmt, load_main)
        self.assertIn(stmt, load_bus)
        self.assertIn("if (FAIR_PLAY_COURTESY) OPEX_LEVEL_LIMITS = true;", load_main)
        self.assertEqual(self.settings.count('GetSetting("fair_play_courtesy")'), 2)

    def test_difficulty_capabilities_and_helpers(self) -> None:
        self.assertRegex(self.difficulty, r"\bdebug_signs\s*=\s*2\b")
        self.assertRegex(self.difficulty, r"\bbudget_sign_overlay\s*=\s*2\b")
        allowed_body = _function_body(self.difficulty, "OpexSignAllowed")
        self.assertIn("if (FAIR_PLAY_COURTESY) return false;", allowed_body)
        self.assertIn('OpexLevelAllows("budget_sign_overlay")', allowed_body)
        self.assertIn('OpexLevelAllows("debug_signs")', allowed_body)

        clear_body = _function_body(self.difficulty, "OpexClearBudgetSigns")
        self.assertIn("AISign.IsValidSign(signId)", clear_body)
        self.assertIn("AISign.RemoveSign(signId)", clear_body)
        self.assertNotIn("DemolishSign", clear_body)
        self.assertIn("budgetSignIds.clear();", clear_body)

    def test_probes_and_report_guards(self) -> None:
        sign_body = _function_body(self.probes, "OpexSign")
        self.assertIn("if (!DEBUG_SIGNS) return;", sign_body)
        self.assertIn('if (!OpexSignAllowed("debug_signs")) return;', sign_body)
        self.assertLess(sign_body.index("if (!DEBUG_SIGNS) return;"),
                        sign_body.index('if (!OpexSignAllowed("debug_signs")) return;'))
        self.assertLess(sign_body.index('if (!OpexSignAllowed("debug_signs")) return;'),
                        sign_body.index("AISign.BuildSign"))

        decide_body = _function_body(self.probes, "OpexDecide")
        self.assertIn('if (FAIR_PLAY_COURTESY && kind != "LOAD_RECONCILE") return;', decide_body)

        report_body = _function_body(self.task_report, "OpexAI::_reportYear")
        self.assertIn('if (!OpexSignAllowed("budget")) {', report_body)
        self.assertIn("OpexClearBudgetSigns(_budgetSignIds);", report_body)

    def test_persist_reconcile_cleans_budget_signs(self) -> None:
        reconcile_body = _function_body(self.persist, "OpexAI::_reconcileAfterLoad")
        self.assertIn("if (FAIR_PLAY_COURTESY && _budgetSignIds != null)", reconcile_body)
        self.assertIn("OpexClearBudgetSigns(_budgetSignIds);", reconcile_body)

    def test_squirrel_safety_and_no_sleep(self) -> None:
        for fn_name in ("OpexSignAllowed", "OpexClearBudgetSigns"):
            body = _function_body(self.difficulty, fn_name)
            self.assertNotIn("Sleep(", body)
            self.assertNotIn("function(", body)
            self.assertNotIn(".find(", body)
            for word in RESERVED_WORDS:
                self.assertNotRegex(body, rf"\blocal\s+{word}\b")


if __name__ == "__main__":
    unittest.main()
