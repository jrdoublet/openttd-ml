"""Contrats du diagnostic V242 : proxy de rabattement et pic d'attente."""

import unittest

from v242_feeder_diag import (
    airport_endpoints,
    catchment_summary,
    classify_road_lines,
    latest_company_rows,
    mode_passenger_endpoints,
    summarize_company_rows,
    summarize_line_telemetry,
    summarize_snapshot,
)


def _company(date, slot, arm, policy, seed, road, air=0, rail=0, profit=0):
    return {
        "date": date,
        "policy_id": policy,
        "company_slot": slot,
        "run": [arm, seed, 0],
        "vehs_chunk_valid": True,
        "primary_vehicles": road + air + rail,
        "primary_vehicles_by_mode": {"road": road, "air": air, "rail": rail, "water": 0},
        "stations_by_facility": {"rail": 1, "truck": 0, "bus": road, "airport": 1 if air else 0, "dock": 0},
        "profit_year": profit,
        "company_value": 1000,
        "median_station_rating": 50,
        "air_passenger_capacity": air * 30,
    }


def _line(mode, stations, vehicles, profit_last, capacity=None, airport_at=None, waiting=None, rating=None):
    endpoints = []
    for station_id in stations:
        cargo = {}
        if waiting is not None or rating is not None:
            cargo["0"] = {
                "rated": rating is not None,
                "rating": rating,
                "max_waiting_cargo": waiting,
            }
        endpoints.append({
            "station_id": station_id,
            "town_id": station_id,
            "airport": {"type": 1} if airport_at is not None and station_id in airport_at else None,
            "cargo": cargo,
        })
    return {
        "mode": mode,
        "station_ids": list(stations),
        "vehicles": vehicles,
        "profit_last_year_gbp": profit_last,
        "profit_this_year_gbp": profit_last / 2,
        "capacity_by_cargo": {"0": capacity if capacity is not None else vehicles * 30},
        "endpoint_cargo_stats": endpoints,
    }


class LatestCompanyTests(unittest.TestCase):
    def test_keeps_the_latest_date_only(self):
        rows = [
            _company("1979-06-01", 1, "AAAHogEx", "reference", 42, road=10),
            _company("1979-12-01", 1, "AAAHogEx", "reference", 42, road=166),
            _company("1970-01-01", 1, "AAAHogEx", "reference", 42, road=0),
        ]
        kept = latest_company_rows(rows)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["primary_vehicles_by_mode"]["road"], 166)

    def test_invalid_vehicle_chunk_is_dropped(self):
        row = _company("1979-12-01", 1, "AAAHogEx", "reference", 42, road=3)
        row["vehs_chunk_valid"] = False
        self.assertEqual(latest_company_rows([row]), [])

    def test_groups_do_not_mix_policies(self):
        rows = [
            _company("1979-12-01", 1, "AAAHogEx", "reference", 42, road=100, profit=10),
            _company("1979-12-01", 1, "AAAHogEx", "variant", 42, road=40, profit=5),
        ]
        report = summarize_company_rows(rows)
        by_policy = {item["policy_id"]: item["vehicles"]["road"]["mean"] for item in report}
        self.assertEqual(by_policy, {"reference": 100, "variant": 40})

    def test_aaa_rows_stay_split_by_duel_policy(self):
        left = _company("1979-12-01", 1, "AAAHogEx", "AAAHogEx", 42, road=100)
        right = _company("1979-12-01", 1, "AAAHogEx", "AAAHogEx", 42, road=200)
        left["duel_policy_id"] = "reference"
        right["duel_policy_id"] = "variant"
        report = summarize_company_rows([left, right])
        by_duel = {item["policy_id"]: item["vehicles"]["road"]["mean"] for item in report}
        self.assertEqual(by_duel, {"reference": 100, "variant": 200})
        self.assertEqual({item["company_policy_id"] for item in report}, {"AAAHogEx"})


class FeederProxyTests(unittest.TestCase):
    def test_joined_airport_stop_counts_as_feeder(self):
        lines = [
            _line("air", [10, 11], 2, 50000, capacity=80, airport_at={10, 11}),
            _line("road", [10, 20], 4, 1000),
            _line("road", [30, 31], 2, 200),
        ]
        split = classify_road_lines(lines)
        self.assertEqual(len(split["feeder"]), 1)
        self.assertTrue(split["feeder"][0]["touches_air"])
        self.assertFalse(split["feeder"][0]["touches_rail"])
        self.assertEqual(len(split["other_road"]), 1)
        summary = summarize_snapshot({"ok": True, "lines": lines, "unresolved_vehicles": []})
        self.assertEqual(summary["road_vehicles"], 6)
        self.assertEqual(summary["feeder_vehicles"], 4)
        self.assertAlmostEqual(summary["feeder_share"], 4 / 6)
        self.assertEqual(summary["feeder_profit_last_year"], 1000)
        self.assertEqual(summary["other_road_profit_last_year"], 200)
        self.assertEqual(summary["air_profit_last_year"], 50000)

    def test_rail_join_is_separate_from_a_free_road_line(self):
        lines = [
            _line("rail", [5, 6], 1, 8000),
            _line("road", [6, 7], 3, 400),
        ]
        split = classify_road_lines(lines)
        self.assertEqual(len(split["feeder"]), 1)
        self.assertTrue(split["feeder"][0]["touches_rail"])
        self.assertFalse(split["feeder"][0]["touches_air"])

    def test_no_shared_station_means_no_feeder(self):
        lines = [_line("road", [1, 2], 5, 10), _line("air", [3, 4], 1, 10, airport_at={3, 4})]
        summary = summarize_snapshot({"ok": True, "lines": lines})
        self.assertEqual(summary["feeder_vehicles"], 0)
        self.assertEqual(summary["feeder_share"], 0)

    def test_failed_snapshot_is_ignored(self):
        self.assertIsNone(summarize_snapshot({"ok": False, "lines": []}))


