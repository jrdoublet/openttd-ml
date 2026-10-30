"""Source-only structural contracts; engine behavior requires actual smoke."""
import unittest

from sweeps.estim31_motor_joint_prepare_20261030 import BASE, DEST, DESIGNS, FILE, NEW


class JointEngineContract(unittest.TestCase):
    def test_historical_sources_identical_and_exact_engine_choice(self):
        for name in DESIGNS:
            old, new = BASE/name/'ai/OpexAI', DEST/name/'ai/OpexAI'
            for filename in ('air_economics_c121.nut','globals_pre.nut','settings.nut','info.nut'):
                self.assertEqual((old/filename).read_bytes(),(new/filename).read_bytes())
            code = (DEST/name/FILE).read_text('utf-8')
            self.assertIn(NEW,code)
            self.assertIn('local winnerEconomics = ("jointEconomics" in best)',code)
            self.assertIn('if ((ESTIM_UNIFIE & 1) == 0) {',code)
            self.assertNotIn('candidate.upperScore < best.economics.decisionScore',code)


if __name__ == '__main__':
    unittest.main()
