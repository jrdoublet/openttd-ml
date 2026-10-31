import hashlib
import tempfile
import unittest
from pathlib import Path

from sweeps.estim31_v161_newrank_20261030 import (
    SEEDS40, check_health, check_qualification)


class HealthyCompleteness(unittest.TestCase):
    def test_only_complete_healthy_games(self):
        games = [{'game_ok': True, 'game_status': 'complete'} for _ in range(10)]
        self.assertTrue(check_health({'games': games, 'failed_runs': []}, 10))
        self.assertFalse(check_health({'games': games[:-1]}, 10))
        games[0]['game_status'] = 'stagnation_suspect'
        self.assertFalse(check_health({'games': games}, 10))
        games[0]['game_status'] = 'complete'
        self.assertFalse(check_health({'games': games, 'failed_runs': ['bad']}, 10))

    def test_exact_pairing_and_source_provenance(self):
        campaign, policy, sha = 'fixture_40x5', 'fixture_variant', 'a' * 64

        def arm(name):
            result = {}
            for seed in SEEDS40:
                for company in ('OpexAI', 'AAAHogEx'):
                    for year in range(1970, 1975):
                        date = f'{year}-12-01'
                        result[(seed, company, date)] = {
                            'run': [company, seed, 0], 'campaign_id': campaign,
                            'duel_policy_id': name, 'source_bundle_sha256': sha}
            return result

        def game(name, seed):
            return {'seed': seed, 'repeat': 0, 'policy_id': name,
                    'campaign_id': campaign, 'source_bundle_sha256': sha,
                    'expected_last_checkpoint': '1974-12-01',
                    'game_ok': True, 'game_status': 'complete',
                    'companies': {c: {'horizon_complete': True,
                                      'status': 'complete', 'run_ok': True}
                                  for c in ('OpexAI', 'AAAHogEx')}}

        reference, variant = arm('reference'), arm(policy)
        report = {'games': [game(p, s) for p in ('reference', policy)
                            for s in SEEDS40],
                  'failed_runs': [], 'campaign_id': campaign,
                  'policy_id': 'reference', 'source_bundle_sha256': sha,
                  'years': 5, 'start_year': 1970, 'repeats': 1, 'map_size': 8,
                  'expected_last_checkpoint': '1974-12-01', 'seeds': list(SEEDS40),
                  'policies': [{'id': 'reference', 'explicit_settings': [['probes', 2]]},
                               {'id': policy, 'explicit_settings': [
                                   ['probes', 2], ['estim_unifie', 31]]}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'manifest.json'
            path.write_text('{}', encoding='utf-8')
            report['manifest_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            check = lambda: check_qualification(
                report, reference, variant, campaign, policy, path)
            self.assertIsNone(check())
            report['games'][0]['seed'] = SEEDS40[1]
            self.assertIn('duplicate', check())
            report['games'][0]['seed'] = SEEDS40[0]
            report['games'][0]['source_bundle_sha256'] = 'b' * 64
            self.assertIn('provenance', check())
            report['games'][0]['source_bundle_sha256'] = sha
            key = next(iter(variant))
            variant[key]['campaign_id'] = 'different campaign'
            self.assertIn('mixed source', check())
            variant[key]['campaign_id'] = campaign
            report['manifest_sha256'] = '0' * 64
            self.assertIn('manifest', check())
            report['manifest_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            report['policies'][0]['explicit_settings'] = [['probes', 258]]
            self.assertIn('settings', check())


if __name__ == '__main__':
    unittest.main()
