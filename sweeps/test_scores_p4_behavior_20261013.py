"""Contrats P4 variante : OFF identique, Save/Load candidat, facteur C70 borné à la cohorte."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'ai' / 'OpexAI'


def code(name):
    return (ROOT / name).read_text(encoding='utf8')


class P4Behavior(unittest.TestCase):
    def test_off_all_levels(self):
        info=code('info.nut')
        block=info.split('name = "score_c70_stable_cohort"',1)[1].split('});',1)[0]
        for d in ('easy','medium','hard','custom'):
            self.assertIn(f'{d}_value = 0',block)
        self.assertIn('SCORE_C70_STABLE_COHORT <- false;',code('globals_pre.nut'))
        self.assertIn('SCORE_C70_STABLE_COHORT = AIController.GetSetting("score_c70_stable_cohort") != 0;',code('settings.nut'))

    def test_log_off_both_arms_and_profiling_separated(self):
        report=code('task_report.nut')
        self.assertIn('if (SCORE_C70_COHORT_LOG) AILog.Info("P4_C70_LINE',report)
        self.assertIn('if (SCORE_C70_COHORT_LOG) AILog.Info("P4_C70_SUM',report)
        self.assertIn('if (SCORE_C70_STABLE_COHORT && C70_MODE_CALIBRATION)',report)
        self.assertIn('C70_MODE_FACTOR[mode] = stableK;',report)

    def test_load_rebuilds_from_identical_line_aggregates(self):
        model=code('projects_models.nut')
        report=code('task_report.nut')
        self.assertIn('stableSums[line.mode][0] += line.p4C70Real.tofloat() / line.p4C70Pred.tofloat();',model)
        self.assertIn('C70_MODE_FACTOR[m] = (stableAcc[0] + 1.0) / (stableAcc[1] + 1).tofloat();',model)
        self.assertIn('line.p4C70Real += real;',report)
        self.assertIn('line.p4C70Pred += cPred.tofloat();',report)
        self.assertIn('local legacyK = C70_MODE_FACTOR[mode];',report)
        self.assertIn('local stableK = (acc[2] + 1.0) / (acc[1] + 1).tofloat();',report)

    def test_missing_stable_line_starts_at_one(self):
        # Condition exacte du pseudo-échantillon C70 ; sans observation
        # candidate, ne jamais transformer « inconnu » en k=0.
        def k(values):
            return (1.0+sum(values))/(len(values)+1)
        self.assertEqual(k([]),1.0)
        self.assertAlmostEqual(k([.2,.8]),2.0/3.0)


if __name__=='__main__':
    unittest.main()
