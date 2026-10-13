"""Active-service mode profitability is a descriptive paired audit only."""
import unittest

from analyse_p0_active_mode_profit_20261012 import analyze, profile


def snapshot(seed, arm, year, *, policy="reference", unresolved=False, profit=10):
    return {"seed": seed, "arm": arm, "year": year,
            "duel_policy_id": policy, "ok": True,
            "unresolved_vehicles": [999] if unresolved else [],
            "lines": [{"mode": "air", "vehicle_ids": [seed + year],
                       "profit_this_year_gbp": profit}]}


class ModeProfitTests(unittest.TestCase):
    def test_reject_duplicate_vehicles(self):
        item = snapshot(1, "OpexAI", 1971)
        item["lines"].append(dict(item["lines"][0]))
        with self.assertRaisesRegex(ValueError, "multiple services"):
            profile(item)

    def test_reject_nonfinite_or_missing_vehicle_profit(self):
        item = snapshot(1, "OpexAI", 1971)
        item["lines"][0]["profit_this_year_gbp"] = float("nan")
        with self.assertRaisesRegex(ValueError, "missing vehicle"):
            profile(item)

    def test_unresolved_company_excludes_both_paired_arms(self):
        snaps = [snapshot(seed, arm, year, profit=seed + year)
                 for seed in (1, 2) for arm in ("OpexAI", "AAAHogEx")
                 for year in (1971, 1972, 1973)]
        for item in snaps:
            if item["seed"] == 2 and item["arm"] == "AAAHogEx" and item["year"] == 1973:
                item["unresolved_vehicles"] = [999]
        result = analyze({"seeds": [1, 2], "campaign_id": "test", "source_bundle_sha256": "abc",
                          "line_telemetry": {"snapshots": snaps}})
        self.assertEqual(2, result["by_year"]["1972"]["n"])
        self.assertEqual(1, result["by_year"]["1973"]["n"])
        self.assertEqual([2], result["by_year"]["1973"]["excluded_seeds"])
        self.assertEqual([2], result["same_seed_growth"]["1972_to_1973"]["excluded"])
        self.assertEqual(1, result["by_year"]["1973"]["mean_active_primary_vehicles"]["OpexAI"]["air"])
        self.assertEqual(1974, result["by_year"]["1973"]["pooled_vehicle_profit_per_active_vehicle_gbp"]["OpexAI"]["air"])

    def test_separate_policy_and_reject_duplicates(self):
        snaps = [snapshot(1, arm, year) for arm in ("OpexAI", "AAAHogEx")
                 for year in (1971, 1972, 1973)]
        snaps += [snapshot(1, arm, year, policy="other", profit=1000)
                  for arm in ("OpexAI", "AAAHogEx") for year in (1971, 1972, 1973)]
        report = {"seeds": [1], "campaign_id": "test", "source_bundle_sha256": "abc",
                  "line_telemetry": {"snapshots": snaps}}
        self.assertEqual(10, analyze(report)["by_year"]["1973"]["mean_vehicle_profit_by_mode_gbp"]["OpexAI"]["air"])
        snaps.append(snapshot(1, "OpexAI", 1973))
        with self.assertRaisesRegex(ValueError, "duplicate snapshot"):
            analyze(report)


if __name__ == "__main__":
    unittest.main()
