import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
PROJECTS = (ROOT / "ai" / "OpexAI" / "projects.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")


class C111AirC100DecisionShadowTests(unittest.TestCase):
    def test_setting_is_off_by_default_and_loaded(self):
        self.assertIn("C111_AIR_C100_DECISION_SHADOW <- false;", GLOBALS)
        start = INFO.index('name = "c111_air_c100_decision_shadow"')
        snippet = INFO[start:start + 760]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)
        self.assertIn('AIController.GetSetting("c111_air_c100_decision_shadow")', SETTINGS)

    def test_chooser_replays_c100_but_returns_legacy_equipment_and_c68_shadow(self):
        match = re.search(r"function OpexC111ChooseRoutePlane\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("OpexC104BestAirEngine", body)
        self.assertIn("opcodePadding, 0", body)
        self.assertIn("OpexC103ChooseRoutePlane", body)
        self.assertIn("decisionEconomics = decision.economics", body)
        self.assertIn("economics = equipment.economics", body)
        self.assertNotIn("AICompany.GetBankBalance", body)

    def test_full_choice_branch_is_isolated(self):
        full = AIR[AIR.index("function OpexAirChooseRoutePlaneFull("):]
        self.assertIn("if (C111_AIR_C100_DECISION_SHADOW && C72_PLANE_CHOICE == 0", full)
        self.assertIn("return OpexC111ChooseRoutePlane", full)
        self.assertLess(
            full.index("if (C111_AIR_C100_DECISION_SHADOW && C72_PLANE_CHOICE == 0"),
            full.index("if (C82_ENGINE_CALIBRATION || C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY)"),
        )

    def test_plan_comparison_uses_shadow_only_under_c111(self):
        match = re.search(r"function OpexAirPlanBetter\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("if (!C111_AIR_C100_DECISION_SHADOW)", body)
        self.assertIn('"decisionEconomics" in plan', body)
        self.assertIn('"decisionEconomics" in bestPlan', body)

    def test_project_keeps_real_finance_but_shadow_decision_values(self):
        match = re.search(r"function OpexC111ProjectFromAir\(.*?\)(.*?)\n\}", PROJECTS, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("capital = economics.capital", body)
        self.assertIn("budgetCapital = budgetCapital", body)
        self.assertIn("decisionFinanceCapital = decisionBudgetCapital", body)
        self.assertIn("profitAnnual = decisionEconomics.profitAnnual", body)
        self.assertIn("revenueAnnual = decisionEconomics.revenueAnnual", body)
        default = re.search(r"function OpexProjectFromAir\(.*?\)(.*?)\n\}", PROJECTS, re.S)
        self.assertIsNotNone(default)
        self.assertIn("C111_AIR_C100_DECISION_SHADOW", default.group(1))

    def test_affordability_is_real_but_fund_score_uses_shadow_capital(self):
        match = re.search(r"function OpexProjectSelectAffordable\(.*?\)(.*?)\n\}", PROJECTS, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("if (financeCapital > capitalBudget) continue;", body)
        self.assertIn("local decisionFinanceCapital = financeCapital;", body)
        self.assertIn("project.decisionFinanceCapital", body)
        self.assertIn("kDec > decisionFinanceCapital", body)

    def test_shadow_is_propagated_to_all_air_plan_families(self):
        self.assertGreaterEqual(AIR.count("plan.decisionEconomics <-"), 3)
        self.assertIn("decisionLossAnnual", AIR)


if __name__ == "__main__":
    unittest.main()
