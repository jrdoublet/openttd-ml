import copy
import unittest
from run_c121_night_queue import healthy, gate_pass, resource_args


class GateTests(unittest.TestCase):
    def test_resource_override_is_explicit_and_bounded(self):
        self.assertEqual(resource_args({}),
                         ["--cpus", "3", "--memory", "2g", "--max-workers", "3"])
        self.assertEqual(resource_args({"cpus": 10, "memory": "8g", "max_workers": 10}),
                         ["--cpus", "10", "--memory", "8g", "--max-workers", "10"])
        with self.assertRaises(ValueError):
            resource_args({"cpus": 10, "max_workers": 11})
        with self.assertRaises(ValueError):
            resource_args({"memory": "0g"})

    def setUp(self):
        self.data = {"failed_runs": [], "games": [
            {"game_ok": True, "unattributed_errors": [], "companies": {
                name: {"horizon_complete": True, "run_ok": True}
                for name in ("OpexAI", "AAAHogEx")}} for _ in range(80)],
            "policy_comparison": {"comparison_complete": True, "complete_pairs": 40,
                "adoption_sample_complete": True, "metric_coverage_complete": True,
                "decision_rule": {"rule": "gain_short"}, "verdict": "pass",
                "primary_pass": True, "value_guard_pass": True}}

    def test_complete_gate(self):
        self.assertTrue(gate_pass(self.data, "gain_short", 40))

    def test_economic_failure_does_not_authorize_B(self):
        self.data["policy_comparison"]["verdict"] = "fail_primary"
        self.assertTrue(healthy(self.data, 40))
        self.assertFalse(gate_pass(self.data, "gain_short", 40))

    def test_coverage_and_rule_are_required(self):
        for field in ("adoption_sample_complete", "metric_coverage_complete"):
            data = copy.deepcopy(self.data)
            data["policy_comparison"][field] = False
            self.assertFalse(gate_pass(data, "gain_short", 40))
        self.assertFalse(gate_pass(self.data, "non_erosion", 40))

    def test_adversary_and_unknown_errors_stop_queue(self):
        for change in ("adversary", "errors", "missing_game"):
            data = copy.deepcopy(self.data)
            if change == "adversary":
                data["games"][0]["companies"]["AAAHogEx"]["horizon_complete"] = False
            elif change == "errors":
                data["games"][0]["unattributed_errors"] = ["unknown fatal"]
            else:
                data["games"].pop()
            self.assertFalse(healthy(data, 40))


if __name__ == "__main__":
    unittest.main()
