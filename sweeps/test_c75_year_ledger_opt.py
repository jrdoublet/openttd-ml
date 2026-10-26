"""C75: l'expérience de suppression des seuls compteurs annuels reste OFF au défaut."""

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class C75YearLedgerOptContracts(unittest.TestCase):
    def test_opt_in_off_in_all_four_profiles(self):
        info = source("info.nut")
        block = re.search(
            r'AddSetting\(\{ name = "c75_year_ledger_skip",.*?\}\);', info, re.S
        )
        self.assertIsNotNone(block)
        self.assertEqual(info.count('name = "c75_year_ledger_skip"'), 1)
        for profile in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(), rf"{profile}_value\s*=\s*0\b")
        self.assertEqual(
            source("settings.nut").count('GetSetting("c75_year_ledger_skip")'), 1
        )
        self.assertIn("C75_YEAR_LEDGER_SKIP <- false;", source("globals_pre.nut"))

    def test_only_diagnostic_consumers_can_be_elided(self):
        probes = source("probes.nut")
        start = probes.index("function OpexC75ResetYearLedger()")
        end = probes.index("function OpexC75BypassResetYearLedger(", start)
        reset = probes[start:end]
        self.assertIn(
            "if (C75_YEAR_LEDGER_SKIP && !C49_SCARCITY_LEDGER && !C69_BOTTLENECK_PROBE)",
            reset,
        )
        self.assertLess(reset.index("C75_YEAR_LEDGER = null;"), reset.index("return;"))
        self.assertLess(reset.index("return;"), reset.index("C75_YEAR_LEDGER = {"))
        self.assertIn("C75_YEAR_LEDGER != null", source("task_projects.nut"))
        self.assertIn("C75_YEAR_LEDGER != null", source("scheduler_tasks.nut"))
        self.assertIn("!C69_BOTTLENECK_PROBE || C75_YEAR_LEDGER == null", probes)

    def test_k_pass_and_bypass_keep_their_state(self):
        probes = source("probes.nut")
        self.assertIn("C75_PASS_DATES.append(now);", probes)
        self.assertIn("N = C75_PASS_DATES.len();", probes)
        self.assertIn("function OpexC75ComputeKPass(", probes)
        self.assertIn("function OpexC75BypassResetYearLedger(", probes)
        projects = source("task_projects.nut")
        self.assertIn("OpexC75RecordPassDate(now);", projects)
        self.assertIn("c75KPassData = OpexC75ComputeKPass(now);", projects)
        self.assertIn("OpexC75BypassEnsureYear(year);", projects)
        persist = source("persist.nut")
        self.assertIn("c75PassDates = C75_PASS_DATES,", persist)
        self.assertIn("C75_PASS_DATES = this._reloadC75PassDates;", persist)
        self.assertNotIn("c75YearLedger =", persist)
        self.assertNotIn("C75_YEAR_LEDGER =", persist)

    def test_both_resets_use_the_same_guard(self):
        self.assertIn("OpexC75ResetYearLedger();", source("settings.nut"))
        self.assertIn("OpexC75ResetYearLedger();", source("main.nut"))
        self.assertIn("OpexC75ResetYearLedger();", source("probes.nut"))


if __name__ == "__main__":
    unittest.main()
