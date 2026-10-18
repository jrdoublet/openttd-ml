import unittest
from rva_company_gain import service_externality


class Network(unittest.TestCase):
    def call(self, **kw):
        inputs=dict(demand_before_month=100, allocation_delta_month=-50,
                    capacity_month=100, waiting=0, horizon_months=12,
                    observed_delivered_month=100, final_receipts_annual=1200)
        inputs.update(kw)
        return service_externality(**inputs)

    def test_fixed_costs_do_not_disappear(self):
        self.assertEqual(self.call()['profit_delta_annual'], -600)

    def test_saturation_and_stock(self):
        self.assertEqual(self.call(demand_before_month=200)['profit_delta_annual'], 0)
        self.assertEqual(self.call(waiting=600)['profit_delta_annual'], 0)

    def test_unknown_is_not_zero(self):
        self.assertIsNone(self.call(final_receipts_annual=None)['revenue_delta_annual'])
        self.assertIsNone(self.call(observed_delivered_month=0)['revenue_delta_annual'])
