"""Frozen-source and OFF-neutrality contracts for new cap interactions."""
import hashlib
import json
import unittest

from sweeps.estim31_v161_capcombo_prepare_20261030 import (
    PARENT, DEST, FILE, DESIGNS)
from sweeps.estim31_v161_motorcap_prepare_20261030 import changed_files


class CapComboContracts(unittest.TestCase):
    def test_only_experimental_prior_or_existing_runtime_settings_change(self):
        original = (PARENT / FILE).read_text('utf-8')
        for name, config in DESIGNS.items():
            with self.subTest(name=name):
                path = DEST / name
                self.assertTrue(path.is_dir())
                differences = changed_files(PARENT, path)
                self.assertEqual(differences, {FILE} if config['air'] != 2 else set())
                expected = original.replace(
                    'ESTIM_K_R_PRIOR.air = 2.00;',
                    f"ESTIM_K_R_PRIOR.air = {config['air']:.2f};", 1)
                self.assertEqual((path / FILE).read_text('utf-8'), expected)
                self.assertIn('if ((ESTIM_UNIFIE & 1) == 0)', expected)
                design = json.loads((path / 'design.json').read_text('utf-8'))
                for key, value in config.items():
                    self.assertEqual(design['configuration'][key], value)
                self.assertEqual(design['combined_sha256'][FILE],
                                 hashlib.sha256((path / FILE).read_bytes()).hexdigest())
                self.assertEqual((path / 'ai/OpexAI/air_economics_c121.nut').read_bytes(),
                                 (PARENT / 'ai/OpexAI/air_economics_c121.nut').read_bytes())


if __name__ == '__main__':
    unittest.main()
