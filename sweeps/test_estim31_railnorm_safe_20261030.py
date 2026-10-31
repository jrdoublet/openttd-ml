import unittest
from pathlib import Path

from sweeps.estim31_joint_next_prepare import REPO
from sweeps.estim31_railnorm_safe_prepare_20261030 import BASE, DEST, DESIGNS, PATCH


class RailNormSafeContract(unittest.TestCase):
    def test_only_models_file_changes(self):
        for name in DESIGNS:
            old, new = BASE/name/'ai/OpexAI', DEST/name/'ai/OpexAI'
            source = (new/'projects_models.nut').read_text('utf-8')
            self.assertIn(PATCH, source)
            self.assertEqual(source.count('ESTIM_UNIFIE & 16'),
                             (old/'projects_models.nut').read_text('utf-8').count('ESTIM_UNIFIE & 16')+1)
            for old_path in old.rglob('*'):
                if old_path.is_file() and old_path.name != 'projects_models.nut':
                    self.assertEqual(old_path.read_bytes(),
                                     (new/old_path.relative_to(old)).read_bytes(), old_path.name)


if __name__ == '__main__':
    unittest.main()
