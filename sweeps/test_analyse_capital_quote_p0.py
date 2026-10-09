"""Une construction n'est pas recomptee a chaque checkpoint mensuel."""
import unittest

from sweeps.analyse_capital_quote_p0 import analyze


class CapitalQuoteAnalysisTests(unittest.TestCase):
    def test_last_checkpoint_only(self):
        def row(date, policy, value):
            return {
                "run": ["OpexAI", 42, 0], "date": date, "policy_id": policy,
                "capital_quote_by_mode": {
                    "air": {"success_events": 1, "failed_events": 0,
                            "quoted_success": 100, "actual_success": value,
                            "actual_failed_at_return": 0, "max_samples_learned": 1}
                },
            }
        outcome = analyze([
            row("1970-01-01", "learning", 95),
            row("1970-12-01", "learning", 110),
            row("1970-12-01", "reference", 100),
        ])
        self.assertEqual(outcome["last_checkpoint_games"], 2)
        data = outcome["by_policy_and_mode"]["learning"]["air"]
        self.assertEqual(data["quoted_success"], 100)
        self.assertEqual(data["actual_success"], 110)
        self.assertEqual(data["ratio_actual_to_quote_success"], 1.1)

    def test_missing_is_unknown(self):
        outcome = analyze([{"run": ["OpexAI", 7, 0], "date": "1970-12-01",
                            "policy_id": "variant", "capital_quote_by_mode": None}])
        self.assertEqual(outcome["games_without_extracted_signs"], {"variant": 1})
        self.assertEqual(outcome["by_policy_and_mode"], {})


if __name__ == "__main__":
    unittest.main()
