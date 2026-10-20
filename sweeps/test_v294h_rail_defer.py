"""Contrats V294h. Ne compilent pas Squirrel : smoke moteur distinct requis."""
import re
import unittest
from pathlib import Path

from test_b5_rail_persistence import function_body

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class TestV294hRailDefer(unittest.TestCase):
    def setUp(self):
        self.code = read("task_v294h.nut")

    def test_setting_default_zero_and_loaded_once(self):
        block = re.search(r'AddSetting\(\{\s*name = "v294_rail_defer",(.*?)\}\);',
                          read("info.nut"), re.S).group(1)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{level}_value\s*=\s*0\b")
        self.assertIn("min_value = 0, max_value = 5000", block)
        self.assertEqual(read("settings.nut").count('GetSetting("v294_rail_defer")'), 1)
        self.assertIn("V294H_RAIL_DEFER <- 0;", read("globals_pre.nut"))

    def test_file_required_and_state_transient(self):
        main = read("main.nut")
        self.assertIn('require("task_v294h.nut");', main)
        self.assertIn("this._v294Deferred = [];", main)
        self.assertIn("this._v294Ready = {};", main)
        persist = read("persist.nut")
        self.assertIn("this._v294Deferred = [];", persist)
        self.assertNotIn("v294Deferred =", function_body(persist, "function OpexAI::Save()"))

    def test_every_hook_is_guarded(self):
        for name in ("main.nut", "probes.nut"):
            self.assertIn("if (V294H_RAIL_DEFER > 0) OpexV294hAdvance(this);", read(name))
        rail = read("task_rail.nut")
        self.assertIn("(V294H_RAIL_DEFER > 0) ? OpexV294hQuickBudget(plan.iterationBudget) : plan.iterationBudget", rail)
        self.assertIn("if (V294H_RAIL_DEFER > 0 && !v233Graft && !c121PrepPlan) {", rail)
        self.assertIn("if (V294H_RAIL_DEFER > 0 && !(V233_GOODS_GRAFT && OpexV233IsGraft(state.candidate))) {", rail)
        self.assertIn('if (v294Ready && result.reason != "CASH") OpexV294hConsumed(this, candidate, result);', rail)
        # Toutes les fonctions publiques sortent tout de suite au defaut.
        for fn in ("OpexV294hQuickBudget(planBudget)", "OpexV294hTryDefer(owner, state, slice, plan)",
                   "OpexV294hAdvance(owner)", "OpexV294hBeforeSearch(owner, candidate)"):
            body = function_body(self.code, "function " + fn)
            self.assertIn("V294H_RAIL_DEFER <= 0", body.split("\n")[1] + body.split("\n")[2])

    def test_defer_only_primary_abnd_and_reason_code(self):
        body = function_body(self.code, "function OpexV294hTryDefer(owner, state, slice, plan)")
        self.assertIn('slice.stop != "ABND"', body)
        self.assertIn("isStockSearch", body)
        self.assertIn("plan = clone plan", body)
        self.assertIn('plan.reason = "DEFER";', body)
        self.assertIn('"DEFER"', read("lines.nut"))

    def test_background_never_crosses_tick(self):
        body = function_body(self.code, "function OpexV294hAdvance(owner)")
        self.assertIn("AIController.GetTick() == tick", body)
        self.assertIn("GetOpsTillSuspend()", body)

    def test_no_closure_and_no_undeclared_globals(self):
        self.assertNotRegex(self.code, r"function\s*\(")
        for name in set(re.findall(r"\bV294H_[A-Z_]+\b", self.code)):
            declared = (f"const {name} =" in self.code) or (f"{name} <-" in read("globals_pre.nut"))
            self.assertTrue(declared, name)


if __name__ == "__main__":
    unittest.main()
