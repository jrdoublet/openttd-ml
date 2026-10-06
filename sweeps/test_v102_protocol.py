"""Protocole V102 : Wilcoxon exact, bootstrap percentile, gain_short et non_erosion.

Aucun moteur, aucun Docker. Les règles signs20 et mean40 restent celles du
harnais : mêmes exigences, mêmes clés du dict decision_rule.
"""
from __future__ import annotations

import random
import statistics
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import openttdlab
except ImportError:
    fake_lab = types.ModuleType("openttdlab")
    for name in ("bananas_ai", "bananas_ai_library", "local_folder", "run_experiments"):
        setattr(fake_lab, name, mock.MagicMock())
    sys.modules["openttdlab"] = fake_lab

from bench_1v1_5y_20seeds import (  # noqa: E402
    DECISION_RULES,
    SEEDS,
    SEEDS_40,
    annotate_paired_comparison_wilcoxon,
    bootstrap_mean_ci,
    build_policy_comparison,
    c66_threshold_specification_error,
    default_seeds_for_rule,
    exact_wilcoxon_signed_rank_p,
    paired_metric_display_p,
    policy_adoption_eligibility,
    resolve_min_useful_primary_delta,
    wilcoxon_signed_rank_statistic,
)


CAMPAIGN_DELTAS = [
    -464967, 389424, 245755, 30906, 513843, -209618, 725418, -94101, -276303, 276532,
    -333463, 117613, 475093, 168949, 131686, -392366, -133627, 333908, 949410, 383819,
]

SIGNS20_RULE_KEYS = {
    "required_pairs",
    "required_wins",
    "max_sign_test_p_exclusive",
    "min_useful_primary_delta",
    "value_guard_max_loss_pct",
    "primary_rule",
    "value_guard_rule",
    "all_planned_pairs_required_for_verdict",
}
MEAN40_RULE_KEYS = {
    "rule",
    "required_pairs",
    "confidence_level",
    "min_useful_primary_delta",
    "value_guard_max_loss_pct",
    "primary_rule",
    "value_guard_rule",
    "all_planned_pairs_required_for_verdict",
}


def comparison(
    deltas,
    *,
    rule,
    years,
    seeds=None,
    absolute=5.0,
    pct=None,
    required_seeds=None,
    required_years=None,
    reference_profit=100.0,
    trajectory_profit=None,
    variant_value=1000.0,
    reference_value=1000.0,
    starting_year=1970,
):
    """Paires synthétiques. Seul profit_year varie ; le bootstrap des autres séries est constant."""
    if seeds is None:
        seeds = list(range(1, len(deltas) + 1))
    summary = []
    rows = []
    terminal_year = int(starting_year) + int(years) - 1
    for seed, delta in zip(seeds, deltas):
        for policy, opex_profit, opex_value in (
            ("reference", reference_profit, reference_value),
            ("variant", reference_profit + delta, variant_value),
        ):
            for arm, profit_value, company_value in (
                ("OpexAI", opex_profit, opex_value),
                ("AAAHogEx", 90.0, 1100.0),
            ):
                record = {
                    "duel_policy_id": policy,
                    "arm": arm,
                    "seed": seed,
                    "repeat": 0,
                    "run_ok": True,
                    "game_ok": True,
                    "status": "complete",
                    "profit_year": profit_value,
                    "company_value": company_value,
                    "profit": 10.0,
                    "performance_history": 100,
                    "median_station_rating": 100,
                    "primary_vehicles": 10,
                }
                summary.append(record)
                row_profit = profit_value
                if trajectory_profit is not None and policy == "reference" and arm == "OpexAI":
                    row_profit = trajectory_profit
                rows.append({
                    **record,
                    "profit_year": row_profit,
                    "run": [arm, seed, 0],
                    "date": f"{terminal_year}-12-01",
                })
    return build_policy_comparison(
        summary,
        rows,
        seeds=seeds,
        repeats=1,
        reference_policy_id="reference",
        variant_policy_id="variant",
        primary_metric="profit_year",
        min_useful_primary_delta=absolute,
        min_useful_primary_delta_pct=pct,
        required_seeds=required_seeds,
        required_years=required_years,
        value_guard_max_loss_pct=5.0,
        starting_year=starting_year,
        years=years,
        decision_rule=rule,
    )


