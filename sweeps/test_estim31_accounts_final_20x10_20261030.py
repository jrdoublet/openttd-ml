import unittest

from sweeps.estim31_real_accounts_from_saves_20261030 import NAMES
from sweeps.estim31_top3_20x10_20261030 import SEEDS20


class ActualFiscalAccounting(unittest.TestCase):
    def test_only_net_real_postings_supported(self):
        self.assertEqual(len(SEEDS20), 20)
        self.assertEqual(len(NAMES), 13)
        self.assertIn('construction_all_modes', NAMES)
        self.assertIn('new_vehicles_net_all_modes', NAMES)
        self.assertIn('other_including_town_actions', NAMES)
        self.assertNotIn('air_engine_223_gross_purchases', NAMES)


if __name__ == '__main__':
    unittest.main()
