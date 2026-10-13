"""Contrats hôte P2 : aucune estimation ne devient un coefficient de politique."""
from __future__ import annotations

import unittest

from analyse_p2_recal_oos_20261013 import (
    analyze, arm_summary, candidate_factors, clustered_bootstrap,
    extract_provisional, parse_seed, witness_constructions,
)


def obs(seed, line, arm, ratio, same=True):
    return dict(seed=seed, line=str(line), arm=arm,
                candidate_same_as_purchase=same, raw_ratio=ratio,
                amort_adjusted_ratio=ratio)


class P2RecalContracts(unittest.TestCase):
    def test_seed_identity_requires_log_name(self):
        self.assertEqual(parse_seed("scores_p2_shadow_seed314159_r0.log"), 314159)
        with self.assertRaises(ValueError):
            parse_seed("reference.log")

    def test_first_mature_exercise_once_per_seed_line_and_actual_amort(self):
        source = {
            "sources": {
                "scores_p2_shadow_seed42_r0.log": {
                    "purchases": {"7": {"date": "1970-03-01",
                                        "engine": "228", "c121_actual_n": "1"}},
                    "mature_annual": [
                        dict(line="7", arm="hubsite", exercise=1972, pred_prof="100",
                             real_prof="60", model_same_at_election_and_purchase=True,
                             provisional_comparable=True),
                        dict(line="7", arm="hubsite", exercise=1973, pred_prof="100",
                             real_prof="80", model_same_at_election_and_purchase=True,
                             provisional_comparable=True),
                    ],
                },
            },
        }
        logs = {42: ["[0] [I] C121_BUILD line=7 arm=hubsite engine=228 "
                     "actual_n=1 actual_amort=10\n"]}
        observations, counts = extract_provisional(source, logs)
        self.assertEqual(counts["provisional_line_years"], 2)
        self.assertEqual(counts["unique_provisional_lines"], 1)
        self.assertEqual(observations[0]["exercise"], 1972)
        self.assertEqual(observations[0]["raw_ratio"], .6)
        self.assertEqual(observations[0]["amort_adjusted_ratio"], .5)

    def test_no_cross_bundle_mixing(self):
        # Fail before reading any file: provenance and OOS seed split are hard gates.
        sources = {"sources": {f"scores_p2_shadow_seed{s}_r0.log": {}
                                for s in (42, 314)}}
        manifest = {"source_bundle": {"sha256": "bundle-one"},
                    "campaign_id": "p2"}
        with self.assertRaisesRegex(ValueError, "intersect"):
            analyze(sources, manifest, None, validation_seeds=[42])
        with self.assertRaisesRegex(ValueError, "provenance mismatch"):
            analyze(sources, manifest, None, campaign={
                "campaign_id": "other", "source_bundle_sha256": "bundle-two",
            })

    def test_seed_median_prevents_repeated_lines_from_dominating(self):
        rows = ([obs(1, n, "hubsite", .2) for n in range(10)] +
                [obs(2, 20, "hubsite", .6), obs(3, 21, "hubsite", .8)])
        report = arm_summary(rows)["hubsite"]
        self.assertEqual(report["lines"], 12)
        self.assertEqual(report["seeds"], 3)
        self.assertEqual(report["median_of_seed_medians"], .6)
        self.assertEqual(report["median_of_lines_descriptive_only"], .2)

    def test_dont_fit_family_without_3_seeds(self):
        rows = [obs(1, "a", "hubhub", .4), obs(1, "b", "hubhub", .5),
                obs(2, "c", "hubhub", .6), obs(2, "d", "hubhub", .6)]
        self.assertNotIn("air:hubhub", candidate_factors(rows, "raw_ratio"))

    def test_amortization_and_same_price_are_separate_sensitivity_profiles(self):
        rows = [obs(1, 1, "newpair", .2, False), obs(2, 2, "newpair", .4),
                obs(3, 3, "newpair", .8), obs(4, 4, "newpair", .9)]
        all_factors = candidate_factors(rows, "amort_adjusted_ratio")
        same_price = candidate_factors([r for r in rows if r["candidate_same_as_purchase"]],
                                       "amort_adjusted_ratio")
        self.assertIn("air:newpair", all_factors)
        self.assertNotIn("air:newpair", same_price)

    def test_cluster_bootstrap_reproducible_by_seed(self):
        rows = [obs(1, 1, "newpair", .3), obs(1, 2, "newpair", .4),
                obs(2, 3, "newpair", .8), obs(3, 4, "hubsite", .4),
                obs(1, 5, "hubsite", .5)]
        a = clustered_bootstrap(rows, resamples=150, seed=0)
        b = clustered_bootstrap(rows, resamples=150, seed=0)
        self.assertEqual(a, b)
        self.assertEqual(a["by_family"]["newpair"]["support_seed_count"], 2)
        self.assertEqual(a["by_family"]["hubhub"]["support_seed_count"], 0)

    def test_witness_build_is_not_counterfactual(self):
        flip = dict(before_key=["air", "pax", "hubsite", "10", "20", "0", "228", "-1"],
                    after_key=["air", "pax", "newpair", "20", "30", "0", "228", "-1"],
                    year="1970", month="12", day="19")
        lines = ["[0] [I] OPEX 1970-12-21 AIR_BUILD src=10 dst=20 "
                 "arm=hubsite engine=228\n"]
        witness = witness_constructions(lines, flip)
        self.assertEqual(witness["witness_legacy_air_build_date"], "1970-12-21")
        self.assertEqual(witness["witness_alternative_air_build_count"], 0)
        self.assertIsNone(witness["counterfactual_built"])


if __name__ == "__main__":
    unittest.main()
