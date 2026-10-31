"""Cross-variant proof: only four existing opt-in source files can differ."""
import unittest

from sweeps.estim31_v161_motorcap_prepare_20261030 import (
    BASE, DEST, MARGIN, MOTOR, MOTOR_FILE, MARGIN_FILES, NAMES, changed_files)


class V161MotorCapContracts(unittest.TestCase):
    def test_exact_union_of_parent_source_differences(self):
        for name in NAMES:
            self.assertTrue((DEST / name).is_dir())
            self.assertEqual(changed_files(BASE / name, MOTOR / name), {MOTOR_FILE})
            self.assertEqual(changed_files(BASE / name, MARGIN / name),
                             set(MARGIN_FILES))
            self.assertEqual(changed_files(BASE / name, DEST / name),
                             {MOTOR_FILE, *MARGIN_FILES})
            for file in (MOTOR_FILE, *MARGIN_FILES):
                source = MOTOR if file == MOTOR_FILE else MARGIN
                self.assertEqual((DEST / name / file).read_bytes(),
                                 (source / name / file).read_bytes())
            for file in ('settings.nut', 'globals_pre.nut', 'air_economics_c121.nut'):
                self.assertEqual((BASE / name / 'ai/OpexAI' / file).read_bytes(),
                                 (DEST / name / 'ai/OpexAI' / file).read_bytes())

    def test_no_unproved_pruning_and_same_engine_revalidation(self):
        for name in NAMES:
            self.assertTrue((DEST / name).is_dir())
            code = (DEST / name / MOTOR_FILE).read_text('utf-8')
            self.assertNotIn('candidate.upperScore < best.economics.decisionScore', code)
            self.assertIn('OpexC121OneOrTwoDepth(inv, 1)', code)
            fleet = (DEST / name / 'ai/OpexAI/air_fleet.nut').read_text('utf-8')
            self.assertIn('MARGINAL_ENGINE_STALE', fleet)
            self.assertIn('if ((ESTIM_UNIFIE & 1) == 0)', fleet)


if __name__ == '__main__':
    unittest.main()
