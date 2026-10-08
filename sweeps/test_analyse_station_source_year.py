import unittest
from analyse_station_source_year import annual_cases, summarize, bounds_metrics


def analysis(seed=73):
    snapshots = []
    # Leap-free synthetic calendar with genuine month lengths, 25 checkpoints.
    from datetime import date
    for i in range(25):
        day = date(1971 + i // 12, i % 12 + 1, 1).toordinal()
        node = {"station": 7, "cargo": 3, "graph": "0", "compression": 0,
                "membership": [[7, 100]], "xy": 100, "build_date": 0,
                "supply": (day - date(1971, 1, 1).toordinal()) * 10, "last_update": day}
        snapshots.append({"economy_date": day,
            "station_supply": {"ok": True, "economy_date": day, "nodes": [node]},
            "station_sources": {"7": {"owner": 0, "airport": True,
                "b9_own_monthly": 608, "b9_visible_monthly": 304}}})
    return {"snapshots": snapshots, "pass_cargo": 3, "seed": seed, "game_id": str(seed)}


class FutureYearTests(unittest.TestCase):
    def test_frozen_anchor_and_all_months(self):
        a = analysis()
        a["snapshots"][13]["station_sources"]["7"]["b9_visible_monthly"] = 99999
        rows, exclusions = annual_cases(a)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["future_exact_intervals"], 12)
        self.assertAlmostEqual(rows[0]["actual"], rows[0]["b9_visible"])
        self.assertEqual(exclusions, {"incomplete_future_horizon": 1})

    def test_no_imputation_on_compression_or_missing_node(self):
        for change in ("compression", "nodes"):
            a = analysis()
            if change == "compression":
                a["snapshots"][18]["station_supply"]["nodes"][0]["compression"] = 1
            else:
                a["snapshots"][18]["station_supply"]["nodes"] = []
            rows, excluded = annual_cases(a)
            self.assertEqual(rows, [])
            self.assertEqual(excluded["missing_or_inexact_future_interval"], 1)

    def test_every_reserved_seed_must_improve(self):
        a, b = analysis(), analysis(314)
        self.assertTrue(summarize([a, b])["precision_gate_pass"])
        b["snapshots"][12]["station_sources"]["7"]["b9_visible_monthly"] = 1000
        self.assertFalse(summarize([a, b])["precision_gate_pass"])
        b["snapshots"] = b["snapshots"][:20]
        self.assertFalse(summarize([a, b])["precision_gate_pass"])

    def test_error_bounds_cover_every_label_and_crossing(self):
        cases = [{"game_id": "a", "station": 1, "actual_lower": 90, "actual_upper": 110,
                  "b9_own": 200, "b9_visible": 100}]
        report = bounds_metrics(cases)
        self.assertTrue(report["visible_better_for_every_admissible_label"])
        self.assertLess(report["absolute_error_delta_upper"], 0)
        cases[0].update(b9_own=95, b9_visible=105)
        report = bounds_metrics(cases)
        self.assertFalse(report["visible_better_for_every_admissible_label"])
        self.assertEqual(report["absolute_error_delta_lower"], -10)
        self.assertEqual(report["absolute_error_delta_upper"], 10)

    def test_surviving_growth_preserves_annual_label_without_imputation(self):
        a = analysis()
        for snapshot in a["snapshots"][18:]:
            snapshot["station_supply"]["nodes"][0]["membership"].append([8, 200])
        rows, _ = annual_cases(a, bounded=True)
        self.assertEqual(rows, [])
        rows, _ = annual_cases(a, bounded=True, surviving_growth=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["surviving_growth_intervals"], 1)
        self.assertEqual(rows[0]["actual_lower"], rows[0]["actual_upper"])
        self.assertEqual(rows[0]["future_exact_intervals"], 12)


if __name__ == "__main__":
    unittest.main()
