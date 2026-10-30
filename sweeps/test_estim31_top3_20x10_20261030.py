"""Selection cannot change post-hoc or accidentally use the mean of ratios."""
import unittest

from sweeps.estim31_top3_20x10_20261030 import SEEDS20, freeze, analyze


class Top3Contract(unittest.TestCase):
    def test_known_twenty_seeds_and_ratio_of_means(self):
        self.assertEqual(len(SEEDS20), 20)
        self.assertEqual(SEEDS20[:5], (42, 100, 7, 999, 2026))
        opex, aaa = [10, 100], [100, 10]
        self.assertEqual(100 * sum(opex) / sum(aaa), 100)
        self.assertNotEqual(100 * sum(opex) / sum(aaa),
                            (100 * opex[0] / aaa[0] + 100 * opex[1] / aaa[1]) / 2)

    def test_freeze_requires_three_healthy_provenance_40x5(self):
        rows = [{'suite': 'v161', 'name': str(i), 'ratio_pct': float(i),
                 'health': '80/80 complete', 'pairs': {str(s): {} for s in range(40)},
                 'source_bundle_sha256': 'a' * 64} for i in range(3)]
        result = freeze({'ranked': rows, 'criterion': 'ratio of means'})
        self.assertEqual(len(result['locked_40x5_ranking']), 3)
        rows[1]['pairs'].pop('2')
        with self.assertRaises(ValueError):
            freeze({'ranked': rows, 'criterion': 'ratio of means'})

    def test_partial_does_not_choose_default(self):
        from pathlib import Path
        frozen = {'criterion_10y': 'ratio', 'seeds20': list(SEEDS20),
                  'locked_40x5_ranking': [
                      {'suite': 'v161', 'name': f'absent_{i}',
                       'ratio_40x5_pct': 100.0, 'source_bundle_sha256': 'a' * 64}
                      for i in range(3)]}
        result = analyze(Path('/nonexistent'), frozen)
        self.assertIsNone(result['winner'])
        self.assertEqual(len(result['not_yet_qualified']), 3)


if __name__ == '__main__':
    unittest.main()
