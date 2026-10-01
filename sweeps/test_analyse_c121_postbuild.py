import unittest
from sweeps.analyse_c121_postbuild import annual_key_fix, checkpoint_coverage, perturbation


class RecoveryTests(unittest.TestCase):
    def test_monthly_coverage_rejects_duplicate_missing_and_wrong_identity(self):
        rows = [{"date": f"{1970 + m // 12}-{m % 12 + 1:02d}-01", "arm": "c121", "seed": 42}
                for m in range(38)]
        self.assertTrue(checkpoint_coverage(rows, "c121", 42, 3))
        self.assertTrue(checkpoint_coverage(list(reversed(rows)), "c121", 42, 3))
        self.assertFalse(checkpoint_coverage(rows[:-1], "c121", 42, 3))
        self.assertFalse(checkpoint_coverage(rows + [rows[0]], "c121", 42, 3))
        self.assertFalse(checkpoint_coverage(rows, "c115", 42, 3))
        self.assertFalse(checkpoint_coverage(rows, "c121", 100, 3))

    def test_json_annual_keys_preserve_unknown(self):
        self.assertEqual(annual_key_fix({"annual": {"OpexAI": {"0": None, "1": 100}}}),
                         {"annual": {"OpexAI": {0: None, 1: 100}}})

    def test_no_perturbation_verdict_on_partial_games(self):
        class Duel:
            @staticmethod
            def compare(*args):
                return {"complete": False}
        self.assertEqual(perturbation([], "c121", [42], 3, Duel),
                         {"complete": False, "practical_filter": False})

    def test_filter_requires_each_gate_and_is_not_neutrality(self):
        class Duel:
            values = [1, 1, 1, -1, -1]
            value_pct = 0

            @classmethod
            def compare(cls, *args):
                return {"complete": True, "paired_final": {"trace": {
                    "per_seed": [{"opex_profit_delta": v} for v in cls.values],
                    "opex_profit_delta": sum(cls.values) / 5, "value_delta_pct": cls.value_pct}}}
        games = [{"arm": "c121", "annual": {"OpexAI": {2: 100}}}]
        def result():
            return perturbation(games, "c121", [42, 100, 999, 1234, 5678], 3, Duel)
        self.assertTrue(result()["practical_filter"])
        self.assertFalse(result()["neutrality_proven"])
        Duel.value_pct = -5.1
        self.assertFalse(result()["practical_filter"])
        Duel.value_pct = 0
        Duel.values = [1, 1, 1, -100, -100]
        self.assertFalse(result()["practical_filter"])
        Duel.values = [100, 100, -1, -1, -1]
        self.assertFalse(result()["practical_filter"])


if __name__ == "__main__":
    unittest.main()