import unittest
from rva_replay import select


class Replay(unittest.TestCase):
    def project(self,key,profit=100,finance=100,mode='rail',**kw):
        return dict(key=key,profit=profit,fund_profit=profit,finance=finance,
                    decision_finance=finance,revenue=profit+10,tier=0,bonus_pct=0,mode=mode,**kw)

    def snapshot(self,projects,**kw):
        return dict(inventory_complete=True,fit_complete=True,projects=projects,
                    budget=100,k_dec=100,floor_pct=0,limit=10,**kw)

    def test_affordability_before_floor_and_tie_order(self):
        s=self.snapshot([self.project('rich',1000,101),self.project('a'),self.project('b')])
        s['floor_pct']=50;r=select(s)
        self.assertEqual(r['selected'],'a');self.assertEqual(r['rejected']['rich'],'cash')
        self.assertEqual(r['ranked'],['a','b'])

    def test_tier_bonus_kdec_and_no_claim_of_executed_purchase(self):
        a=self.project('rail',200);b=self.project('air',150,mode='air');b['bonus_pct']=100
        r=select(self.snapshot([a,b]));self.assertEqual(r['selected'],'air')
        self.assertIsNone(r['executed_purchase']);self.assertIsNone(r['simulated_purchase'])
        b['tier']=-1;self.assertEqual(select(self.snapshot([a,b]))['selected'],'rail')

    def test_partial_snapshot_is_unknown_and_no_mutation(self):
        s=self.snapshot([self.project('a')]);s['inventory_complete']=False
        self.assertEqual(select(s)['status'],'not_covered')
        self.assertNotIn('score',s['projects'][0])

    def test_profit_override_changes_admission_not_just_rank(self):
        s=self.snapshot([self.project('pax',200),self.project('freight',100)])
        r=select(s,{'pax':{'profit':-1,'fund_profit':-1}})
        self.assertEqual(r['selected'],'freight');self.assertEqual(r['rejected']['pax'],'floor')
