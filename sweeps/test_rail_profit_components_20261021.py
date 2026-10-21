"""Fixtures synthétiques pour le diagnostic RAIL-PROFIT-1 (sans Docker)."""

import unittest

from sweeps.diag_rail_profit_components_20261021 import (
    average_rank, compare_targets, factor, fit, parse_game, quartile, spearman,
)


def event(date, tag, fields, company=0):
    return f"[0] [I] [{company}] [I] OPEX {date} {tag} {fields}"


class ProfitComponentsTests(unittest.TestCase):
    def test_join_maturity_scale_and_accounting(self):
        lines = [
            event("1970-1-1", "PROJECT_CHOSEN", "mode=rail cargo=COAL src=1 dst=2 cost=2000 profit=900 roi=450"),
            event("1970-2-1", "RAIL_BUILD", "line=7 cargo=COAL src=1 dst=2 dist=90 cost=2800 trains=2 wagons=5"),
            event("1971-1-1", "LINE_REVENUE", "line=7 mode=rail cargo=COAL year=1971 age=1 pred_rev=1500 real_rev=100 pred_run=200 real_run=90 pred_prof=1200 real_prof=10 vehs=2"),
            event("1972-1-1", "LINE_REVENUE", "line=7 mode=rail cargo=COAL year=1972 age=2 pred_rev=1500 real_rev=1400 pred_run=200 real_run=400 pred_prof=1200 real_prof=1000 vehs=4"),
            event("1973-1-1", "LINE_REVENUE", "line=7 mode=rail cargo=COAL year=1973 age=3 pred_rev=1500 real_rev=900 pred_run=200 real_run=400 pred_prof=1200 real_prof=500 vehs=2"),
            event("1973-1-1", "LINE_REVENUE", "line=8 mode=air age=3 real_rev=2"),
            event("1973-1-1", "LINE_REVENUE", "line=7 mode=rail cargo=COAL year=1973 age=3 pred_rev=0 real_rev=0 pred_run=0 real_run=0 pred_prof=0 real_prof=0 vehs=2",1),
        ]
        rows, count = parse_game(lines, 42)
        self.assertEqual(count['mature_usable_line_years'], 2)
        self.assertEqual(count['immature'], 1)
        self.assertEqual(count['real_accounting_mismatch_years'], 0)
        self.assertEqual(count['predicted_gap_nonzero_years'], 2)
        self.assertEqual(len(rows), 1)
        r=rows[0]
        self.assertTrue(r['matched_choice'])
        self.assertEqual(r['cost_actual'], 2800)
        self.assertEqual(r['cost_pred'], 2000)
        self.assertEqual(r['years'],2)
        self.assertEqual(r['pred_prof'],1200)
        self.assertEqual(r['real_prof'], 500)  # median of 1000*2/4 and 500*2/2
        self.assertEqual(r['real_run'],300)  # median of 400*2/4 and 400*2/2
        self.assertEqual(r['real_rev'],800)  # 700 and 900 after fleet normalization
        self.assertEqual(r['amort_pred'],100)
        self.assertEqual(r['pred_oper'],1300)
        self.assertEqual(r['real_net_proxy'],400)

    def test_negative_profit_and_unknown_choice_survive(self):
        rows, counts=parse_game([
            event("1970-1-1","RAIL_BUILD","line=2 cargo=PASS src=3 dst=4 dist=20 cost=3000 trains=1"),
            event("1973-1-1","LINE_REVENUE","line=2 mode=rail cargo=PASS year=1973 age=3 pred_rev=100 real_rev=-20 pred_run=50 real_run=80 pred_prof=30 real_prof=-100 vehs=1"),
        ],7)
        self.assertEqual(counts['build_no_choice'],1)
        self.assertEqual(counts['mature_without_choice'],1)
        self.assertEqual(rows[0]['real_prof'],-100)
        self.assertIsNone(rows[0]['roi_pred'])

    def test_shrinkage_sign_and_rank_ties(self):
        sample=[]
        for i in range(30):
            sample.append({'cargo':'COAL','distance':80,'roi_pred':40,
                           'pred_prof':100,'real_prof':-10 if i<2 else 80})
        fit_values=fit(sample)
        self.assertGreater(fit_values['global'],0)
        self.assertEqual(factor(fit_values, {'cargo':'COAL','distance':90,'roi_pred':40,
                                              'pred_prof':-1},'cargo_distance'),1)
        self.assertEqual(quartile(90),1)
        self.assertEqual(quartile(127),2)
        self.assertEqual(quartile(172),3)
        self.assertEqual(quartile(173),4)
        self.assertEqual(average_rank([1,1,3]),[.5,.5,2.])
        self.assertAlmostEqual(spearman([1,2,3,4],[4,3,2,1]),-1)

    def test_comparable_targets_are_distinct(self):
        train=[]
        test=[]
        for seed in range(40):
            row={'seed':seed,'line':str(seed),'cargo':'COAL','distance':80,
                 'roi_pred':45, 'pred_prof':100, 'real_prof':80,
                 'pred_oper':110, 'real_oper':80, 'pred_net_proxy':100,
                 'real_net_proxy':70}
            train.append(row)
            test.append(dict(row))
        operating=compare_targets(train,test,list(range(40)),'pred_oper','real_oper')
        net=compare_targets(train,test,list(range(40)),'pred_net_proxy','real_net_proxy')
        self.assertEqual(operating['raw']['mae'],30)
        self.assertEqual(net['raw']['mae'],30)
        self.assertLess(operating['global']['mae'],1e-6)
        self.assertLess(net['global']['mae'],1e-6)


if __name__ == '__main__':
    unittest.main()
