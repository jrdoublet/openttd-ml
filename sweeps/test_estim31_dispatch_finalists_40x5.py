"""Protect the economic meaning of the ESTIM-31 40×5 reader."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import json


SCRIPT = Path(__file__).with_name('estim31_dispatch_finalists_40x5_analyse.py')
SPEC = importlib.util.spec_from_file_location('estim31_dispatch_ranking_reader', SCRIPT)
READER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(READER)


class ESTIM31RankingContracts(unittest.TestCase):
    def test_ratio_of_means_not_mean_of_ratios(self):
        rows = {}
        for seed, ours, theirs in ((1, 100, 200), (2, 50, 10)):
            rows[(READER.DATE, seed, 'OpexAI')] = {'profit_year': ours}
            rows[(READER.DATE, seed, 'AAAHogEx')] = {'profit_year': theirs}
        self.assertAlmostEqual(READER.ratio(rows, (1, 2)), 15000/210)
        self.assertNotAlmostEqual(READER.ratio(rows, (1, 2)), (50+500)/2)

    def test_reader_never_confuses_off_with_variant_duel(self):
        records = []
        for policy, ours, theirs in [('reference', 333, 444),
                                     ('dispatch31_trial', 222, 555)]:
            for company, profit in [('OpexAI', ours), ('AAAHogEx', theirs)]:
                records.append({'date': READER.DATE, 'duel_policy_id': policy,
                                'run': [company, 42], 'profit_year': profit})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'trial.jsonl'
            path.write_text(''.join(json.dumps(r)+'\n' for r in records), 'utf8')
            reference, variant = READER.read(path, 'dispatch31_trial')
        self.assertEqual(READER.ratio(reference, (42,)), 75)
        self.assertEqual(READER.ratio(variant, (42,)), 40)

    def test_duplicate_duel_snapshot_raises(self):
        entry = {'date': READER.DATE, 'duel_policy_id': 'reference',
                 'run': ['OpexAI', 42], 'profit_year': 1}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'bad.jsonl'
            path.write_text(json.dumps(entry)+'\n'+json.dumps(entry)+'\n', 'utf8')
            with self.assertRaises(ValueError):
                READER.read(path, 'dispatch31_trial')


if __name__ == '__main__':
    unittest.main()
