"""V249 : contrats statiques des statues de ville.

Reglage entier v249_statue_cash, defaut 0, lu une fois. A 0 la tache ne touche
aucune API de jeu. Un passage pose au plus une statue. Le journal est garde
par DECISION_LOG avant le formatage des champs. Aucun etat n'est sauvegarde.
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _body(source, signature):
    match = re.search(re.escape(signature) + r"\n\{(.*?)\n\}", source, re.S)
    return match.group(1) if match else ""


class TestV249Statues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.task = cls.sources["task_v249.nut"]
        cls.dispatch = _body(cls.task, "function OpexAI::_dispatchV249Statue(task, year)")
        cls.measure = _body(cls.task, "function OpexV249MeasureStatueCost(townId)")

    def test_setting_declared_default_zero(self):
        block = re.search(
            r'name = "v249_statue_cash",(.*?)\}\);', self.sources["info.nut"], re.S)
        self.assertIsNotNone(block)
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 10000", body)
        self.assertIn("step_size = 50", body)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(body, level + r" = 0\b")
        self.assertIn("V249_STATUE_CASH <- 0;", self.sources["globals_pre.nut"])

    def test_setting_read_once(self):
        reads = [(name, text.count('GetSetting("v249_statue_cash")'))
                 for name, text in self.sources.items()]
        self.assertEqual(sum(count for _, count in reads), 1)
        self.assertEqual(self.sources["settings.nut"].count('GetSetting("v249_statue_cash")'), 1)
        self.assertIn("function OpexLoadSettings()", self.sources["settings.nut"])
        self.assertRegex(
            self.sources["settings.nut"],
            r'statueCash >= 0 && statueCash <= 10000\) \? statueCash : 0')

    def test_zero_cost_guard(self):
        self.assertTrue(self.dispatch)
        guard = "if (V249_STATUE_CASH <= 0) return false;"
        self.assertIn(guard, self.dispatch)
        guard_at = self.dispatch.index(guard)
        for api in ("AIDate", "AICompany", "AITown", "AIStation", "AIVehicle",
                    "AIAccounting", "AITestMode", "AIGameSettings", "OpexDecide"):
            found = self.dispatch.find(api)
            if found >= 0:
                self.assertGreater(found, guard_at, api)
        start = self.sources["main.nut"]
        appended = 'this._taskQueue.append({ name = "v249_statue", dueCycle = 0, enabled = V249_STATUE_CASH > 0 });'
        self.assertIn(appended, start)
        self.assertLess(start.index("OpexV147ExtendQueue(this);"), start.index(appended))
        loan = start.index("AIGameSettings.GetValue(\"difficulty.max_loan\")")
        self.assertLess(start.index("if (V249_STATUE_CASH > 0 && V249_BASE_MAX_LOAN <= 0)"), loan)

    def test_at_most_one_statue_per_pass(self):
        self.assertEqual(self.dispatch.count("AITown.PerformTownAction"), 1)
        call = self.dispatch.index("AITown.PerformTownAction")
        self.assertNotIn("foreach", self.dispatch[call:])
        self.assertNotIn("while", self.dispatch[call:])
        self.assertLess(self.dispatch.rfind("return true;"), len(self.dispatch))
        self.assertIn("local built = AITown.PerformTownAction", self.dispatch)
        self.assertIn("if (!built)", self.dispatch)
        self.assertEqual(self.measure.count("AITown.PerformTownAction"), 1)
        self.assertLess(self.measure.index("local test = AITestMode();"),
                        self.measure.index("AITown.PerformTownAction"))
        self.assertIn("if (this._v249StatueMonth == ym) return false;", self.dispatch)
        self.assertIn('this._taskQueue.append({ name = "v249_statue"', self.sources["main.nut"])
        self.assertIn('task.name == "v249_statue"', self.sources["scheduler.nut"])

    def test_journal_guarded_and_aggregated(self):
        for line in self.task.splitlines():
            if "OpexDecide(" in line:
                self.assertIn("DECISION_LOG", line, line)
        self.assertIn(
            'OpexDecide("V249_STATUE", "town=" + bestTown + " cost=" + cost + " cash=" + net'
            ' + " threshold=" + threshold + " lines=" + bestLines + " profit=" + bestProfit)',
            self.dispatch)
        self.assertIn('OpexDecide("V249_SKIP", "reason=cash cash="', self.dispatch)
        self.assertIn(
            '"reason=no_town statue=" + nStatue + " unavailable=" + nUnavail',
            self.dispatch)
        loop = self.dispatch[self.dispatch.index("foreach (townId, info in byTown)"):
                             self.dispatch.index("if (!found)")]
        self.assertNotIn("OpexDecide", loop)

    def test_no_saved_state(self):
        persist = self.sources["persist.nut"]
        self.assertNotIn("v249", persist.lower())
        self.assertNotIn("_v249StatueMonth", persist)
        self.assertNotIn("V249_BASE_MAX_LOAN", persist)
        self.assertIn("_v249StatueMonth = -1;", self.sources["main.nut"])


if __name__ == "__main__":
    unittest.main()
