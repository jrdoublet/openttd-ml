"""N75: contracts for the C75 bypass refund on immediate C80 marginal veto.

Static tests only: OpenTTD/Squirrel execution requires an authorized engine smoke.
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(path):
    return (ROOT / path).read_text(encoding="utf-8")


class N75C75RefundContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = source("ai/OpexAI/info.nut")
        cls.settings = source("ai/OpexAI/settings.nut")
        cls.globals = source("ai/OpexAI/globals_pre.nut")
        cls.task = source("ai/OpexAI/task_projects.nut")
        cls.persist = source("ai/OpexAI/persist.nut")
        cls.begin = cls.task.index("function OpexAI::_tryBuildProjects(year)")
        cls.end = cls.task.index("function ", cls.begin + 10)
        cls.build = cls.task[cls.begin:cls.end]

    def test_public_setting_0_1_2_and_all_difficulties_off(self):
        setting = self.info.split('name = "n75_c75_refund",', 1)[1].split("});", 1)[0]
        self.assertIn("min_value = 0, max_value = 2", setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting, rf"\b{difficulty}_value = 0\b")
        self.assertEqual(self.info.count('name = "n75_c75_refund"'), 1)
        self.assertIn("N75_C75_REFUND <- 0;", self.globals)
        self.assertEqual(self.settings.count('AIController.GetSetting("n75_c75_refund")'), 1)

    def test_refund_0_is_inert_and_shadow_1_observes_only(self):
        self.assertIn("if (N75_C75_REFUND != 0", self.build)
        self.assertIn('if (N75_C75_REFUND == 2) c75BypassConsumed = false;', self.build)
        self.assertEqual(self.build.count("c75BypassConsumed = false;"), 2)
        self.assertIn('else if (N75_C75_REFUND == 1 && n75RefundUsed)', self.build)
        self.assertIn('"postrefund=shadow_candidate"', self.build)
        self.assertNotIn("N75_C75_REFUND", self.persist)

    def test_c75_newline_cash_and_year_guards_stay_in_place(self):
        self.assertIn("local c75BypassConsumed = false;", self.build)
        self.assertIn("local n75RefundUsed = false;", self.build)
        self.assertIn("OpexC75KPassBypassIsNewLine(project)", self.build)
        self.assertIn("projCap <= availCap", self.build)
        self.assertIn("year == OPEX_START_YEAR + 1 || year == OPEX_START_YEAR + 2", self.build)
        self.assertIn("if (!n75RefundUsed) n75BypassConsumedHere = true;", self.build)
        self.assertIn("else if (N75_C75_REFUND == 2) n75PostRefundBypass = true;", self.build)
        self.assertIn("if (!c75BypassConsumed)", self.build)
        self.assertIn('c75StopReason = (availCap >= 0 && projCap > availCap) ? "cash" : "k_pass";', self.build)

    def test_refund_tied_to_first_bypass_and_immediate_c80_veto(self):
        consume = self.build.index("c75BypassConsumed = true;")
        c80 = self.build.index("if (OpexC80ProjectBelowMarginalFloor(this._lines, project))")
        refund = self.build.index("if (n75BypassConsumedHere && !n75RefundUsed)")
        constructor = self.build.index('if (mode == "fleet")', refund)
        self.assertLess(consume, c80)
        self.assertLess(c80, refund)
        self.assertLess(refund, constructor)
        veto_block = self.build[refund:constructor]
        self.assertIn("n75RefundUsed = true;", veto_block)
        self.assertIn('"c80_marginal_before_constructor"', veto_block)
        self.assertIn("if (N75_C75_REFUND == 2) c75BypassConsumed = false;", veto_block)
        self.assertEqual(self.build.count("n75RefundUsed = true;"), 1)
        self.assertIn("continue;", veto_block)

    def test_postrefund_log_proves_execution_then_own_key_built(self):
        self.assertIn("local n75PostRefundBypass = false;", self.build)
        self.assertLess(self.build.index("local n75PostRefundBypass = false;"),
                        self.build.index("if (builtCount > 0) {", self.build.index("local n75PostRefundBypass = false;")))
        attempt = self.build.index('"postrefund=attempt"')
        builder = self.build.index('this._tryBuildAirProject(', attempt)
        built = self.build.index('"postrefund=built"')
        self.assertLess(attempt, builder)
        self.assertGreater(built, builder)
        self.assertIn("OpexC69AttemptKey(project) in c75BuiltKeys", self.build)
        self.assertIn("c75BuiltKeys[OpexC69AttemptKey(project)] <- true;", self.task)
        self.assertIn("_recordPortfolioProjectBuilt(project, i, c75BuiltKeys, c69BuiltProjects);", self.build)

    def test_trace_fields_and_no_persistent_pass_state(self):
        logger = self.task.split("function OpexN75C75RefundLog(", 1)[1].split("\n}\n", 1)[0]
        for token in ("C75_REFUND", "year=", "key=", "mode=", "rank=", "profit=",
                      "finance=", "available=", "reason="):
            self.assertIn(token, logger)
        for file in ("ai/OpexAI/persist.nut", "ai/OpexAI/main.nut"):
            self.assertNotIn("n75RefundUsed", source(file))
        self.assertIn("local n75RefundUsed = false;", self.build)
        self.assertNotIn("n75PostRefundBypass", self.persist)

    def test_c77_and_c80_before_any_postrefund_attempt(self):
        self.assertIn("this._ensureSelection();", self.build)
        self.assertIn("this._c83WatchAirSlotTransitions();", self.build)
        self.assertLess(self.build.index("OpexC80ProjectBelowMarginalFloor(this._lines, project)"),
                        self.build.index('"postrefund=attempt"'))
        self.assertIn("this._tryBuildRailProject", self.build)
        self.assertIn("this._tryBuildAirProject", self.build)
        self.assertNotIn('mode == "fleet" ? true', self.build)


if __name__ == "__main__":
    unittest.main()
