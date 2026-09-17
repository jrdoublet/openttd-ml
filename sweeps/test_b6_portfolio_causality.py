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
            "live_selected=", "live_profit=", "live_cap=", "same_live_choice=",
            "live_profit_delta=", "actual_live_affordable=",
            "actual_roi=", "actual_turnover_bonus=", "actual_generation_ratio=",
            "cf_roi=", "cf_turnover_bonus=", "cf_generation_ratio=",
            "actual_age_days=", "actual_recycled=", "pool_recycled=",
        ):
            self.assertIn(field, probe)
        self.assertIn("local copied = clone p;", probe)
        self.assertIn("OpexProjectSelectAffordable(", probe)
        self.assertIn("liveAlternatives, liveBudget, PORTFOLIO_MAX_BATCH", probe)

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
        for signature in (
            "function OpexProjectFromFleet(",
            "function OpexProjectFromAir(",
            "function OpexProjectFromWater(",
        ):
            self.assertIn("economicsDate = AIDate.GetCurrentDate()", body(self.projects, signature))

    def test_0611_fresh_equivalence_is_passive_and_fail_closed(self):
        probe = body(self.projects, "function OpexB6LogFreshEquivalence(")
        self.assertIn("if (!DECISION_LOG", probe)
        self.assertIn("OpexB6FreshBucket(staleProjects.candidateGroups, true)", probe)
        self.assertIn("oldList.len() != 1", probe)
        self.assertIn("freshList.len() != 1", probe)
        self.assertIn('OpexDecide("B6_FRESH_EQ"', probe)
        self.assertIn('OpexDecide("B6_FRESH_TOP"', probe)
        self.assertNotIn("OpexProjectRememberAll(", probe)
        self.assertNotIn("OpexProjectSelectAffordable(", probe)

        bucket = body(self.projects, "function OpexB6FreshBucket(")
        self.assertIn("function OpexB6FreshBucket(groups, recycledOnly = false)", self.projects)
        self.assertIn("b6RecycledSinceFresh", bucket)

        inc = body(self.projects, "function OpexIncrementalUpdateProjects(")
        replay = inc[inc.index("/* 1. Filtrer les candidats existants"):inc.index("/* 2. Injection")]
        self.assertIn("if (DECISION_LOG) p.b6RecycledSinceFresh <- true;", replay)

        task_projects = read("task_projects.nut")
        rebuild = body(task_projects, "function OpexAI::_rebuildProjects(")
        stale = rebuild.index("local b6StaleProjects")
        build = rebuild.index("this._projects = OpexBuildProjects(")
        compare = rebuild.index("OpexB6LogFreshEquivalence(", build)
        self.assertLess(stale, build)
        self.assertLess(build, compare)
        self.assertIn("stage == OPEX_STAGE_COMPLETE", rebuild[build:compare + 100])

    def test_0611_reprices_only_recycled_freight_top_for_measurement(self):
        helper = body(self.projects, "function OpexB6LogRepricedFreightTop(")
        self.assertIn("if (!DECISION_LOG", helper)
        self.assertIn("funded[0]", helper)
        self.assertIn("if (!(key in recycledKeys)) return;", helper)
        self.assertIn('project.kind != "freight"', helper)
        self.assertIn('OpexDecide("B6_RECYCLE_TOP_PRICE"', helper)
        self.assertIn('decision = "change_rank"', helper)
        self.assertIn('decision = "change_unaffordable"', helper)
        self.assertIn('decision = "change_not_generated"', helper)
        self.assertIn('OpexProjectSelectionScore(runner, "fundScore")', helper)
        self.assertNotIn("OpexProjectRememberAll(", helper)
        self.assertNotIn("OpexProjectSelectAffordable(", helper)

        reprice = body(self.projects, "function OpexB6RepriceFreightTop(")
        self.assertIn("AIIndustry.GetLastMonthProduction", reprice)
        self.assertIn('cand.placeJoin.candidateEnd == "A"', reprice)
        self.assertIn("OpexOriginService(lines, cand.src)", reprice)
        self.assertIn("service.line.srcIndustry", reprice)
        self.assertIn("OpexLineEconomics(", reprice)
        self.assertIn("OpexRoadLineEconomics(", reprice)
        self.assertIn("cand.isTransformer", reprice)

if __name__ == "__main__":
    unittest.main()
