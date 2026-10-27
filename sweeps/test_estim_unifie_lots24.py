"""Contrats ESTIM-1 M1/M2/M4/M5: isolation, invariants et parite choix-chantier.

Ces contrats source ne remplacent ni la VM Squirrel ni les portes A/B.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def code(name):
    text = source(name)
    text = re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", text)
    return text


class EstimUnifieLots24(unittest.TestCase):
    def test_switch_and_unchanged_default(self):
        settings = code("settings.nut")
        info = code("info.nut")
        self.assertRegex(info, r'name\s*=\s*"estim_unifie"[\s\S]*?max_value\s*=\s*15')
        self.assertRegex(info, r'name\s*=\s*"estim_unifie"[\s\S]*?default_value\s*=\s*0')
        self.assertIn('GetSetting("estim_unifie")', settings)

    def test_m5_common_cash_contract(self):
        finance = code("projects_finance.nut")
        self.assertIn("function OpexEstimFinanceCapital", finance)
        self.assertIn("factor = RAIL_FINANCE_BIAS_PCT / 100.0;", finance)
        self.assertNotIn("1.063", finance)
        self.assertIn("else if (mode == \"road\") factor = 1.21;", finance)
        self.assertIn("if (!capitalIsActual)", finance)
        self.assertNotIn("function OpexEstimFinanceCashNeeded", finance)
        self.assertNotIn("OpexCashReserve", finance)
        self.assertIn("(ESTIM_UNIFIE & 2) != 0", finance)
        for name in ("task_air.nut", "task_road.nut", "task_rail.nut", "task_water.nut", "air_fleet.nut"):
            with self.subTest(name=name):
                text = code(name)
                self.assertIn("(ESTIM_UNIFIE & 2) != 0", text)
                self.assertIn("OpexEstimFinanceCapital(", text)

    def test_m1_fleet_uses_physical_marginal_components(self):
        catalog = code("air_catalog_c121.nut")
        builder = code("projects_builders.nut")
        models = code("projects_models.nut")
        self.assertIn("next.rawRevenueAnnual - actual.rawRevenueAnnual", catalog)
        self.assertIn("next.runningAnnual - actual.runningAnnual", catalog)
        self.assertIn("next.vehicleAmortAnnual - actual.vehicleAmortAnnual", catalog)
        self.assertIn("estimMarginalBaseVehicles != have", builder)
        self.assertIn("local tranche = clone entry;", builder)
        self.assertIn("tranche.want = 1;", builder)
        self.assertIn("payload = tranche", builder)
        self.assertIn("deltaC = dC, deltaP = dP", builder)
        self.assertIn("local dR = (dRaw.tofloat() * ESTIM_K_R.air).tointeger();", builder)
        self.assertIn("local dP = dR - dE - dA;", builder)
        self.assertIn("deltaR = dR, deltaE = dE, deltaA = dA, deltaC = dC", builder)
        self.assertIn("estimMarginalModeled", models)
        self.assertIn("(ESTIM_UNIFIE & 4) != 0", builder)
        # Palier perime (flotte au-dela du n -> n+1 mesure) : marge historique, pas de blocage.
        self.assertIn("if ((ESTIM_UNIFIE & 4) != 0 && OpexEstimFleetStepCurrent(entry))\n"
                      "    return OpexEstimProjectFromFleet(entry);", builder)
        self.assertIn("line.estimMarginalBaseVehicles == have", builder)

    def test_fleet_fitting_preserves_delta_contract(self):
        selection = code("projects_selection.nut")
        for name in ("deltaR", "deltaE", "deltaA", "deltaC"):
            self.assertIn("fitted." + name + " =", selection)
            self.assertNotIn("fitted." + name + " <-", selection)
        self.assertIn("fitted.deltaP = fitted.deltaR - fitted.deltaE - fitted.deltaA;", selection)
        self.assertIn('OpexEstimFinanceCapital("air", capital, plan.distance', code("task_air.nut"))

    def test_m4_monthly_rate_is_bounded_to_bit_8(self):
        economy = code("economy.nut")
        self.assertIn("return 365.0 / 12.0;", economy)
        self.assertIn("(ESTIM_UNIFIE & 8) != 0 ? OpexEstimDaysPerMonth() : legacyDays", economy)
        self.assertIn("OpexEstimRivalAvailableMonthly", economy)
        self.assertIn("(100 - transportedPercent) / 100.0", economy)
        self.assertIn("OpexEstimRailPhysicalTrainCap", economy)
        self.assertIn("OpexEstimMonthDays(30.4)", code("air_economics_c121.nut"))
        self.assertIn("OpexEstimMonthDays(30.4)", code("air_trip.nut"))
        self.assertIn("OpexEstimRivalAvailableMonthly", code("candidates.nut"))
        self.assertIn("(ESTIM_UNIFIE & 8) != 0", code("air_engine_choice.nut"))


if __name__ == "__main__":
    unittest.main()
