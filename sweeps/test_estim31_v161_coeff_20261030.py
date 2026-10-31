import json
import unittest

from sweeps.estim31_v161_coeff_prepare_20261030 import ROOT, PARENT, DEST, FILE, DESIGNS


class PriorCoefficientIsolation(unittest.TestCase):
    def test_only_the_early_estim_priors_change(self):
        original = (PARENT / FILE).read_text('utf-8')
        for name, (air, rail, weight) in DESIGNS.items():
            with self.subTest(name=name):
                new = DEST / name
                text = (new / FILE).read_text('utf-8')
                expected = (original
                    .replace('ESTIM_K_R_PRIOR.air = 2.00;', f'ESTIM_K_R_PRIOR.air = {air:.2f};', 1)
                    .replace('ESTIM_K_R_PRIOR.rail = 0.75;', f'ESTIM_K_R_PRIOR.rail = {rail:.2f};', 1)
                    .replace('ESTIM_K_R_PRIOR_WEIGHT = 15.0;',
                             f'ESTIM_K_R_PRIOR_WEIGHT = {weight:.1f};', 1))
                self.assertEqual(text, expected)
                for filename in ('air_economics_c121.nut', 'globals_pre.nut',
                                 'settings.nut', 'air_fleet.nut', 'task_air.nut',
                                 'task_projects.nut'):
                    self.assertEqual((new / 'ai/OpexAI' / filename).read_bytes(),
                                     (PARENT / 'ai/OpexAI' / filename).read_bytes())
                config = json.loads((new / 'design.json').read_text('utf-8'))['configuration']
                self.assertEqual((config['air'], config['rail'], config['weight']),
                                 (air, rail, weight))
                self.assertIn('if ((ESTIM_UNIFIE & 1) == 0)', text)


if __name__ == '__main__':
    unittest.main()
