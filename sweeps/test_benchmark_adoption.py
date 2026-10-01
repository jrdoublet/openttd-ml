"""R24 : les statistiques favorables ne suffisent pas à qualifier le protocole."""
from pathlib import Path
import sys
import types
import unittest
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import openttdlab
except ImportError:
    fake_lab = types.ModuleType("openttdlab")
    for name in ("bananas_ai", "bananas_ai_library", "local_folder", "run_experiments"):
        setattr(fake_lab, name, mock.MagicMock())
    sys.modules["openttdlab"] = fake_lab

from bench_1v1_5y_20seeds import build_policy_comparison, policy_adoption_eligibility


class BenchmarkAdoptionTests(unittest.TestCase):
    def compare(self, seeds, repeats=1, years=10, rule="signs20", missing=False):
        """Résumés synthétiques sains ; la santé mensuelle relève d'assess_game."""
        summary = []
        for repeat in range(repeats):
            for seed in dict.fromkeys(seeds):
                for policy in ("ref", "var"):
                    for arm in ("OpexAI", "AAAHogEx"):
                        profit = 110.0 if policy == "var" and arm == "OpexAI" else 100.0
                        summary.append({
                            "duel_policy_id": policy, "arm": arm,
                            "seed": seed, "repeat": repeat,
                            "run_ok": True, "game_ok": True, "status": "complete",
                            "profit_year": profit, "company_value": 1000.0,
                            "profit": profit / 4, "performance_history": 100,
                            "median_station_rating": 100, "primary_vehicles": 10,
                        })
        if missing:
            summary.pop()
        return build_policy_comparison(
            summary, [], seeds=seeds, repeats=repeats,
            reference_policy_id="ref", variant_policy_id="var",
            primary_metric="profit_year", min_useful_primary_delta=5.0,
            value_guard_max_loss_pct=5.0, starting_year=1970, years=years,
            decision_rule=rule,
        )

    def test_repeated_maps_cannot_replace_independent_seeds(self):
        for seeds, repeats, rule in (([42], 20, "signs20"),
                                     (list(range(5)), 4, "signs20"),
                                     (list(range(20)), 2, "mean40")):
            with self.subTest(seeds=len(seeds), repeats=repeats, rule=rule):
                result = self.compare(seeds, repeats=repeats, rule=rule)
                self.assertTrue(result["comparison_complete"])
                self.assertEqual(result["verdict"], "diagnostic_only")
                self.assertFalse(result["adoption_sample_complete"])
                self.assertFalse(result["adoption_protocol"]["independent_seed_sample"])
                self.assertIn("repeated_seeds", result["adoption_protocol"]["reasons"])
                self.assertIsNone(result["primary_pass"])
                self.assertEqual(result["aggregates"]["profit_year"]["policy_delta"]["mean"], 10)

    def test_duplicate_seed_arguments_cannot_inflate_sample(self):
        result = self.compare([42] * 20)
        self.assertEqual(result["verdict"], "diagnostic_only")
        self.assertIn("duplicate_seeds", result["adoption_protocol"]["reasons"])
        self.assertEqual(result["adoption_protocol"]["distinct_seeds"], 1)

    def test_other_horizons_remain_diagnostic(self):
        for rule, size in (("signs20", 20), ("mean40", 40)):
            for years in (1, 5, 6, 9, 11):
                with self.subTest(rule=rule, years=years):
                    result = self.compare(list(range(size)), years=years, rule=rule)
                    self.assertEqual(result["verdict"], "diagnostic_only")
                    self.assertIn("horizon_not_10_years", result["adoption_protocol"]["reasons"])

    def test_documented_protocols_can_pass(self):
        for rule, size in (("signs20", 20), ("mean40", 40)):
            with self.subTest(rule=rule):
                result = self.compare(list(range(size)), rule=rule)
                self.assertEqual(result["verdict"], "pass")
                self.assertTrue(result["adoption_sample_complete"])
                self.assertEqual(result["adoption_protocol"]["reasons"], [])

    def test_incomplete_pairs_take_precedence_over_protocol(self):
        for years in (1, 10):
            with self.subTest(years=years):
                result = self.compare(list(range(20)), years=years, missing=True)
                self.assertFalse(result["comparison_complete"])
                self.assertEqual(result["verdict"], "incomplete")
                self.assertIsNone(result["primary_pass"])

    def test_unknown_rule_is_rejected(self):
        with self.assertRaises(ValueError):
            policy_adoption_eligibility(list(range(20)), 1, 10, "typo")


if __name__ == "__main__":
    unittest.main()