import unittest

from sweeps.estim31_real_accounts_from_saves_20261030 import NAMES


class FiscalPostingsDefinition(unittest.TestCase):
    def test_categories_are_net_physical_account_names(self):
        self.assertEqual(len(NAMES), 13)
        self.assertIn('construction_all_modes', NAMES)
        self.assertIn('new_vehicles_net_all_modes', NAMES)
        self.assertIn('other_including_town_actions', NAMES)
        self.assertNotIn('statues_gross_cash', NAMES)
        self.assertNotIn('aircraft_capex_gross', NAMES)


if __name__ == '__main__':
    unittest.main()
