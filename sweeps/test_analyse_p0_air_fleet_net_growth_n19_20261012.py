"""Paired fleet-growth audit must not conflate multiple C66 policies."""
import unittest

from analyse_p0_air_fleet_net_growth_n19_20261012 import analyze


def snap(seed, arm, year, *, policy="reference", ids=(1, 2), profit=10, bad=False):
    return {"seed": seed, "arm": arm, "year": year,
            "duel_policy_id": policy, "ok": True,
            "unresolved_vehicles": [99] if bad else [],
            "lines": [{"mode": "air", "station_ids": [12, 8],
                       "vehicle_financials": [{"vehicle_id": x, "profit_this_year_gbp": profit}
                                              for x in ids]}]}


class NetAIRGrowthTests(unittest.TestCase):
    def report(self):
        snapshots = []
        for seed in (42, 100):
            for arm in ("OpexAI", "AAAHogEx"):
                snapshots += [snap(seed, arm, 1972), snap(seed, arm, 1973,
                             ids=(1, 2, 3) if arm == "OpexAI" else (1, 2), profit=5)]
                snapshots += [snap(seed, arm, 1972, policy="variant", profit=1000),
                              snap(seed, arm, 1973, policy="variant", profit=300)]
        return {"campaign_id": "fixture", "source_bundle_sha256": "sha", "seeds": [42, 100],
                "line_telemetry": {"snapshots": snapshots}}

    def test_only_reference_and_same_incumbent_ids(self):
        result = analyze(self.report())
        self.assertEqual(2, result["paired_n"])
        self.assertEqual(2, result["summary"]["OpexAI"]["expanded"]["matched_active_services_all_seeds"])
        self.assertEqual(4, result["summary"]["OpexAI"]["expanded"]["surviving_aircraft_all_seeds"])
        self.assertEqual(-5, result["summary"]["OpexAI"]["expanded"]["pooled_change_per_survivor_gbp"])
        self.assertEqual(2, result["summary"]["AAAHogEx"]["unchanged"]["matched_active_services_all_seeds"])

    def test_excludes_entire_pair_if_aaa_unresolved(self):
        report = self.report()
        for row in report["line_telemetry"]["snapshots"]:
            if row["seed"] == 100 and row["arm"] == "AAAHogEx" and row["year"] == 1973 and row["duel_policy_id"] == "reference":
                row["unresolved_vehicles"] = [123]
        result = analyze(report)
        self.assertEqual(1, result["paired_n"])
        self.assertEqual([100], result["excluded"])

    def test_duplicate_policy_year_snapshot_rejected(self):
        report = self.report()
        report["line_telemetry"]["snapshots"].append(report["line_telemetry"]["snapshots"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            analyze(report)


if __name__ == "__main__":
    unittest.main()
