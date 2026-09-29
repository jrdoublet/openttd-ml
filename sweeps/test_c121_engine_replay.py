import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse_c121_engine_replay import analyse


def build(complete=1, known=2, total=2, changed=1):
    return {
        "engine": 1,
        "replay_engine_total": total,
        "replay_engine_known": known,
        "replay_engine_evaluated": known,
        "replay_engine_complete": complete,
        "replay_pass_engine": 1,
        "replay_pass_n": 2,
        "replay_pass_revenue": 100,
        "replay_pass_profit": 70,
        "replay_pass_score": 3.0,
        "replay_mail_engine": 2 if changed else 1,
        "replay_mail_n": 3,
        "replay_mail_revenue": 120,
        "replay_mail_profit": 80,
        "replay_mail_score": 4.0,
        "replay_mail_changed": changed,
        "replay_shadow_ticks": 2,
        "replay_shadow_ops": 600,
        "eval_ticks": 1,
        "eval_ops": 300,
    }


class TestC121EngineReplay(unittest.TestCase):
    def test_partial_coverage_is_reported_but_stability_still_uses_observed_subset(self):
        payload = {"rows": [{"seed": 42, "c121_builds": [build(), build(0, 1, 2)]}]}
        result = analyse(payload)
        self.assertEqual(result["coverage"]["learning_event_count"], 2)
        self.assertEqual(result["coverage"]["complete_count"], 1)
        self.assertEqual(result["mail_stability"]["eligible_count"], 1)
        self.assertEqual(result["mail_stability"]["changed_count"], 1)

    def test_pass_to_mail_score_comparison_keeps_same_objective(self):
        payload = {"rows": [{"seed": 7, "c121_builds": [build(), build(changed=0)]}]}
        result = analyse(payload)
        stability = result["mail_stability"]
        self.assertEqual(stability["eligible_count"], 2)
        self.assertEqual(stability["changed_count"], 1)
        self.assertEqual(stability["changed_fraction"], 0.5)
        self.assertEqual(stability["fleet_delta_mail_minus_pass"]["median"], 1.0)
        self.assertEqual(stability["profit_delta_mail_minus_pass"]["median"], 10.0)
        self.assertAlmostEqual(stability["score_ratio_mail_over_pass"]["median"], 4.0 / 3.0)


if __name__ == "__main__":
    unittest.main()
