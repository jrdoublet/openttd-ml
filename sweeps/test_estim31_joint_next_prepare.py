"""Source and OFF isolation contracts for the new multi-factor grid."""
import importlib.util
import json
from pathlib import Path
import unittest


PATH = Path(__file__).with_name('estim31_joint_next_prepare.py')
SPEC = importlib.util.spec_from_file_location('estim31_next_prepare', PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GridSourceContracts(unittest.TestCase):
    def test_no_historical_code_changed(self):
        owner = MODULE.BASE / 'ai/OpexAI'
        for name in MODULE.CONFIGS:
            candidate = MODULE.DEST / name / 'ai/OpexAI'
            for filename in ('air_economics_c121.nut', 'settings.nut',
                             'globals_pre.nut'):
                self.assertEqual((owner/filename).read_bytes(),
                                 (candidate/filename).read_bytes(),
                                 (name, filename))

    def test_only_scanned_module_changed_and_no_unsafe_break(self):
        source = (MODULE.BASE/'ai/OpexAI/air_economics_c121_fullscan.nut')
        baseline = source.read_text('utf8')
        assert 'candidate.upperScore < best.economics.decisionScore' not in baseline
        for name, values in MODULE.CONFIGS.items():
            source_path = (MODULE.DEST/name/'ai/OpexAI/air_economics_c121_fullscan.nut')
            code = source_path.read_text('utf8')
            self.assertNotIn('candidate.upperScore < best.economics.decisionScore', code)
            self.assertEqual(code.count('function OpexC121ChooseRoutePlaneFullScan('),1)
            self.assertIn('ESTIM-only one-time interaction controls',code)
            self.assertIn('if (ESTIM_K_R_PRIOR.air !=', code)
            self.assertEqual(code.split('  /* ESTIM-only one-time')[0],
                             baseline.split('  if (catalog == null || plan == null')[0]
                             .split('function OpexC121ChooseRoutePlaneFullScan(catalog, plan, lines = null)\n{\n')[0]
                             + 'function OpexC121ChooseRoutePlaneFullScan(catalog, plan, lines = null)\n{\n')
            manifest = json.loads((MODULE.DEST/name/'design.json').read_text('utf8'))
            self.assertEqual(manifest['configuration']['air'],values[0])

    def test_all_scenarios_have_multiple_controls(self):
        baseline=(1.5,1.0,15.0,False,3,2,0,0)
        for name, scenario in MODULE.CONFIGS.items():
            self.assertGreaterEqual(sum(a!=b for a,b in zip(baseline,scenario)),2,
                                    name)


if __name__ == '__main__':
    unittest.main()
