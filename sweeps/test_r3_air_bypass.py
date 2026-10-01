"""R3 source ordering contracts; the A-B/A-C/D-E scenario still needs NoAI."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TestAirBypass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "ai/OpexAI/task_projects.nut").read_text(encoding="utf-8")
        cls.air = (ROOT / "ai/OpexAI/task_air.nut").read_text(encoding="utf-8")
        start = cls.source.index('if (project.mode == "air"\n        && !OpexAirBatchPlanStillLive(')
        end = cls.source.index("local c121ChainAttempt = false;", start)
        cls.preflight = cls.source[start:end]
        cls.after = cls.source[end:]

    def test_liveness_guard_is_independent_of_c121_and_c75(self):
        condition = self.preflight.split("{", 1)[0]
        self.assertIn("!OpexAirBatchPlanStillLive(project.payload, this._lines)", condition)
        for flag in ("c121FirstYearAirBatch", "C121_", "C75_", "builtCount"):
            self.assertNotIn(flag, condition)

    def test_dead_plan_skips_before_kpass_or_consumption(self):
        self.assertTrue(self.preflight.rstrip().endswith("continue;\n    }"))
        self.assertNotIn("c75BypassConsumed", self.preflight)
        self.assertNotIn("break;", self.preflight)
        self.assertIn("if (projCap >= c75KPass)", self.after)
        self.assertIn("c75BypassConsumed = true;", self.after)

    def test_single_bypass_and_finance_checks_remain(self):
        self.assertEqual(self.source.count("c75BypassConsumed = true;"), 1)
        self.assertIn("local c75BypassConsumed = false;", self.source)
        threshold = self.after.split("if (projCap >= c75KPass)", 1)[1]
        self.assertLess(threshold.index("if (projCap <= availCap)"), threshold.index("c75BypassConsumed = true;"))
        self.assertIn("if (!c75BypassConsumed)", threshold)
        self.assertIn('c75StopReason = (availCap >= 0 && projCap > availCap) ? "cash" : "k_pass";', threshold)

    def test_c121_first_year_policy_and_counter_remain_scoped(self):
        self.assertIn("if (c121FirstYearAirBatch) c121DeadSkipped++;", self.preflight)
        self.assertIn('if (c121FirstYearAirBatch && project.mode == "air")', self.after)
        self.assertIn("c121ChainAttempt = true;", self.after)
        self.assertIn('" dead_skipped=" + c121DeadSkipped', self.after)

    def test_existing_discard_reason_and_probe_gates_are_preserved(self):
        self.assertIn('reason = "batch_plan_dead"', self.preflight)
        self.assertIn('if (AIR_BATCH_TOWN_RESERVE) OpexAirBatchTownReserveNote("batch_plan_dead", 1);', self.preflight)
        for flag in ("DECISION_LOG", "MONTHLY_FUNNEL", "C78_SLOT_INTERCEPT_PROBE", "C120_AIR_TERRITORIAL_RANKING", "C122_AIR_THREAT_PROBE"):
            self.assertIn(flag, self.preflight)

    def test_executor_still_rechecks_live_plan_and_physical_sites(self):
        executor = self.air.split("function OpexAI::_tryBuildAirProject(", 1)[1]
        self.assertIn("!OpexAirBatchPlanStillLive(plan, this._lines)", executor)
        self.assertIn("!OpexAirBatchSiteStillBuildable(plan.siteA", executor)
        self.assertIn("!OpexAirBatchSiteStillBuildable(plan.siteB", executor)
        self.assertIn("OpexAirV92PairBlocked(this._lines, plan)", executor)
        # The early guard reuses town/second-slot/hub/duplicate checks; it is not
        # a replacement implementation of site validation or a new planner.
        live = self.air.split("function OpexAirBatchPlanStillLive(", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("OpexAirC83SecondSlotOpen", live)
        self.assertIn("OpexAirBatchHubHasCapacity", live)
        self.assertIn("line.originA == plan.siteA.town.tile", live)


if __name__ == "__main__":
    unittest.main()