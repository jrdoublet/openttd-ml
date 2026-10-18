"""RVA-09, ledger identities and missing-data boundaries, no economic claim."""
import copy
import unittest
from rva_company_gain import company_gain, comparable_alternatives


class CompanyGain(unittest.TestCase):
    def line(self):
        return {"context": {"fingerprint": "fixture", "horizon": "terminal_economy_year",
                            "currency": "GBP", "annual_clock": "economy"},
                "revenue_basis": "final_company_receipts", "demand_basis": "physical_line_demand",
                "revenue_annual": 100, "running_annual": 20, "amort_annual": 10,
                "capital_required": 500, "line_demand": {"a": 100, "b": 80}, "corrections": {}}

    def effect(self, line, revenue=-50, costs=0):
        return {"service_id": "air-existing", "context": line["context"],
                "revenue_delta_annual": revenue, "avoidable_cost_delta_annual": costs,
                "source": "fixture_counterfactual_prediction"}

    def test_cannibalization_reduces_gain_without_reducing_physical_demand(self):
        line = self.line()
        before = copy.deepcopy(line)
        result = company_gain(line, [self.effect(line)], affected_inventory_complete=True)
        self.assertEqual(result["profit_line_annual"], 70)
        self.assertEqual(result["gain_company_annual"], 20)
        self.assertEqual(result["line_demand"], {"a": 100, "b": 80})
        self.assertEqual(result["capital_required"], 500)
        self.assertFalse(result["causal_measurement"])
        self.assertEqual(line, before)

    def test_only_explicit_avoidable_cost_savings_enter_gain(self):
        line = self.line()
        result = company_gain(line, [self.effect(line, costs=-10)], affected_inventory_complete=True)
        self.assertEqual(result["network_delta_annual"], -40)
        self.assertEqual(result["gain_company_annual"], 30)
        positive = company_gain(line, [self.effect(line, revenue=5)], affected_inventory_complete=True)
        self.assertEqual(positive["gain_company_annual"], 75)

    def test_unknown_effect_and_incomplete_inventory_are_not_zero(self):
        line = self.line()
        for effects, complete in (([self.effect(line, revenue=None)], True), ([], False),
                                  ([self.effect(line, revenue=float("nan"))], True)):
            result = company_gain(line, effects, affected_inventory_complete=complete)
            self.assertEqual(result["profit_line_annual"], 70)
            self.assertIsNone(result["gain_company_annual"])
        self.assertEqual(company_gain(line, [], affected_inventory_complete=True)["gain_company_annual"], 70)

    def test_no_transfer_receipts_or_second_correction_of_same_field(self):
        for field, value in (("revenue_basis", "transfer_credit"),
                             ("demand_basis", "V216a_net_scaled"),
                             ("corrections", {"revenue_annual": ["V212", "RVA"]})):
            line = self.line(); line[field] = value
            with self.assertRaises(ValueError):
                company_gain(line, [], affected_inventory_complete=True)

    def test_duplicate_services_and_different_horizon_refused(self):
        line = self.line(); effect = self.effect(line)
        with self.assertRaises(ValueError):
            company_gain(line, [effect, effect], affected_inventory_complete=True)
        effect = copy.deepcopy(effect); effect["context"]["horizon"] = "different"
        with self.assertRaises(ValueError):
            company_gain(line, [effect], affected_inventory_complete=True)

    def test_rail_net_and_air_gross_not_comparable(self):
        context = self.line()["context"]
        rail = {"project_id": "rail", "context": context, "profit_basis": "net_company_contribution",
                "gain_company_annual": 20}
        air = dict(rail, project_id="air", profit_basis="line_profit")
        self.assertFalse(comparable_alternatives([rail, air])["comparable"])
        air["profit_basis"] = "net_company_contribution"
        self.assertTrue(comparable_alternatives([rail, air])["comparable"])
        air["gain_company_annual"] = None
        self.assertFalse(comparable_alternatives([rail, air])["comparable"])
