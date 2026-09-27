#!/usr/bin/env python3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
PROJECTS = (ROOT / "ai" / "OpexAI" / "projects.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
TASK_AIR = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")

class C116IncrementalProbeTests(unittest.TestCase):
    def test_probe_is_legacy_only(self):
        start = AIR.index("function OpexC116LegacyIncrementalCandidates(")
        end = AIR.index("function OpexC104FormatAirChoice(", start)
        body = AIR[start:end]
        self.assertIn("OpexAirEconomics(catalog, airport, plane", body)
        self.assertNotIn("forcePhysicalTiming", body)
        self.assertNotIn("forceC100RankReplay", body)

    def test_incremental_gate_uses_kdec(self):
        start = AIR.index("function OpexC116LegacyIncrementalCandidates(")
        end = AIR.index("function OpexC104FormatAirChoice(", start)
        body = AIR[start:end]
        self.assertIn("deltaCapital = legacy.economics.capital - runner.economics.capital", body)
        self.assertIn("if (deltaCapital > kDec) gateChoice = runner;", body)
        self.assertIn("if (kDec > 0)", body)

    def test_opportunity_candidate_walks_legacy_frontier_only(self):
        start = AIR.index("function OpexC116LegacyIncrementalCandidates(")
        end = AIR.index("function OpexC104FormatAirChoice(", start)
        body = AIR[start:end]
        self.assertIn("local opportunityChoice = legacy;", body)
        self.assertIn("while (true)", body)
        self.assertIn("stepProfit.tofloat() / next.economics.profitAnnual.tofloat()", body)
        self.assertIn("stepCapital.tofloat() / kDec.tofloat()", body)
        self.assertIn("relativeProfit < relativeCapital", body)
        self.assertIn("opportunitySteps++", body)
        self.assertNotIn("forcePhysicalTiming", body)
        self.assertNotIn("forceC100RankReplay", body)

    def test_active_setting_is_off_by_default_and_decouples_generation_from_c115(self):
        self.assertIn("C116_AIR_MARGINAL_CAPITAL <- false;", GLOBALS)
        start = INFO.index('name = "c116_air_marginal_capital"')
        snippet = INFO[start:start + 700]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)
        self.assertIn('AIController.GetSetting("c116_air_marginal_capital")', SETTINGS)
        start = AIR.index("function OpexAirChooseRoutePlaneFull(")
        end = AIR.index("function OpexM3ProbeAirEquipment", start)
        body = AIR[start:end]
        c115 = body.index("if (C115_AIR_C100_CAPITAL_REPLAY")
        self.assertIn("!C116_AIR_MARGINAL_CAPITAL", body[c115:])
        self.assertNotIn("OpexC116ChooseBuildPlan", body)
        self.assertNotIn("OpexC116ChooseRoutePlane", body)

        memo_start = AIR.index("function OpexAirChooseRoutePlane(")
        memo_end = AIR.index("function OpexC101ChooseRoutePlane", memo_start)
        memo = AIR[memo_start:memo_end]
        self.assertIn("(C115_AIR_C100_CAPITAL_REPLAY && !C116_AIR_MARGINAL_CAPITAL)", memo)
        self.assertNotIn("|| C116_AIR_MARGINAL_CAPITAL", memo)

    def test_active_build_choice_uses_exact_pending_project_gap(self):
        start = AIR.index("function OpexC116BestPendingAirProject()")
        end = AIR.index("function OpexAirChooseRoutePlaneFull(", start)
        body = AIR[start:end]
        self.assertIn("C116_AIR_PROJECT_SNAPSHOT.unlockable", body)
        self.assertIn("point.hurdle > best.hurdle", body)
        self.assertIn("local target = OpexC116BestPendingAirProject();", body)
        self.assertIn("deltaCapital < target.gap", body)
        self.assertIn("plane.price >= baselinePlane.price", body)
        self.assertIn("economics.profitAnnual > runner.economics.profitAnnual", body)
        self.assertIn("buildPlan.plane = runner.plane", body)
        self.assertIn("buildPlan.economics = runner.economics", body)
        self.assertNotIn("OpexAvailableCapital()", body)
        self.assertNotIn("decisionFinance > available", body)
        self.assertNotIn("marginalRoi", body)
        self.assertNotIn("forcePhysicalTiming", body)
        self.assertNotIn("forceC100RankReplay", body)
        self.assertNotIn("OpexAirPlans", body)

    def test_build_choice_keeps_ranked_plan_immutable_and_retargets_c84(self):
        start = AIR.index("function OpexC116ChooseBuildPlan(")
        end = AIR.index("function OpexAirChooseRoutePlaneFull(", start)
        body = AIR[start:end]
        self.assertIn("local buildPlan = {};", body)
        self.assertIn("foreach (k, v in plan) buildPlan[k] <- v;", body)
        self.assertNotIn("plan.plane = runner.plane", body)
        self.assertNotIn("plan.economics = runner.economics", body)
        self.assertIn("if (C84_AIR_TARGET_FLEET)", body)
        self.assertIn("OpexAirTargetEconomics", body)
        self.assertIn("buildPlan.targetPlanes", body)
        self.assertIn("V92_AIR_SERVICE_CHOICE", body)
        self.assertIn("C85_AIR_EQUIPMENT_FRONTIER", body)

    def test_post_selection_path_uses_build_plan_only_for_execution(self):
        start = TASK_AIR.index("function OpexAI::_tryBuildAirProject(")
        end = TASK_AIR.index("function OpexAirFleetRefusal", start)
        body = TASK_AIR[start:end]
        choose = body.index("local buildChoice = OpexC116ChooseBuildPlan(this._catalog, plan);")
        cash = body.index("local money = AICompany.GetBankBalance", choose)
        build = body.index("OpexBuildAirRoute(this._catalog, this._budget, buildPlan", cash)
        self.assertLess(choose, cash)
        self.assertLess(cash, build)
        self.assertIn("PROJECT_CHOSEN", body)
        self.assertIn("cost=\" + plan.capital", body)
        self.assertIn("AIR_BUILD", body)
        self.assertIn("cost=\" + buildPlan.capital", body)
        self.assertIn("planeId = buildPlan.plane.id", body)
        self.assertIn("refleetEngine = AIVehicle.GetEngineType(result.vehicle)", body)

    def test_active_unlockable_project_lookup_is_cached_only(self):
        start = AIR.index("function OpexC116UnlockedProjectOpportunity(")
        end = AIR.index("function OpexC116ChooseBuildPlan(", start)
        body = AIR[start:end]
        self.assertIn("C116_AIR_PROJECT_SNAPSHOT.unlockable", body)
        self.assertIn("point.gap > deltaCapital", body)
        self.assertNotIn("OpexAirPlans", body)
        self.assertNotIn("OpexAirEconomics", body)

    def test_c104_logs_c116_candidates(self):
        start = AIR.index("function OpexC104ProbeAirEngineCompare(")
        end = AIR.index("function OpexC105ChooseRoutePlane", start)
        body = AIR[start:end]
        for name in ("c116_gate", "c116_score", "c116_marg", "c116_opp"):
            self.assertIn(f'OpexC104FormatAirChoice("{name}"', body)
        self.assertIn("c116_opp_steps=", body)

    def test_project_opportunity_snapshot_reuses_affordable_portfolio(self):
        self.assertIn("C116_AIR_PROJECT_SNAPSHOT <- null;", GLOBALS)
        start = PROJECTS.index("function OpexC116ObserveAirPortfolioOpportunity(")
        end = PROJECTS.index("/* portfolio_v2 : la selection finale.", start)
        body = PROJECTS[start:end]
        insert_start = PROJECTS.index("function OpexC116InsertPortfolioOpportunity(")
        insert_end = start
        insert_body = PROJECTS[insert_start:insert_end]
        self.assertIn("affordable.len()", body)
        self.assertIn("snapshot.air.len() < 3", body)
        self.assertIn("OpexProjectFinanceCapital(project)", body)
        self.assertIn("snapshot.top =", body)
        self.assertIn("top.profitAnnual.tofloat() * 1000.0", body)
        self.assertIn("snapshot.unlockable", body)
        self.assertIn("snapshot.unlockableAny", body)
        self.assertIn("prior.gap <= point.gap && prior.hurdle >= point.hurdle", insert_body)
        self.assertNotIn("OpexAirPlans", body)
        self.assertNotIn("OpexAirEconomics", body)
        select_start = PROJECTS.index("function OpexProjectSelectAffordable(")
        select_end = PROJECTS.index("function OpexProjectSelectionScore(", select_start)
        select_body = PROJECTS[select_start:select_end]
        opportunity = select_body.index("OpexC116ObserveAirPortfolioOpportunity(c116Snapshot, project, financeCapital, capitalBudget);")
        finance_gate = select_body.index("if (financeCapital > capitalBudget) continue;", opportunity)
        self.assertLess(opportunity, finance_gate)
        self.assertIn("OpexC116RememberAirPortfolioOpportunity(affordable, capitalBudget, c116Snapshot);",
                      select_body)

    def test_c104_logs_cached_project_opportunity(self):
        fmt_start = AIR.index("function OpexC116FormatProjectSnapshot(")
        fmt_end = AIR.index("function OpexC104ProbeAirEngineCompare(", fmt_start)
        fmt = AIR[fmt_start:fmt_end]
        best_start = AIR.index("function OpexC116SnapshotBest(")
        best_end = fmt_start
        best = AIR[best_start:best_end]
        self.assertIn("C116_AIR_PROJECT_SNAPSHOT", fmt)
        self.assertIn("c116p_age=", fmt)
        self.assertIn("c116u_gap=", fmt)
        self.assertIn("c116g_gap=", fmt)
        self.assertIn("c116t_hurdle=", fmt)
        self.assertIn("point.gap > deltaCapital", best)
        self.assertIn('"_P="', fmt)
        self.assertIn('"_C="', fmt)
        probe_start = fmt_end
        probe_end = AIR.index("function OpexC105ChooseRoutePlane", probe_start)
        self.assertIn("OpexC116FormatProjectSnapshot(c116.deltaCapital)", AIR[probe_start:probe_end])
        self.assertIn("c116_self_unlock=", AIR[probe_start:probe_end])

    def test_c104_probe_can_observe_real_c115_baseline(self):
        start = AIR.index("if (C115_AIR_C100_CAPITAL_REPLAY")
        end = AIR.index("return OpexC115ChooseRoutePlane", start)
        branch = AIR[start:end]
        self.assertNotIn("!C104_AIR_C100_COMPARE_PROBE", branch)

if __name__ == "__main__":
    unittest.main()
