import unittest
from datetime import date

from sweeps.estim31_real_accounts_from_saves_20261030 import NAMES,accounting_year,diff_accounts


class ActualNetExpenseContract(unittest.TestCase):
    def test_new_year_first_month_resets_only_for_new_accounting_year(self):
        rows=[dict(game_index=0,seed=999,policy='reference',company='OpexAI',
                   date=date(1970,12,1),cumulative=[100]*13),
              dict(game_index=0,seed=999,policy='reference',company='OpexAI',
                   date=date(1971,1,1),cumulative=[140]*13),
              dict(game_index=0,seed=999,policy='reference',company='OpexAI',
                   date=date(1971,2,1),cumulative=[25]*13),
              dict(game_index=0,seed=999,policy='reference',company='OpexAI',
                   date=date(1971,3,1),cumulative=[60]*13)]
        out=diff_accounts(rows)
        self.assertEqual([x['postings_net_by_category'][NAMES[0]] for x in out],
                         [100,40,25,35])
        self.assertEqual([x['accounting_year'] for x in out],[1970,1970,1971,1971])

    def test_revenues_keep_negative_sign(self):
        a=dict(game_index=0,seed=999,policy='reference',company='AAAHogEx',
               date=date(1974,12,1),cumulative=[-200]*13)
        self.assertEqual(diff_accounts([a])[0]['postings_net_by_category'][NAMES[9]],-200)


if __name__=='__main__':
    unittest.main()
