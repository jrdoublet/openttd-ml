"""V309 étape 1 : contrats de la sonde passive (sans moteur).

Avant l'implémentation, les assertions statiques sont intentionnellement rouges ;
une fois le code intégré, elles doivent vérifier les deux boucles et le défaut 0.
"""

from pathlib import Path
import gzip
import math
import re
import tempfile
import unittest

from sweeps.diag_v309_idle import read_idle_logs


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(file):
    return (AI / file).read_text(encoding="utf-8")


def wait_days(minimum_cost: int, balance: int, monthly_net: int):
    """Équivalent Python du nombre de jours jusqu'à financement (30j/mois)."""
    if minimum_cost <= balance:
        return 0
    if monthly_net <= 0:
        return None
    return math.ceil((minimum_cost - balance) * 30 / monthly_net)


def cartography_blocks(idle_ops: int):
    return max(0, idle_ops) // 430


class TestV309Idle(unittest.TestCase):
    def test_reader_keeps_arms_seeds_and_missing_wait_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "reference_seed42_r0.log").write_text(
                "[0] [I] OPEX 1970-1-1 V309_IDLE loops=7 useless=4 "
                "useless_ops=860 sleep_ops=430 wait_days=-1 blocks=3 cash_below_days=3 "
                "unknown_cost_loops=1 unfunded_cost_loops=5 stable_unfunded_loops=3 "
                "stable_unfunded_ops=250 cost_source=unfunded_snapshot wait_capped=0\n"
                "[0] [I] OPEX 1970-2-1 V309_IDLE loops=3 useless=2 "
                "useless_ops=430 sleep_ops=430 wait_days=60 blocks=2 cash_below_days=2 "
                "unknown_cost_loops=0 unfunded_cost_loops=2 stable_unfunded_loops=1 "
                "stable_unfunded_ops=100 cost_source=unfunded_snapshot wait_capped=1\n",
                encoding="utf-8")
            (path / "v309_idle_seed42_r0.log").write_text(
                "[0] [I] OPEX 1970-1-1 V309_IDLE loops=5 useless=1 "
                "useless_ops=100 sleep_ops=500 wait_days=15 blocks=1\n", encoding="utf-8")
            result = read_idle_logs(path)
        self.assertEqual(result["reference"][1970]["months"], 2)
        self.assertEqual(result["reference"][1970]["useless_pct"], 60.0)
        self.assertEqual(result["reference"][1970]["unavailable_waits"], 1)
        self.assertEqual(result["reference"][1970]["wait_days_mean"], 60)
        self.assertEqual(result["reference"][1970]["cash_below_days"], 5)
        self.assertEqual(result["reference"][1970]["unknown_cost_loops"], 1)
        self.assertEqual(result["reference"][1970]["unfunded_cost_loops"], 7)
        self.assertEqual(result["reference"][1970]["stable_unfunded_loops"], 4)
        self.assertEqual(result["reference"][1970]["stable_unfunded_ops"], 350)
        self.assertEqual(result["reference"][1970]["capped_wait_months"], 1)
        self.assertEqual(result["v309_idle"][1970]["loops"], 5)
        self.assertIsNone(result["v309_idle"][1970]["cash_below_days"])
        self.assertIsNone(result["v309_idle"][1970]["unknown_cost_loops"])
        self.assertIsNone(result["v309_idle"][1970]["stable_unfunded_loops"])

    def test_duplicate_monthly_flushed_log_does_not_inflate_counters(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "v309_idle_seed42_r0.log"
            row = ("OPEX 1970-3-1 V309_IDLE loops=10 useless=2 useless_ops=300 "
                   "sleep_ops=400 blocks=1 wait_days=15 stable_unfunded_loops=5 "
                   "stable_unfunded_ops=900\n")
            log.write_text(row + row, encoding="utf-8")
            with gzip.open(str(log) + ".gz", "wt", encoding="utf-8") as gz:
                gz.write(row)
            actual = read_idle_logs(tmp)["v309_idle"][1970]
        self.assertEqual(actual["months"], 1)
        self.assertEqual(actual["loops"], 10)
        self.assertEqual(actual["stable_unfunded_loops"], 5)
        self.assertEqual(actual["stable_unfunded_ops"], 900)

    def test_cash_gap_converts_to_days_without_divide_by_zero(self):
        self.assertEqual(wait_days(30000, 45000, 4000), 0)
        self.assertEqual(wait_days(30000, 20000, 10000), 30)
        self.assertEqual(wait_days(30000, 20000, 3000), 100)
        self.assertIsNone(wait_days(30000, 20000, 0))
        self.assertIsNone(wait_days(30000, 20000, -1))

    def test_v308_theoretical_conversion(self):
        self.assertEqual(cartography_blocks(429), 0)
        self.assertEqual(cartography_blocks(430), 1)
        self.assertEqual(cartography_blocks(860), 2)
        self.assertEqual(cartography_blocks(-20), 0)

    def test_setting_off_in_all_difficulties_and_read_once(self):
        info = source("info.nut")
        self.assertNotIn('name = "v309_idle_probe"', info)
        self.assertIn('V309_IDLE_PROBE = OpexProbeEnabled(67108864);', source("settings.nut"))
        self.assertIn("V309_IDLE_PROBE <- false", source("globals_pre.nut"))

    def test_tick_hook_in_both_loops_with_no_default_side_effects(self):
        main_loop = source("main.nut").rsplit("while (true) {", 1)[-1]
        profiled_loop = source("probes.nut").split(
            "function OpexAI::_mainLoopProfiled()", 1)[1].split("/* probe_span_trace", 1)[0]
        for loop in (main_loop, profiled_loop):
            self.assertEqual(loop.count("if (V309_IDLE_PROBE) OpexV309IdleBegin();"), 1)
            self.assertEqual(loop.count("if (V309_IDLE_PROBE) OpexV309IdleTick(this);"), 1)
            self.assertLess(loop.index("OpexV309IdleBegin()"), loop.index("OpexV309IdleTick(this)"))
            self.assertLess(loop.index("OpexV309IdleTick(this)"), loop.index("AIController.Sleep(1)"))

    def test_probe_log_and_no_score_changes(self):
        probe = source("probes.nut")
        self.assertIn("V309_IDLE", probe)
        self.assertIn("AIController.GetOpsTillSuspend", probe)
        self.assertIn("_projects", probe)
        self.assertIn("OPEX_LINES_REVISION", probe)
        self.assertIn("OPEX_ABANDON_REVISION", probe)
        self.assertIn("OpexProjectFinanceCapital", probe)
        self.assertIn("AICompany.GetQuarterlyIncome", probe)
        self.assertIn("AICompany.GetQuarterlyExpenses", probe)
        self.assertIn("cash_below_days=", probe)
        self.assertIn('"nextProjectCapital" in stats', probe)
        self.assertIn('"minCapital" in stats', probe)
        self.assertIn('minCost > portfolio.capitalBudget', probe)
        self.assertIn('source = "unfunded_snapshot"', probe)
        self.assertIn('source = "unknown"', probe)
        self.assertIn('unknown_cost_loops=', probe)
        self.assertIn('unfunded_cost_loops=', probe)
        self.assertIn('stable_unfunded_loops=', probe)
        self.assertIn('stable_unfunded_ops=', probe)

    def test_probe_uses_safe_relative_clock_and_caches_portfolio_scan(self):
        probe = source("probes.nut")
        part = probe.split("function OpexV309IdleBegin()", 1)[1].split(
            "/* Sonde probe_loop_ops", 1)[0]
        self.assertIn("state.mark = OpexOpsMeasureBegin();", part)
        self.assertIn("OpexOpsMeasureEnd(state.mark)", part)
        self.assertNotIn("OpexOpsClock()", part)
        projects = probe.split("function OpexV309IdleProjects", 1)[1].split(
            "function OpexV309IdleMonthlyNet", 1)[0]
        self.assertIn("state.cachedSelectStamp == SELECT_BISECT_STAMP", projects)
        self.assertIn("state.cachedBestCount == count", projects)
        self.assertIn("state.cachedHead == head", projects)
        self.assertIn("return state.cachedProject;", projects)
        self.assertIn("if (days > 36500.0)", part)
        self.assertIn('state.priorSource == "unfunded_snapshot"', part)
        self.assertIn('projects.cost == state.priorCost', part)
        self.assertIn('projects.cost.tofloat() - cash.tofloat()', part)
        self.assertIn("state.waitCapped = 1;", part)
        self.assertLess(part.index("state.waitCapped = 1"),
                        part.index("state.sleepOps += AIController.GetOpsTillSuspend()"))


if __name__ == "__main__":
    unittest.main()
