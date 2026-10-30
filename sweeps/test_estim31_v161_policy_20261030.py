"""Prove the policy factorial changes parameters only, not any AI sources."""
import json
import unittest

from sweeps.estim31_v161_policy_prepare_20261030 import DEST, MIX, PARENT, file_map


class V161PolicyFactorial(unittest.TestCase):
    def test_identical_off_and_estim_source(self):
        original = file_map(PARENT)
        base = json.loads((PARENT / 'design.json').read_text('utf-8'))['configuration']
        for name, changes in MIX.items():
            with self.subTest(name=name):
                target = DEST / name
                self.assertTrue(target.is_dir())
                self.assertEqual(file_map(target), original)
                design = json.loads((target / 'design.json').read_text('utf-8'))
                expected = dict(base, **changes)
                self.assertEqual(design['configuration'], expected)
                self.assertEqual(design['v161_policy_factors'], changes)


if __name__ == '__main__':
    unittest.main()
