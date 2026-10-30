import unittest

from sweeps.estim31_c121_no_upper_prepare_20261030 import ROOT, DEST, DESIGNS, FILE


class ExactEnumeration(unittest.TestCase):
    def test_off_byte_identity_and_no_upper_bound(self):
        for name, parent in DESIGNS.items():
            a = ROOT / parent / 'ai/OpexAI'
            b = DEST / name / 'ai/OpexAI'
            for file in ('air_economics_c121.nut', 'settings.nut', 'globals_pre.nut',
                         'task_air.nut', 'air_fleet.nut', 'task_projects.nut'):
                self.assertEqual((a / file).read_bytes(), (b / file).read_bytes())
            scan = (DEST / name / FILE).read_text('utf-8')
            self.assertEqual(scan.count('candidates.append({ plane = plane });'), 2)
            self.assertNotIn('local upperScore', scan)
            self.assertNotIn('a.upperScore', scan)
            self.assertNotIn('C121InitialEngineUpperScore(', scan)
            self.assertIn('if ((ESTIM_UNIFIE & 1) == 0)', scan)
            self.assertNotIn('candidate.upperScore < best.economics.decisionScore', scan)


if __name__ == '__main__':
    unittest.main()
