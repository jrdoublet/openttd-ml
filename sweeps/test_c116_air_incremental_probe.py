#!/usr/bin/env python3
import unittest
from pathlib import Path
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air
from opex_projects_source import read_projects_source

ROOT = Path(__file__).resolve().parents[1]
AIR = read_builder_air()
PROJECTS = read_projects_source()
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

    def test_post_selection_path_uses_build_plan_only_for_execution(self):
        start = TASK_AIR.index("function OpexAI::_tryBuildAirProject(")
        end = TASK_AIR.index("function OpexAirFleetRefusal", start)
        body = TASK_AIR[start:end]
        choose = body.index("local buildPlan = plan;")
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

    def test_c104_logs_c116_candidates(self):
        start = AIR.index("function OpexC104ProbeAirEngineCompare(")
        end = AIR.index("\nfunction ", start + 1)
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
        probe_end = AIR.index("\nfunction ", probe_start + 1)
        self.assertIn("OpexC116FormatProjectSnapshot(c116.deltaCapital)", AIR[probe_start:probe_end])
        self.assertIn("c116_self_unlock=", AIR[probe_start:probe_end])

    def test_c104_probe_can_observe_real_c115_baseline(self):
        start = AIR.index("if (C115_AIR_C100_CAPITAL_REPLAY")
        end = AIR.index("return OpexC115ChooseRoutePlane", start)
        branch = AIR[start:end]
        self.assertNotIn("!C104_AIR_C100_COMPARE_PROBE", branch)

if __name__ == "__main__":
    unittest.main()