class WilcoxonTests(unittest.TestCase):
    def test_hand_cases(self):
        self.assertEqual(exact_wilcoxon_signed_rank_p([1, -2, 3, -4, 5]), 0.8125)
        self.assertEqual(exact_wilcoxon_signed_rank_p([1, 2, 3, 4, 5, 6]), 0.03125)
        self.assertEqual(exact_wilcoxon_signed_rank_p([0, 1, -1, 2, 2, -3]), 0.9375)

    def test_all_zero_is_none(self):
        self.assertIsNone(exact_wilcoxon_signed_rank_p([0, 0.0, -0.0]))
        self.assertIsNone(exact_wilcoxon_signed_rank_p([]))

    def test_campaign_vector(self):
        stat = wilcoxon_signed_rank_statistic(CAMPAIGN_DELTAS)
        self.assertEqual(stat["w_plus"], 145)
        self.assertEqual(stat["expectation"], 105)
        self.assertEqual(stat["n"], 20)
        self.assertAlmostEqual(stat["p"], 0.142906189, delta=1e-9)
        self.assertAlmostEqual(exact_wilcoxon_signed_rank_p(CAMPAIGN_DELTAS), 0.142906189, delta=1e-9)


class BootstrapTests(unittest.TestCase):
    def test_deterministic_and_brackets_a_positive_mean(self):
        sample = [10, 12, 11, 13, 15, 9, 14]
        first = bootstrap_mean_ci(sample)
        second = bootstrap_mean_ci(sample)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)
        mean = statistics.mean(sample)
        self.assertLess(first[0], mean)
        self.assertLess(mean, first[1])

    def test_empty_is_missing(self):
        self.assertEqual(bootstrap_mean_ci([]), (None, None))

    def test_percentiles_match_random_choices(self):
        values = [1.5, -2.0, 4.0, 8.0, 3.0]
        resamples = 500
        seed = 7
        observed = bootstrap_mean_ci(values, resamples=resamples, seed=seed, confidence=0.95)
        generator = random.Random(seed)
        means = sorted(
            statistics.mean(generator.choices(values, k=len(values)))
            for _ in range(resamples)
        )
        expected = (means[int(0.025 * resamples)], means[int(0.975 * resamples)])
        self.assertEqual(observed, expected)


