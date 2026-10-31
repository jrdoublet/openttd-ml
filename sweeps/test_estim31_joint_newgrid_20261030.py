"""Check source isolation, exact paired ratio and duplicate-safe newgrid reader."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PREPARE = module('newgrid_prepare', 'estim31_joint_newgrid_prepare_20261030.py')
READ = module('newgrid_reader', 'estim31_joint_newgrid_analyse_20261030.py')


class ESTIM31NewGridTests(unittest.TestCase):
    def test_all_settings_changes_are_under_existing_estim_switch(self):
        self.assertEqual(len(PREPARE.CONFIGS), 10)
        self.assertEqual(PREPARE.DISPATCH.count('ESTIM_UNIFIE & 1'), 1)
        for name, values in PREPARE.CONFIGS.items():
            self.assertRegex(name, r'^a\d{3}_r\d{3}_w\d{2}_(flat|slope)')
            self.assertEqual(len(values), 5)
            self.assertGreater(values[0], 0)
            self.assertGreater(values[1], 0)
            self.assertGreater(values[2], 0)

    def test_ratio_uses_pooled_profits_not_average_ratios(self):
        rows={}
        for seed, our_profit, their_profit in ((42,80,100),(100,15,5)):
            rows[(READ.DATE,seed,'OpexAI')]={'profit_year':our_profit}
            rows[(READ.DATE,seed,'AAAHogEx')]={'profit_year':their_profit}
        self.assertAlmostEqual(READ.ratio(rows,(42,100)),100*95/105)

    def test_duplicates_are_rejected_and_arms_distinct(self):
        rows=[]
        for policy,profit in (('reference',300),('grid31_demo',500)):
            rows.append({'date':READ.DATE,'duel_policy_id':policy,
                         'run':['OpexAI',42],'profit_year':profit})
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'pairs.jsonl'
            path.write_text(''.join(json.dumps(x)+'\n' for x in rows),'utf8')
            arms=READ.snapshots(path,(42,),'grid31_demo')
            self.assertEqual(arms['reference'][(READ.DATE,42,'OpexAI')]['profit_year'],300)
            self.assertEqual(arms['grid31_demo'][(READ.DATE,42,'OpexAI')]['profit_year'],500)
            path.write_text(path.read_text('utf8')+json.dumps(rows[0])+'\n','utf8')
            with self.assertRaises(ValueError):
                READ.snapshots(path,(42,),'grid31_demo')


if __name__=='__main__':
    unittest.main()
