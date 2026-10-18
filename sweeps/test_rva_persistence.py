import copy
import json
from pathlib import Path
import unittest
from rva_learning import DwellModel


class Persistence(unittest.TestCase):
    def model(self):
        m=DwellModel();m.observe('route/material/cargo/distribution',10,[4,6])
        m.observe('route/material/cargo/distribution',30,[8,10])
        return m

    def test_roundtrip_only_completed_observations(self):
        m=self.model();state=json.loads(json.dumps(m.save('worldA',20)))
        restored=DwellModel.load(state,'worldA',20)
        self.assertEqual(restored.load_status,'restored')
        self.assertEqual(restored.predict('route/material/cargo/distribution',21,3),
                         m.predict('route/material/cargo/distribution',21,3))
        self.assertEqual(len(restored.observations),1)

    def test_invalidation_and_corruption(self):
        s=self.model().save('worldA',20)
        for changed in [dict(s,version=99),dict(s,fingerprint='worldB'),dict(s,saved_tick=21)]:
            self.assertEqual(DwellModel.load(changed,'worldA',20).observations,[])
        bad=copy.deepcopy(s);bad['observations'][0]['dwell_bounds']=[float('nan'),5]
        self.assertEqual(DwellModel.load(bad,'worldA',20).observations,[])
        bad=copy.deepcopy(s);bad['observations'][0]['completed_tick']=21
        self.assertEqual(DwellModel.load(bad,'worldA',20).observations,[])

    def test_no_default_save_format_change(self):
        ai=Path(__file__).resolve().parents[1]/'ai/OpexAI'
        self.assertNotIn('RVA_', (ai/'persist.nut').read_text())
        self.assertIn('if (RVA_CYCLE_PROBE) OpexRvaResetTransient();',(ai/'main.nut').read_text())
        source=(ai/'rva_evaluator.nut').read_text()
        for token in ('RVA_EVAL_WORK = null','RVA_CYCLE_STATE = null'):
            self.assertIn(token,source)