class EligibilityTests(unittest.TestCase):
    def test_signs20_and_mean40_are_unchanged(self):
        signs = policy_adoption_eligibility(list(range(20)), 1, 10, "signs20")
        self.assertTrue(signs["eligible"])
        self.assertEqual(signs["required_distinct_seeds"], 20)
        self.assertEqual(signs["required_years"], 10)
        self.assertEqual(signs["reasons"], [])
        ignored = policy_adoption_eligibility(
            list(range(20)), 1, 10, "signs20", required_seeds=5, required_years=1,
        )
        self.assertTrue(ignored["eligible"])
        self.assertEqual(ignored["required_distinct_seeds"], 20)
        self.assertEqual(ignored["required_years"], 10)
        short = policy_adoption_eligibility(list(range(20)), 1, 6, "signs20")
        self.assertFalse(short["eligible"])
        self.assertEqual(short["required_years"], 10)
        self.assertIn("horizon_not_10_years", short["reasons"])

        mean40 = policy_adoption_eligibility(
            list(range(40)), 1, 10, "mean40", required_seeds=20, required_years=3,
        )
        self.assertTrue(mean40["eligible"])
        self.assertEqual(mean40["required_distinct_seeds"], 40)
        self.assertEqual(mean40["required_years"], 10)
        too_few = policy_adoption_eligibility(list(range(20)), 1, 10, "mean40")
        self.assertFalse(too_few["eligible"])
        self.assertIn("distinct_seed_count", too_few["reasons"])

    def test_gain_short_and_non_erosion(self):
        gain = policy_adoption_eligibility(list(range(40)), 1, 3, "gain_short")
        self.assertTrue(gain["eligible"])
        self.assertEqual(gain["required_distinct_seeds"], 40)
        self.assertEqual(gain["required_years"], 3)
        refused = policy_adoption_eligibility(list(range(20)), 1, 3, "gain_short")
        self.assertFalse(refused["eligible"])
        self.assertIn("distinct_seed_count", refused["reasons"])
        custom = policy_adoption_eligibility(
            list(range(10)), 1, 2, "gain_short", required_seeds=10, required_years=2,
        )
        self.assertTrue(custom["eligible"])
        self.assertEqual(custom["required_years"], 2)

        erosion = policy_adoption_eligibility(list(range(20)), 1, 10, "non_erosion")
        self.assertTrue(erosion["eligible"])
        self.assertEqual(erosion["required_distinct_seeds"], 20)
        self.assertEqual(erosion["required_years"], 10)
        ignored = policy_adoption_eligibility(
            list(range(20)), 1, 10, "non_erosion", required_seeds=40, required_years=3,
        )
        self.assertTrue(ignored["eligible"])
        self.assertEqual(ignored["required_distinct_seeds"], 20)
        self.assertEqual(ignored["required_years"], 10)

    def test_default_seed_lists_keep_the_historical_rules(self):
        self.assertEqual(default_seeds_for_rule("signs20"), list(SEEDS))
        self.assertEqual(default_seeds_for_rule("signs20", 7), list(SEEDS))
        self.assertEqual(default_seeds_for_rule("mean40"), list(SEEDS_40))
        self.assertEqual(default_seeds_for_rule("mean40", 7), list(SEEDS_40))
        self.assertEqual(default_seeds_for_rule("non_erosion"), list(SEEDS))
        self.assertEqual(default_seeds_for_rule("non_erosion", 7), list(SEEDS))
        self.assertEqual(default_seeds_for_rule("gain_short"), list(SEEDS_40))
        self.assertEqual(default_seeds_for_rule("gain_short", 10), list(SEEDS_40[:10]))
        self.assertEqual(DECISION_RULES, ("signs20", "mean40", "gain_short", "non_erosion"))


class ThresholdTests(unittest.TestCase):
    def test_relative_threshold_is_pct_times_reference_mean(self):
        resolved, reference_mean = resolve_min_useful_primary_delta(None, 4, [1000, 3000])
        self.assertEqual(reference_mean, 2000)
        self.assertEqual(resolved, 80)

    def test_comparison_uses_terminal_reference_opex_not_the_summary(self):
        result = comparison(
            [0, 0, 0, 0],
            rule="gain_short",
            years=1,
            absolute=None,
            pct=10,
            required_seeds=4,
            required_years=1,
            reference_profit=100.0,
            trajectory_profit=2500.0,
        )
        rule = result["decision_rule"]
        self.assertEqual(rule["min_useful_primary_delta_pct"], 10.0)
        self.assertEqual(rule["reference_terminal_profit_mean"], 2500.0)
        self.assertEqual(rule["reference_terminal_year"], 1970)
        self.assertEqual(rule["min_useful_primary_delta"], 250.0)
        self.assertAlmostEqual(
            rule["min_useful_primary_delta"],
            rule["min_useful_primary_delta_pct"] / 100.0 * rule["reference_terminal_profit_mean"],
        )

    def test_exactly_one_threshold_for_the_new_rules(self):
        self.assertIsNone(c66_threshold_specification_error("signs20", 50000, None))
        self.assertIn(
            "min-useful-primary-delta doit",
            c66_threshold_specification_error("signs20", None, None),
        )
        self.assertIn(
            "min-useful-primary-delta doit",
            c66_threshold_specification_error("mean40", None, 4),
        )
        self.assertIsNotNone(c66_threshold_specification_error("signs20", 1, 4))
        self.assertIsNone(c66_threshold_specification_error("gain_short", None, 4))
        self.assertIsNone(c66_threshold_specification_error("non_erosion", 50000, None))
        self.assertIsNotNone(c66_threshold_specification_error("gain_short", 1, 4))
        self.assertIsNotNone(c66_threshold_specification_error("non_erosion", None, None))
        with self.assertRaises(ValueError):
            comparison(
                [1], rule="gain_short", years=1, absolute=5, pct=4,
                required_seeds=1, required_years=1,
            )
        with self.assertRaises(ValueError):
            comparison(
                [1], rule="non_erosion", years=10, absolute=None, pct=None,
            )


