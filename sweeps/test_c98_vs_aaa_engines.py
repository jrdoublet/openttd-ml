import unittest

from sweeps.diag_c98_vs_aaa_engines import summarize


def aircraft(engine, profit, full=True, vehicle_id=1):
    return {
        "vehicle_id": vehicle_id,
        "engine": engine,
        "engine_label": str(engine),
        "build_year": 1970,
        "profit_last_year_gbp": profit,
        "full_prior_year": full,
        "passenger_capacity": 100,
        "book_value": 1000,
    }


class C98VsAaaEngineTests(unittest.TestCase):
    def test_summary_filters_partial_prior_year_aircraft(self):
        rows = [{
            "seed": 42, "year": 1975, "date": "1975-12-01",
            "companies": {
                "0": {"aircraft": [aircraft(1, 100), aircraft(2, 999, False, 2)], "lines": []},
                "1": {"aircraft": [aircraft(3, 200)], "lines": []},
            },
        }]
        report = summarize(rows)
        self.assertEqual(report["opex"]["full_prior_year_aircraft"], 1)
        self.assertEqual(report["opex"]["profit_last_year_per_plane_gbp"]["median"], 100.0)

    def test_common_service_uses_full_year_vehicles_and_profit(self):
        rows = [{
            "seed": 7, "year": 1975, "date": "1975-12-01",
            "companies": {
                "0": {"aircraft": [aircraft(1, 100)], "lines": [{
                    "service_key": "air|1,2|cargo=0", "full_year_vehicles": 1,
                    "full_year_profit_last_year_gbp": 100.0, "full_year_engines": {"1": 1},
                }]},
                "1": {"aircraft": [aircraft(2, 400)], "lines": [{
                    "service_key": "air|1,2|cargo=0", "full_year_vehicles": 2,
                    "full_year_profit_last_year_gbp": 400.0, "full_year_engines": {"2": 2},
                }]},
            },
        }]
        common = summarize(rows)["same_market_same_cargo_full_prior_year"]
        self.assertEqual(common["services"], 1)
        self.assertEqual(common["opex_profit_per_plane_gbp"], 100.0)
        self.assertEqual(common["aaa_profit_per_plane_gbp"], 200.0)
        self.assertEqual(common["profit_per_plane_ratio_aaa_over_opex"], 2.0)


if __name__ == "__main__":
    unittest.main()
