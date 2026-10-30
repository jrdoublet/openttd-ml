import unittest

from sweeps.estim31_v161_rail1970_prepare_20261030 import (
    BASE, DEST, NAME, FILE, OLD, NEW, hashes)


class FirstYearRailFundingIsolation(unittest.TestCase):
    def test_exact_opt_in_change_and_off_neutral(self):
        path = DEST / NAME
        oldhashes, newhashes = hashes(BASE), hashes(path)
        self.assertEqual(set(oldhashes), set(newhashes))
        self.assertEqual({k for k in oldhashes if oldhashes[k] != newhashes[k]},
                         {FILE})
        original = (BASE / FILE).read_text('utf-8')
        modified = (path / FILE).read_text('utf-8')
        self.assertEqual(original.count(OLD), 1)
        self.assertEqual(modified, original.replace(OLD, NEW, 1))
        self.assertIn('(ESTIM_UNIFIE & 1) == 0', modified)
        for filename in ('air_economics_c121.nut', 'air_economics_c121_fullscan.nut',
                         'settings.nut', 'globals_pre.nut', 'po01c_regen.nut'):
            self.assertEqual((BASE / 'ai/OpexAI' / filename).read_bytes(),
                             (path / 'ai/OpexAI' / filename).read_bytes())


if __name__ == '__main__':
    unittest.main()
