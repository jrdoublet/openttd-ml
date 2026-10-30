import unittest

from sweeps.estim31_joint_next_prepare import REPO
from sweeps.estim31_v161_safe_prepare_20261030 import ROOT, DEST, DESIGNS


class V161SameEngineContract(unittest.TestCase):
    def test_default_off_historical_functions_and_experimental_guard(self):
        for name,parent in DESIGNS.items():
            a=ROOT/parent/name/'ai/OpexAI'
            b=DEST/name/'ai/OpexAI'
            for filename in ('settings.nut','globals_pre.nut','air_economics_c121.nut',
                             'info.nut','projects_models.nut'):
                self.assertEqual((a/filename).read_bytes(),(b/filename).read_bytes())
            af=(b/'air_fleet.nut').read_text('utf-8')
            self.assertIn('if ((ESTIM_UNIFIE & 1) == 0) {',af)
            self.assertIn('forcedEngine == null',af)
            self.assertIn('MARGINAL_ENGINE_STALE',af)
            self.assertIn('OpexAirAddPlane(line, this._catalog, this._lines, locked)',
                          (b/'task_projects.nut').read_text('utf-8'))
            self.assertIn('OpexAirAddPlane(line, this._catalog, this._lines, locked)',
                          (b/'task_air.nut').read_text('utf-8'))


if __name__=='__main__':
    unittest.main()
