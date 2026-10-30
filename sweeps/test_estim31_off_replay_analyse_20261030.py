"""Small synthetic contracts for the strict OFF replay comparator."""
import json
import tempfile
import unittest
from pathlib import Path

from sweeps.estim31_off_replay_analyse_20261030 import (
    COMPANIES, DATES, SEEDS, evaluate,
)


class ReplayComparatorTest(unittest.TestCase):
    def fixture(self, folder, corrupt=False, omit=False):
        path = Path(folder)
        summary = path / 'campaign.json'
        jsonl = path / 'campaign.jsonl'
        games = [dict(game_ok=True, game_status='complete') for _ in range(4)]
        summary.write_text(json.dumps(dict(source_bundle_sha256='frozen-source',
                                           games=games, failed_runs=[])), encoding='utf8')
        rows = []
        for company in COMPANIES:
            for seed in SEEDS:
                for repeat in (0, 1):
                    for date in DATES:
                        if omit and company == 'AAAHogEx' and seed == 999 and repeat == 1 and date == DATES[0]:
                            continue
                        cash = 1000
                        if corrupt and company == 'OpexAI' and seed == 999 and repeat == 1 and date == DATES[1]:
                            cash = 1001
                        rows.append(dict(run=[company, seed, repeat], date=date,
                                         duel_policy_id='reference', source_bundle_sha256='frozen-source',
                                         profit_year=200, money=cash))
        jsonl.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf8')
        return jsonl, summary

    def test_identical_off_is_zero_mismatch(self):
        with tempfile.TemporaryDirectory() as folder:
            result = evaluate(*self.fixture(folder))
        self.assertEqual(result['mismatches'], 0)
        self.assertEqual(result['expected_comparisons'], 1680)

    def test_repeat_divergence_is_attributed(self):
        with tempfile.TemporaryDirectory() as folder:
            result = evaluate(*self.fixture(folder, corrupt=True))
        self.assertEqual(result['mismatches'], 1)
        self.assertEqual(result['by_company_seed'], {'OpexAI_999': 1})
        self.assertEqual(result['first_mismatch']['date'], DATES[1])

    def test_missing_snapshot_is_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'Missing/unexpected checkpoints'):
                evaluate(*self.fixture(folder, omit=True))


if __name__ == '__main__':
    unittest.main()
