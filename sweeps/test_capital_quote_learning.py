"""P0 devis de capital : contrats du module Squirrel (compilation moteur distincte).

Ces gardes ciblent les regressions constatees en revue : devis initial perdu
apres plan, N de vehicules modifie, biais ROAD 121 et reserves AIR melanges,
et bascule de sauvegarde apres une partie.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (ROOT / name).read_text(encoding="utf-8")


class CapitalQuoteContracts(unittest.TestCase):
    def test_default_off_and_order(self):
        info = source("info.nut")
        match = re.search(r'name = "capital_quote_learning",(.*?)\}\);', info, re.S)
        self.assertIsNotNone(match)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(match.group(1), rf"\b{key}\s*=\s*0\b")
        self.assertIn('CAPITAL_QUOTE_LEARNING <- false;', source("capital_quote_learning.nut"))
        self.assertIn(
            'CAPITAL_QUOTE_LEARNING = AIController.GetSetting("capital_quote_learning") != 0;',
            source("settings.nut"),
        )
        load = source("projects.nut")
        self.assertLess(load.index('require("capital_quote_learning.nut")'),
                        load.index('require("projects_finance.nut")'))

    def test_original_policy_only_off_and_risk_separate(self):
        financing = source("projects_finance.nut")
        self.assertLess(financing.index("if (CAPITAL_QUOTE_LEARNING) return"),
                        financing.index("else if (project.mode == \"road\") biasPct = 121;"))
        learning = source("capital_quote_learning.nut")
        self.assertIn("project.budgetCapital - construction", learning)
        self.assertIn("construction + nonConstruction", learning)
        self.assertIn("project.payload.capital", learning)
        self.assertIn("s.actual.tofloat() / s.quoted.tofloat()", learning)
        self.assertIn("if (!CAPITAL_QUOTE_LEARNING) return 1.0;", learning)
        self.assertIn("return 1.0;", learning)
        self.assertNotIn("30000", learning)
        self.assertNotIn("12000", learning)

    def test_air_simulation_is_not_real_spend(self):
        air = source("air_construction.nut")
        self.assertIn(
            "(AIR_SITE_COST_QUOTE || PROBE_AIR_FINANCE_MARGIN || CAPITAL_QUOTE_LEARNING)",
            air,
        )
        task = source("task_air.nut")
        self.assertEqual(task.count('OpexCapitalQuoteObserve("air",'), 2)
        self.assertIn('quotePlanes = ("planes" in plan) ? plan.planes : 1;', task)
        self.assertIn('quotePlanes = ("planes" in buildPlan) ? buildPlan.planes : 1;', task)
        learning = source("capital_quote_learning.nut")
        self.assertIn("result.vehicles.len() == expectedPlanes", learning)
        self.assertIn('family = "air|" + newAirports + "|planes=" + expectedPlanes;', learning)

    def test_rail_and_road_quote_before_vehicle_reselection(self):
        rail = source("builder_rail.nut")
        self.assertIn("candidate.preCapital <- candidate.capital;", rail)
        self.assertIn("candidate.preQuoteTrains <- candidate.trains;", rail)
        self.assertLess(rail.index("candidate.preQuoteTrains <- candidate.trains"),
                        rail.index("OpexApplyRailEconomics(candidate, economics);"))
        task_rail = source("task_rail.nut")
        self.assertIn('OpexCapitalQuoteObserve("rail", candidate, result, preQuote, -1, preTrains);',
                      task_rail)
        road = source("task_road.nut")
        self.assertLess(road.index("preQuoteRoadVehicles ="), road.index("OpexApplyRoadEconomics(candidate"))
        self.assertIn('OpexCapitalQuoteObserve("road", project, result, project.capital, -1, preQuoteRoadVehicles);',
                      road)
        self.assertLess(road.index("local revisedNeed ="), road.index("OpexBuildRoadRoute(this._catalog"))
        learning = source("capital_quote_learning.nut")
        self.assertIn('family = mode + "|" + kind + "|vehicles=" + expectedVehicles;', learning)

    def test_water_accounting_and_fallback_is_censored(self):
        water = source("builder_water.nut")
        self.assertIn("(C63_INVEST_PROBE || CAPITAL_QUOTE_LEARNING) ? AIAccounting()", water)
        self.assertIn('OpexCapitalQuoteObserve("water", project, result, project.capital);',
                      source("task_water.nut"))
        self.assertIn("AIVehicle.GetEngineType(result.vehicle)", source("capital_quote_learning.nut"))

    def test_failures_not_learned_and_persistence_both_versions(self):
        learning = source("capital_quote_learning.nut")
        self.assertIn("if (success && comparable && quote > 0 && actual > 0 && distance >= 0)",
                      learning)
        self.assertIn("} else if (!success) {", learning)
        self.assertIn("sample.failed++", learning)
        persist = source("persist.nut")
        self.assertEqual(
            persist.count("capitalQuoteLearning <- OPEX_CAPITAL_QUOTE_SAMPLES"), 2)
        self.assertIn('OpexCapitalQuoteLoad(("capitalQuoteLearning" in data)', persist)

    def test_rail_factor_effective_100(self):
        self.assertIn("RAIL_TERRAIN_FACTOR <- 100;", source("economy.nut"))
        self.assertIn("if (rtf > 0) RAIL_TERRAIN_FACTOR = rtf;", source("settings.nut"))
        setting = re.search(r'name = "rail_terrain_factor",(.*?)\}\);',
                            source("info.nut"), re.S)
        self.assertIsNotNone(setting)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(setting.group(1), rf"\b{key}\s*=\s*100\b")

    def test_air_decision_quote_components(self):
        builders = source("projects_builders.nut")
        self.assertEqual(builders.count("decisionConstructionCapital = useInitialProjectEconomics"), 2)
        finance = source("capital_quote_learning.nut")
        self.assertIn('decisionFinance - decisionConstruction', finance)
        self.assertIn('OpexCapitalQuoteAlternativeFinance(project, economics, finance)', source("projects_finance.nut"))
        selection = source("projects_selection.nut")
        self.assertEqual(selection.count('OpexCapitalQuoteDecisionFinance(project, project.decisionFinanceCapital)'), 2)


if __name__ == "__main__":
    unittest.main()
