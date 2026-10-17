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


if __name__ == "__main__":
    unittest.main()
