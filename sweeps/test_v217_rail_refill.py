"""V217 : contrats statiques de la recharge du vivier rail sur tresorerie oisive.

Reglage entier a 0 (inerte), lu une seule fois et borne, un seul appel garde, pas avant la
troisieme annee de jeu, et le drapeau sans voyageurs est remis a faux juste apres la
regeneration. Le smoke 1x1 complete ces contrats.
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class TestV217RailRefill(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.orch = cls.sources["orchestrator.nut"]
        m = re.search(r"function OpexAI::_v217RailRefill\(\)\n\{(.*?)\n\}\n", cls.orch, re.S)
        cls.body = m.group(1) if m else ""

    def test_setting_default_freight_only(self):
        block = re.search(r'name = "v217_rail_refill",(.*?)\}\);', self.sources["info.nut"], re.S)
        self.assertIsNotNone(block)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block.group(1), level + r" = 1\b")
        self.assertIn("max_value = 2", block.group(1))

    def test_setting_read_once_and_bounded(self):
        self.assertEqual(sum(s.count('GetSetting("v217_rail_refill")') for s in self.sources.values()), 1)
        self.assertIn("V217_RAIL_REFILL <- 0;", self.sources["globals_pre.nut"])
        self.assertIn("V217_REGEN_NO_PAX <- false;", self.sources["globals_pre.nut"])
        self.assertRegex(self.sources["settings.nut"], r"railRefill >= 0 && railRefill <= 2\) \? railRefill : 0")

    def test_single_guarded_hook(self):
        hooks = [(n, l.strip()) for n, t in self.sources.items() for l in t.splitlines()
                 if "_v217RailRefill(" in l and "function" not in l]
        self.assertEqual(hooks, [("scheduler.nut",
                                  "if (V217_RAIL_REFILL > 0) this._v217RailRefill();")])
        self.assertIn("function _v217RailRefill();", self.sources["main.nut"])

    def test_guards(self):
        self.assertTrue(self.body)
        self.assertIn("if (V217_LAST_MONTH == ym) return;", self.body)
        self.assertIn("< OPEX_START_YEAR + 2) return;", self.body)
        self.assertIn("if (cash <= V217_IDLE_CASH_MIN) {", self.body)
        self.assertIn("if (startable >= V217_POOL_MIN) {", self.body)
        self.assertEqual(self.body.count('if (DECISION_LOG) OpexDecide("V217_RAIL_SKIP"'), 2)
        self.assertNotIn("_c77RefreshModeCatalog", self.body)
        self.assertIn("this._tooClose(c)", self.body)

    def test_rail_only_regen_and_flag_reset(self):
        regen = re.findall(r'OpexRegenerateModeProjects\([^;]*"(\w+)"', self.body, re.S)
        self.assertEqual(regen, ["rail"])
        on = self.body.index("V217_REGEN_NO_PAX = (V217_RAIL_REFILL == 1);")
        call = self.body.index("OpexRegenerateModeProjects(")
        off = self.body.index("V217_REGEN_NO_PAX = false;")
        self.assertLess(on, call)
        self.assertLess(call, off)

    def test_no_pax_flag_only_gates_rail_pax(self):
        users = [n for n, t in self.sources.items()
                 if re.search(r"\bV217_REGEN_NO_PAX\b", t) and n not in ("globals_pre.nut", "orchestrator.nut")]
        self.assertEqual(users, ["projects_generation.nut"])
        self.assertIn('local generatePax = (!targeted || entityKind == "town") && !V217_REGEN_NO_PAX;',
                      self.sources["projects_generation.nut"])


if __name__ == "__main__":
    unittest.main()
