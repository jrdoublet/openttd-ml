import unittest

from sweeps.estim31_accounts_compact_20261030 import compact
from sweeps.estim31_real_accounts_from_saves_20261030 import NAMES


class CompactPostedAccounting(unittest.TestCase):
    def test_net_categories_keep_sign_and_do_not_invent_mode_allocations(self):
        r = {'campaign': 'fixture', 'source_manifest': 'fixture.json',
             'source_archive': 'fixture_saves', 'games': 80,
             'checkpoints': 40, 'cutoff': '1974-12-01', 'summary_means_40': {},
             'period_records': [
                 {'policy': 'variant', 'company': 'OpexAI',
                  'checkpoint_date': '1974-12-01', 'accounting_year': 1974,
                  'ytd_net_by_category': dict.fromkeys(NAMES, 100),
                  'physical_new_vehicle_ids_at_checkpoint': {'air:engine=223': 2}}
                 for _ in range(40)]}
        result = compact(r)
        self.assertEqual(result['yearly_dec1_ytd_net_account_means_40']
                         ['1974:variant:OpexAI']['construction_all_modes'], 100)
        self.assertEqual(result['physically_observed_minimum_air_entry_ids']
                         ['1974:variant:engine=223'], 80)
        self.assertNotIn('construction_air_only',
                         result['yearly_dec1_ytd_net_account_means_40']['1974:variant:OpexAI'])


if __name__ == '__main__':
    unittest.main()
