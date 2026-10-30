import unittest

from sweeps.estim31_v161_newrank_20261030 import check_health


class HealthyCompleteness(unittest.TestCase):
    def test_only_complete_healthy_games(self):
        games = [{'game_ok': True, 'game_status': 'complete'} for _ in range(10)]
        self.assertTrue(check_health({'games': games, 'failed_runs': []}, 10))
        self.assertFalse(check_health({'games': games[:-1]}, 10))
        games[0]['game_status'] = 'stagnation_suspect'
        self.assertFalse(check_health({'games': games}, 10))
        games[0]['game_status'] = 'complete'
        self.assertFalse(check_health({'games': games, 'failed_runs': ['bad']}, 10))


if __name__ == '__main__':
    unittest.main()
