import copy
import unittest
from rva_options import dossier_key, evaluate_options


class Options(unittest.TestCase):
    context=dict(fingerprint='fixture', horizon='12 economic months', currency='GBP', annual_clock='economy')

    def option(self, name='pax'):
        return dict(option_id=name,od=[1,2,0], feasible=True, tiles=[10,20],
          cycle=dict(one_way_days=10,trains=1,cargos=[dict(cargo=0,capacity=50,
            dwell_a_days=1,dwell_b_days=1,monthly=100)],waiting_a_days=0,waiting_b_days=0,
            rating_anchor_pct=50,parallel_loading=True),
          line=dict(running_annual=10,amort_annual=5,capital_required=100),
          annual_income_per_monthly_unit={0:12},corrections={},effects=[],effects_complete=True)

    def run_options(self, options, **kw):
        return evaluate_options(dossier_key(1,2,0),options,context=self.context,budget=1000,**kw)

    def test_optional_mail_has_cost_and_capacity(self):
        pax=self.option(); mail=copy.deepcopy(pax);mail['option_id']='mail'
        mail['cycle']['cargos'].append(dict(cargo=1,capacity=20,monthly=20,dwell_a_days=1,dwell_b_days=1))
        mail['annual_income_per_monthly_unit'][1]=12
        mail['line']['running_annual']=10000
        self.assertEqual(self.run_options([pax,mail])['selected_option'],'pax')

    def test_partial_failure_requires_new_quote(self):
        option=self.option();option.update(extension=True,incremental_tiles=[30],tiles=[10,20,30])
        r=self.run_options([option],actual_tiles=[10,20])
        self.assertIsNone(r['selected_option'])
        self.assertEqual(r['options'][0]['status'],'requote_actual_footprint')

    def test_redundant_extension_and_unknown_gain_fall_back(self):
        option=self.option();option.update(extension=True,incremental_tiles=[])
        self.assertIsNone(self.run_options([option])['selected_option'])
        option=self.option();option['effects_complete']=False
        self.assertIsNone(self.run_options([option])['selected_option'])

    def test_same_dossier_not_duplicate_purchases(self):
        self.assertEqual(dossier_key(1,2,0),dossier_key(2,1,0))
        with self.assertRaises(ValueError):self.run_options([self.option(),self.option()])