class CatchmentTests(unittest.TestCase):
    def test_peak_below_one_aircraft_is_the_physical_cut(self):
        lines = [
            _line("air", [1, 2], 2, 0, capacity=80, airport_at={1, 2}, waiting=10, rating=100),
            _line("air", [3, 4], 1, 0, capacity=40, airport_at={3, 4}, waiting=40, rating=200),
        ]
        endpoints = airport_endpoints(lines)
        self.assertEqual(len(endpoints), 4)
        summary = catchment_summary(endpoints)
        self.assertEqual(summary["comparable"], 4)
        # Deux aéroports à 10 passagers pour 40 sièges, deux à 40 pour 40 sièges.
        self.assertEqual(summary["peak_waiting_below_one_plane"], 2)
        self.assertAlmostEqual(summary["share_below_one_plane"], 0.5)

    def test_missing_waiting_is_not_zero(self):
        lines = [_line("air", [1], 1, 0, capacity=30, airport_at={1})]
        summary = catchment_summary(airport_endpoints(lines))
        self.assertEqual(summary["comparable"], 0)
        self.assertIsNone(summary["share_below_one_plane"])
        self.assertEqual(summary["max_waiting_cargo"]["n"], 0)

    def test_several_lines_keep_the_smaller_aircraft(self):
        small = _line("air", [1], 1, 0, capacity=20, airport_at={1}, waiting=25, rating=80)
        large = _line("air", [1], 1, 0, capacity=100, airport_at={1}, waiting=25, rating=180)
        endpoints = airport_endpoints([large, small])
        self.assertEqual(len(endpoints), 1)
        self.assertEqual(endpoints[0]["one_plane_seats"], 20)
        self.assertEqual(endpoints[0]["rating"], 80)
        self.assertEqual(endpoints[0]["max_waiting_cargo"], 25)
        summary = catchment_summary(endpoints)
        self.assertEqual(summary["peak_waiting_below_one_plane"], 0)

    def test_rail_endpoint_does_not_require_an_airport(self):
        lines = [_line("rail", [5], 2, 0, capacity=200, waiting=40, rating=90)]
        endpoints = mode_passenger_endpoints(lines, "rail")
        self.assertEqual(len(endpoints), 1)
        self.assertEqual(endpoints[0]["one_plane_seats"], 100)
        summary = catchment_summary(endpoints)
        self.assertEqual(summary["peak_waiting_below_one_plane"], 1)


class TelemetryAggregateTests(unittest.TestCase):
    def test_last_december_only_and_mean_across_seeds(self):
        def snap(seed, date, road_profit):
            return {
                "ok": True,
                "duel_policy_id": "reference",
                "arm": "AAAHogEx",
                "seed": seed,
                "repeat": 0,
                "date": date,
                "lines": [
                    _line("air", [1, 2], 2, 1000, capacity=60, airport_at={1, 2}, waiting=5, rating=120),
                    _line("road", [1, 9], 4, road_profit),
                ],
                "unresolved_vehicles": [],
            }
        payload = {
            "line_telemetry": {
                "scope": "annual",
                "unavailable_fields": ["revenue"],
                "snapshots": [
                    snap(42, "1971-12-01", 10),
                    snap(42, "1972-12-01", 100),
                    snap(100, "1972-12-01", 300),
                ],
            }
        }
        report = summarize_line_telemetry(payload)
        self.assertEqual(len(report["groups"]), 1)
        group = report["groups"][0]
        self.assertEqual(group["games"], 2)
        self.assertEqual(group["date_max"], "1972-12-01")
        self.assertEqual(group["feeder_vehicles"]["mean"], 4)
        self.assertEqual(group["feeder_share"]["mean"], 1)
        self.assertEqual(group["feeder_profit_last_year"]["mean"], 200)
        self.assertAlmostEqual(group["catchment_mean_of_game_means"]["share_below_one_plane"]["mean"], 1)
        self.assertEqual(group["pooled_below_one_plane"], 4)
        self.assertEqual(group["pooled_comparable"], 4)
        self.assertAlmostEqual(group["pooled_share_below_one_plane"], 1)
        fed = group["catchment_mean_of_game_means"]["fed"]
        unfed = group["catchment_mean_of_game_means"]["unfed"]
        self.assertEqual(fed["pooled_comparable"], 2)
        self.assertEqual(unfed["pooled_comparable"], 2)
        self.assertAlmostEqual(fed["pooled_share_below_one_plane"], 1)


if __name__ == "__main__":
    unittest.main()
