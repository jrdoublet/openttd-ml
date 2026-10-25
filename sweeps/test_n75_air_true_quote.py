"""N75: experimental early AIR 1->2 finance quote, not a growth unlock.

Static contract tests. The NoAI Squirrel compiler and actual purchasing must
also be checked through a paired OpenTTD smoke and exposed engine events.
"""
import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class TestN75TrueQuote(unittest.TestCase):
    def test_public_setting_opt_in_only(self):
        info = read("info.nut")
        block = re.search(r'AddSetting\(\{ name = "n75_air_true_quote",.*?\}\);', info, re.S)
        self.assertIsNotNone(block)
        self.assertIn("min_value = 0, max_value = 2", block.group())
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{difficulty}_value = 0", block.group())
        self.assertEqual(info.count('name = "n75_air_true_quote"'), 1)
        self.assertEqual(read("settings.nut").count('GetSetting("n75_air_true_quote")'), 1)
        self.assertIn("N75_AIR_TRUE_QUOTE <- 0;", read("globals_pre.nut"))

    def test_early_only_and_single_initial_aircraft(self):
        air = read("task_air.nut")
        guard = "if (N75_AIR_TRUE_QUOTE > 0 && plan != null && c121BelowTarget"
        self.assertIn(guard, air)
        self.assertIn("have == 1 && n75OldEngine >= 0", air)
        self.assertIn("year >= OPEX_START_YEAR && year <= OPEX_START_YEAR + 2", air)
        self.assertLess(air.index("if (have >= physicalMaxPlanes)"), air.index(guard))
        self.assertLess(air.index("if ((\"deadStreak\" in line) && line.deadStreak >= 2)"), air.index(guard))

    def test_correct_engine_price_during_shadow_and_on(self):
        air = read("task_air.nut")
        self.assertIn("OpexAirBestEngineForLine(line, this._catalog)", air)
        self.assertIn("targetPrice = AIEngine.GetPrice(targetEngine)", air)
        self.assertIn("if (N75_AIR_TRUE_QUOTE == 2) planePrice = n75NewQuote;", air)
        self.assertIn("N75_AIR_TRUE_QUOTE_CACHE_MONTH != monthKey", air)
        self.assertIn("N75_AIR_TRUE_QUOTE_CACHE.rawset(cacheKey, cachedQuote);", air)
        self.assertIn("local fleetEntry = { line = line, want = want, planePrice = planePrice, baseVehicles = have };", air)
        self.assertIn("fleetEntry.n75QuoteOld <- n75OldQuote", air)
        self.assertIn("fleetEntry.n75QuoteNew <- n75NewQuote", air)
        self.assertIn("OpexDecide(\"N75_QUOTE\", \"phase=plan", air)
        self.assertIn("OpexDecide(\"N75_QUOTE\", \"phase=execute", read("task_projects.nut"))

    def test_same_real_purchase_engine_and_live_cash_guard(self):
        real = read("air_fleet.nut")
        self.assertIn("local candidate = OpexAirBestEngineForLine(line, catalog);", real)
        self.assertIn("local price = AIEngine.GetPrice(targetEngine);", real)
        self.assertIn("local need = price + OpexCashReserve() + 1000;", real)
        self.assertIn("if (money < need)", real)
        self.assertIn('result.reason = "N75_FALLBACK_CASH"', real)
        self.assertIn("fallbackPrice + OpexCashReserve() + 1000", real)
        self.assertIn("n75PriceGuard = false", real)
        self.assertIn('N75_AIR_TRUE_QUOTE == 2 && ("n75QuoteEngine" in entry)', read("task_projects.nut"))
        builder = read("projects_builders.nut")
        self.assertIn("local capital = entry.planePrice * entry.want;", builder)
        self.assertIn("budgetCapital = capital + 1000", builder)
        self.assertIn("profitAnnual = profit", builder)
        selection = read("projects_selection.nut")
        self.assertIn("OpexProjectDefensiveAirPriority", selection)
        self.assertIn("OpexProjectFinanceCapital(project)", selection)
        projects = read("task_projects.nut")
        self.assertIn("OpexC80ProjectBelowMarginalFloor", projects)
        self.assertIn("OpexC75ComputeKPass", projects)

    def test_no_new_persistent_mutable_state(self):
        for name in ("persist.nut", "main.nut", "scheduler.nut", "orchestrator.nut"):
            self.assertNotIn("N75_AIR_TRUE_QUOTE", read(name))
            self.assertNotIn("n75Quote", read(name))


if __name__ == "__main__":
    unittest.main()