class DisplayTests(unittest.TestCase):
    def test_zero_wilcoxon_is_not_treated_as_missing(self):
        present = {"wilcoxon_p": 0.0, "sign_test_p": 0.5}
        self.assertEqual(paired_metric_display_p(present), 0.0)
        self.assertEqual(present.get("wilcoxon_p") or present.get("sign_test_p"), 0.5)
        self.assertEqual(
            f"p={paired_metric_display_p(present):.4f}",
            "p=0.0000",
        )
        self.assertEqual(
            paired_metric_display_p({"wilcoxon_p": None, "sign_test_p": 0.25}),
            0.25,
        )
        self.assertEqual(paired_metric_display_p({"sign_test_p": 0.25}), 0.25)

    def test_annotation_fills_the_field_the_report_reads(self):
        differences = [1, -2, 3, -4, 5]
        comparison_row = {"metrics": {"profit_year": {
            "paired_differences": [
                {"seed": index, "difference": value}
                for index, value in enumerate(differences)
            ],
            "sign_test_p": 1.0,
        }}}
        annotate_paired_comparison_wilcoxon([comparison_row])
        metric = comparison_row["metrics"]["profit_year"]
        self.assertEqual(metric["wilcoxon_p"], 0.8125)
        self.assertEqual(paired_metric_display_p(metric), 0.8125)
        self.assertNotEqual(paired_metric_display_p(metric), metric["sign_test_p"])
        source = Path(__file__).resolve().parent.joinpath("bench_1v1_5y_20seeds.py").read_text(
            encoding="utf-8",
        )
        self.assertNotIn('m.get("wilcoxon_p") or m.get("sign_test_p")', source)


