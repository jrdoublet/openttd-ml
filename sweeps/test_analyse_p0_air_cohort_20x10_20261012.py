"""Air cohort comparisons must pair valid snapshots and preserve ID meaning."""
import unittest

from analyse_p0_air_cohort_20x10_20261012 import analyze, stable_market_cohort


def row(seed, arm, year, *, policy="reference", vehicles=(), unresolved=False):
    return {"seed": seed, "arm": arm, "year": year, "duel_policy_id": policy,
            "ok": True, "unresolved_vehicles": [777] if unresolved else [],
            "lines": [{"mode": "air", "market_key": "air|1,2", "station_ids": [1, 2],
                       "vehicle_financials": [
                {"vehicle_id": ident, "profit_this_year_gbp": 10 * ident} for ident in vehicles]}]}


class AirCohort20Tests(unittest.TestCase):
    def report(self):
        snaps = [row(s, arm, 1972, vehicles=(1, 2)) for s in (42, 100)
                 for arm in ("OpexAI", "AAAHogEx")]
        snaps += [row(s, arm, 1973, vehicles=(1, 3)) for s in (42, 100)
                  for arm in ("OpexAI", "AAAHogEx")]
        return {"seeds": [42, 100], "campaign_id": "fixture", "source_bundle_sha256": "fixture-sha",
                "line_telemetry": {"snapshots": snaps}}

    def test_continuing_distinct_from_new_observed_and_retired(self):
        d = analyze(self.report())
        p = d["aggregates"]["OpexAI"]
        self.assertEqual(1, p["continuing"]["mean_aircraft_per_seed"])
        self.assertEqual(1, p["not_seen_prior_december"]["mean_aircraft_per_seed"])
        self.assertEqual(0.5, p["newly_observed_fraction_of_current"])
        self.assertEqual(10, p["continuing"]["pooled_ytd_profit_per_aircraft_gbp"])

    def test_unresolved_aaa_excludes_opex_in_same_pair(self):
        data = self.report()
        next(r for r in data["line_telemetry"]["snapshots"]
             if r["seed"] == 100 and r["arm"] == "AAAHogEx" and r["year"] == 1973)["unresolved_vehicles"] = [7]
        d = analyze(data)
        self.assertEqual([42], d["paired_seeds"])
        self.assertEqual([100], d["excluded"])

    def test_duplicate_snapshot_disallowed(self):
        data = self.report()
        data["line_telemetry"]["snapshots"].append(data["line_telemetry"]["snapshots"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            analyze(data)

    def test_same_aircraft_not_mistaken_for_same_market(self):
        a = {1: ("air|1,2", (1, 2), 10), 2: ("air|3,4", (3, 4), 10)}
        b = {1: ("air|1,2", (1, 2), 20), 2: ("air|4,5", (4, 5), 30)}
        result = stable_market_cohort(b, a)
        self.assertEqual(2, result["continuing_count"])
        self.assertEqual(1, result["same_market_count"])
        self.assertEqual(10, result["same_market_ytd_profit_change_gbp"])


if __name__ == "__main__":
    unittest.main()
