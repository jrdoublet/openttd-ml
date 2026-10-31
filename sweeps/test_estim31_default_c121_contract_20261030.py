import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sweeps.estim31_default_c121_contract_20261030 import source_function, validate


class C121Contract(unittest.TestCase):
    def test_duplicate_or_absent_original_function_is_rejected(self):
        body = 'function OpexC121ChooseRoutePlane(catalog, plan)\n{\n  return null;\n}'
        self.assertEqual(source_function(body, 'OpexC121ChooseRoutePlane'), body)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            source_function(body + '\n' + body, 'OpexC121ChooseRoutePlane')

    def test_historical_function_change_is_rejected(self):
        baseline = ('function OpexC121ChooseRoutePlane(a)\n{\n  return 1;\n}\n'
                    'function OpexC121ScanRoutePlaneEngines(a)\n{\n  return 2;\n}\n')
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'air_economics_c121.nut').write_text(
                baseline.replace('return 1;', 'return 3;'), 'utf-8')
            (root / 'air_economics_c121_fullscan.nut').write_text('placeholder', 'utf-8')
            (root / 'settings.nut').write_text('placeholder', 'utf-8')
            with self.assertRaisesRegex(ValueError, 'Historical C121'):
                validate(root, baseline)


if __name__ == '__main__':
    unittest.main()