class DecisionTests(unittest.TestCase):
    def test_historical_rule_records_and_verdicts_stay(self):
        signs = comparison([10] * 20, rule="signs20", years=10, absolute=5)
        self.assertEqual(set(signs["decision_rule"]), SIGNS20_RULE_KEYS)
        self.assertEqual(signs["decision_rule"]["required_pairs"], 20)
        self.assertEqual(signs["decision_rule"]["required_wins"], 15)
        self.assertEqual(signs["verdict"], "pass")
        self.assertTrue(signs["sign_pass"])
        self.assertIsNone(signs["ci_pass"])
        delta = signs["aggregates"]["profit_year"]["policy_delta"]
        self.assertLess(delta["sign_test_p"], 0.05)
        self.assertLess(delta["wilcoxon_p"], 0.05)
        self.assertEqual(delta["mean_bootstrap_95pct_ci"], [10.0, 10.0])
        self.assertEqual(delta["bootstrap_resamples"], 20000)
        self.assertEqual(delta["bootstrap_seed"], 0)
        self.assertEqual(signs["adoption_protocol"]["required_years"], 10)

        mean40 = comparison([20] * 40, rule="mean40", years=10, absolute=5)
        self.assertEqual(set(mean40["decision_rule"]), MEAN40_RULE_KEYS)
        self.assertEqual(mean40["decision_rule"]["rule"], "mean40")
        self.assertEqual(mean40["decision_rule"]["required_pairs"], 40)
        self.assertEqual(mean40["verdict"], "pass")
        self.assertTrue(mean40["ci_pass"])
        self.assertEqual(mean40["adoption_protocol"]["required_years"], 10)

    def test_gain_short_gates(self):
        passed = comparison([100] * 40, rule="gain_short", years=3, absolute=5)
        self.assertEqual(passed["verdict"], "pass")
        self.assertTrue(passed["primary_pass"])
        self.assertTrue(passed["ci_pass"])
        self.assertTrue(passed["value_guard_pass"])
        self.assertEqual(passed["decision_rule"]["required_pairs"], 40)
        self.assertEqual(passed["decision_rule"]["required_years"], 3)
        self.assertIsNone(passed["decision_rule"]["min_useful_primary_delta_pct"])
        self.assertEqual(passed["decision_rule"]["min_useful_primary_delta"], 5.0)

        mean_too_small = comparison([10] * 40, rule="gain_short", years=3, absolute=50)
        self.assertEqual(mean_too_small["verdict"], "fail_primary")
        self.assertTrue(mean_too_small["ci_pass"])
        self.assertFalse(mean_too_small["primary_mean_pass"])

        ci_crosses_zero = comparison(
            [50] * 20 + [-40] * 20, rule="gain_short", years=3, absolute=5,
        )
        primary = ci_crosses_zero["aggregates"]["profit_year"]["policy_delta"]
        self.assertGreaterEqual(primary["mean"], 5)
        self.assertLess(primary["wilcoxon_p"], 0.05)
        self.assertLessEqual(primary["mean_bootstrap_95pct_ci"][0], 0)
        self.assertEqual(ci_crosses_zero["verdict"], "fail_primary")
        self.assertFalse(ci_crosses_zero["ci_pass"])

        guard = comparison(
            [100] * 40, rule="gain_short", years=3, absolute=5, variant_value=800.0,
        )
        self.assertEqual(guard["verdict"], "fail_value_guard")
        self.assertTrue(guard["primary_pass"])
        self.assertFalse(guard["value_guard_pass"])

        diagnostic = comparison([100] * 20, rule="gain_short", years=3, absolute=5)
        self.assertEqual(diagnostic["verdict"], "diagnostic_only")
        self.assertIsNone(diagnostic["primary_pass"])
        self.assertFalse(diagnostic["adoption_sample_complete"])

    def test_non_erosion_is_unilateral(self):
        mixed = comparison(
            [-30] * 10 + [20] * 10, rule="non_erosion", years=10, absolute=1_000_000,
        )
        primary = mixed["aggregates"]["profit_year"]["policy_delta"]
        self.assertLess(primary["mean"], 0)
        self.assertGreaterEqual(primary["mean_bootstrap_95pct_ci"][1], 0)
        self.assertEqual(mixed["decision_rule"]["min_useful_primary_delta"], 1_000_000.0)
        self.assertIsNone(mixed["primary_mean_pass"])
        self.assertEqual(mixed["verdict"], "pass")
        self.assertTrue(mixed["primary_pass"])
        self.assertEqual(mixed["decision_rule"]["required_pairs"], 20)
        self.assertEqual(mixed["decision_rule"]["required_years"], 10)

        loss = comparison([-100] * 20, rule="non_erosion", years=10, absolute=5)
        self.assertLess(loss["aggregates"]["profit_year"]["policy_delta"]["mean_bootstrap_95pct_ci"][1], 0)
        self.assertEqual(loss["verdict"], "fail_primary")
        self.assertFalse(loss["primary_pass"])
        self.assertTrue(loss["value_guard_pass"])

        untouched = comparison([0] * 20, rule="non_erosion", years=10, absolute=5)
        self.assertEqual(untouched["verdict"], "pass")

        guard = comparison(
            [0] * 20, rule="non_erosion", years=10, absolute=5, variant_value=800.0,
        )
        self.assertEqual(guard["verdict"], "fail_value_guard")
        self.assertTrue(guard["primary_pass"])
        self.assertFalse(guard["value_guard_pass"])


if __name__ == "__main__":
    unittest.main()
