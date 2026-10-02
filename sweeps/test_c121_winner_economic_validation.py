import copy
import unittest
from sweeps.run_c121_winner_economic_validation import neutral_gate, intervention_arms


class NeutralGateTests(unittest.TestCase):
    def test_context_arms_keep_adopted_fusion_and_only_vary_context(self):
        reference, variant = intervention_arms("context")
        self.assertIn("c121_air_winner_fusion=1", reference)
        self.assertIn("c121_air_winner_fusion=1", variant)
        self.assertIn("catalog_cost_probe=0", reference)
        self.assertEqual(reference.replace("engine_context=0", "engine_context=1"), variant)
        with self.assertRaises(ValueError):
            intervention_arms("other")

    def report(self):
        return {"failed_runs": [], "policy_comparison": {
            "comparison_complete": True, "metric_coverage_complete": True,
            "complete_pairs": 20, "planned_pairs": 20, "adoption_sample_complete": True,
            "value_guard_pass": True, "verdict": "fail_primary", "aggregates": {
                "profit_year": {"policy_delta": {
                    "mean_student_t_95pct_ci": [-10, 5], "sign_test_p": .7,
                    "wins": 9, "losses": 11, "ties": 0}}}}}

    def test_raw_fail_primary_can_be_neutral(self):
        self.assertTrue(neutral_gate(self.report(), 20, True)["pass"])

    def test_entirely_negative_ci_rejected(self):
        report = self.report()
        report["policy_comparison"]["aggregates"]["profit_year"]["policy_delta"]["mean_student_t_95pct_ci"] = [-20, -1]
        self.assertFalse(neutral_gate(report, 20, True)["pass"])

    def test_significant_defeat_rejected(self):
        report = self.report()
        d = report["policy_comparison"]["aggregates"]["profit_year"]["policy_delta"]
        d.update(sign_test_p=.01, wins=2, losses=18)
        self.assertFalse(neutral_gate(report, 20, True)["pass"])

    def test_significant_victory_accepted(self):
        report = self.report()
        d = report["policy_comparison"]["aggregates"]["profit_year"]["policy_delta"]
        d.update(sign_test_p=.01, wins=18, losses=2)
        self.assertTrue(neutral_gate(report, 20, True)["pass"])

    def test_missing_health_coverage_value_and_sample_fail_closed(self):
        base = self.report()
        del base["failed_runs"]
        self.assertFalse(neutral_gate(base, 20, True)["pass"])
        for field in ("comparison_complete", "metric_coverage_complete", "value_guard_pass", "adoption_sample_complete"):
            report = self.report()
            del report["policy_comparison"][field]
            self.assertFalse(neutral_gate(report, 20, True)["pass"])

    def test_all_ties_and_unknown_ci(self):
        report = self.report()
        d = report["policy_comparison"]["aggregates"]["profit_year"]["policy_delta"]
        d.update(sign_test_p=None, wins=0, losses=0, ties=20, mean_student_t_95pct_ci=[0, 0])
        self.assertTrue(neutral_gate(report, 20, True)["pass"])
        d["mean_student_t_95pct_ci"] = None
        self.assertFalse(neutral_gate(report, 20, True)["pass"])


if __name__ == "__main__":
    unittest.main()
