import unittest

from analyse_c121_pax_flux import forecast_cases, fit_blend, metrics, quality


def window(bucket, pax=100):
    return {"seed": 42, "line": 2, "age_bucket": bucket, "period_days": 30,
        "pax": pax, "samples": 15, "live_avg": 1, "live_last": 1, "engine": 228,
        "build_engine": 228, "engine_changes": 0, "mixed_engine_samples": 0,
        "invalid_order_samples": 0, "unobserved_transitions": 0,
        "c121_actual_pax_pm": 90, "c121_actual_n": 1, "arm": "hubsite",
        "load_factor": 0.5, "cap_avg": 100, "wait_a": 0, "wait_b": 0}


class FluxForecastTests(unittest.TestCase):
    def test_forecast_uses_only_past_not_future(self):
        events = [window(i, 100 if i < 24 else 200) for i in range(36)]
        cases, _ = forecast_cases(events)
        self.assertEqual(len(cases), 1)
        self.assertAlmostEqual(cases[0]["observed_360"], 100 * 30.4 / 30)
        self.assertAlmostEqual(cases[0]["actual"], 200 * 30.4 / 30)

    def test_unknown_and_bad_observations_are_not_zero(self):
        e = window(1)
        e["pax"] = None
        self.assertFalse(quality(e))
        e = window(1)
        e["unobserved_transitions"] = 1
        self.assertFalse(quality(e))
        events = [window(i) for i in range(36) if i != 20]
        self.assertEqual(forecast_cases(events)[0], [])

    def test_fleet_change_excluded_and_initial_match_separate(self):
        events = [window(i) for i in range(36)]
        for e in events:
            e["live_last"] = e["live_avg"] = 2
        cases, _ = forecast_cases(events)
        self.assertEqual(len(cases), 1)
        self.assertFalse(cases[0]["initial_fleet_match"])
        events[25]["live_last"] = events[25]["live_avg"] = 3
        self.assertEqual(forecast_cases(events)[0], [])

    def test_full_plane_demand_is_censored(self):
        events = [window(i) for i in range(36)]
        for e in events:
            e["load_factor"] = 0.95
        row = forecast_cases(events)[0][0]
        self.assertTrue(row["past_capacity_censored"])
        self.assertFalse(row["future_demand_limited"])

    def test_blend_trains_by_arm_without_pooling_unmatched_fleets(self):
        rows = [{"arm": "hubsite", "initial_fleet_match": True,
            "model_build": 400, "observed_360": 100, "actual": 100},
            {"arm": "hubsite", "initial_fleet_match": False,
            "model_build": 400, "observed_360": 100, "actual": 400}]
        weights = fit_blend(rows)
        self.assertEqual(weights["hubsite"], 1)
        self.assertIsNone(weights["newpair"])

    def test_wape_preserves_flux_weighting_and_zero_denominator(self):
        rows = [{"seed": 1, "line": 1, "actual": 10, "forecast": 20},
                {"seed": 1, "line": 2, "actual": 100, "forecast": 100}]
        self.assertAlmostEqual(metrics(rows, "forecast")["wape"], 10 / 110)
        self.assertIsNone(metrics([], "forecast")["wape"])

    def test_partial_exploration_does_not_rename_old_months_as_recent(self):
        events = [window(i) for i in range(36)]
        events[23]["invalid_order_samples"] = 1
        self.assertEqual(forecast_cases(events)[0], [])
        row = forecast_cases(events, exploratory_partial=True)[0][0]
        self.assertIsNone(row["observed_90"])
        self.assertIsNone(row["observed_180"])
        self.assertEqual(row["past_qualified_months"], 11)
        self.assertIsNone(metrics([row], "observed_90")["wape"])


if __name__ == "__main__":
    unittest.main()
