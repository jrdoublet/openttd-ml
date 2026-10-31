"""No unproven shortcut or late priors in safe ESTIM experiment copies."""
import unittest
from pathlib import Path

from sweeps.estim31_joint_next_prepare import BASE, REPO
from sweeps.estim31_joint_safe_prepare_20261030 import SAFE_CONFIGS


class SafeGridSourceContract(unittest.TestCase):
    def test_historical_off_files_identical(self):
        root = REPO / 'results/estim31_joint_safe20261030'
        for name in SAFE_CONFIGS:
            for file in ('settings.nut', 'globals_pre.nut', 'air_economics_c121.nut'):
                rel = Path('ai/OpexAI') / file
                self.assertEqual((root/name/rel).read_bytes(), (BASE/rel).read_bytes())

    def test_early_prior_and_ge_shortcut_disabled_under_estim(self):
        root = REPO / 'results/estim31_joint_safe20261030'
        for name in SAFE_CONFIGS:
            code = (root/name/'ai/OpexAI/air_economics_c121_fullscan.nut').read_text('utf-8')
            self.assertLess(code.index('ESTIM_K_R_PRIOR.air = '),
                            code.index('function OpexC121ScanRoutePlaneEnginesFullScan'))
            self.assertIn('if ((ESTIM_UNIFIE & 1) == 0) {', code)
            self.assertIn('if (geMode != 1) {', code)
            self.assertNotIn('candidate.upperScore < best.economics.decisionScore', code)
            self.assertNotIn('one-time interaction controls', code)


if __name__ == '__main__':
    unittest.main()
