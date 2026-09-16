"""Contrats B6: instrumentation passive du classement/capital/cache, sans politique."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"

def read(name):
    return (AI / name).read_text(encoding="utf-8")

def body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1 : pos]
    raise AssertionError(signature)

class TestB6PortfolioCausality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projects = read("projects.nut")
        cls.globals = read("globals_post.nut")

    def test_current_policy_is_observed_not_changed(self):
        self.assertIn("PORTFOLIO_MAX_BATCH <- 1;", self.globals)
        self.assertIn("PORTFOLIO_FLOOR_PCT <- 0;", self.globals)
        select = body(self.projects, "function OpexProjectSelectAffordable(")
        self.assertIn('"fundScore"', select)
        self.assertIn("OpexProjectScore(project.profitAnnual, financeCapital)", select)

    def test_probe_is_decision_log_guarded(self):
        probe = body(self.projects, "function OpexB6LogSelectionCausality(")
        self.assertIn("if (!DECISION_LOG) return;", probe)
        for field in (
            "snapshot_budget=", "live_budget=", "affordability_flips=",
            "actual_profit=", "cf_profit=", "delta_profit=",
            "actual_roi=", "actual_turnover_bonus=", "actual_generation_ratio=",
            "cf_roi=", "cf_turnover_bonus=", "cf_generation_ratio=",
            "actual_age_days=", "actual_recycled=", "pool_recycled=",
        ):
            self.assertIn(field, probe)

    def test_full_build_keeps_snapshot_and_logs_live_comparison_only(self):
        build = body(self.projects, "function OpexBuildProjects(")
        snapshot = build.index("local capitalBudget = OpexAvailableCapital();")
        air = build.index("OpexAirPlans(", snapshot)
        select = build.index("OpexProjectSelectAffordable(", air)
        probe = build.index('OpexB6LogSelectionCausality("build"', select)
        self.assertLess(snapshot, air)
        self.assertLess(air, select)
        self.assertLess(select, probe)
        marker = "local capitalBudget = OpexAvailableCapital();"
        self.assertNotIn(marker, build[snapshot + len(marker) : select])

    def test_incremental_marks_replayed_projects_without_refreshing_economics(self):
        inc = body(self.projects, "function OpexIncrementalUpdateProjects(")
        self.assertIn("local recycledKeys = {};", inc)
        self.assertIn("local recycledKey = OpexProjectAttemptKey(p);", inc)
        self.assertIn('OpexB6LogSelectionCausality("incremental"', inc)
        replay = inc[inc.index("/* 1. Filtrer les candidats existants"):inc.index("/* 2. Injection")]
        self.assertNotIn("economicsDate =", replay)

    def test_economics_age_is_a_measurement_field_only(self):
        make = body(self.projects, "function OpexProjectFromCandidate(")
        self.assertIn("economicsDate = AIDate.GetCurrentDate()", make)
        self.assertEqual(self.projects.count("economicsDate"), 3)

if __name__ == "__main__":
    unittest.main()
