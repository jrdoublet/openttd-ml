"""Unit guards for the non-forced route attribution in 10y rail pilot."""

import unittest

from analyse_rail_repair_idle_maturation_10y_20261031 import (
    ORIGINAL, event_date, event_int, match_service, manhattan,
)


def sample_line(*, tiles, cargo="1", profit=1200):
    return {
        "mode": "rail", "ordered_station_tiles": tiles,
        "station_ids": [61, 37], "vehicle_ids": [47],
        "vehicles": 1, "cargo_types": [cargo],
        "profit_this_year_gbp": profit,
        "profit_last_year_gbp": profit / 2,
        "vehicle_value": 10000,
    }


class MaturationMatchTest(unittest.TestCase):
    def setUp(self):
        self.od = ORIGINAL[100]
        self.correct = sample_line(tiles=[46702, 28883])

    def test_cargo_and_proximity_match_real_rail_100(self):
        result = match_service({"ok": True, "lines": [self.correct]}, self.od)
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["distance_tiles"], 3)
        self.assertEqual(result["profit_this_year_gbp"], 1200)

    def test_cargo_mismatch_rejected(self):
        other = sample_line(tiles=[46702, 28883], cargo="8")
        self.assertEqual(match_service({"ok": True, "lines": [other]}, self.od)["status"],
                         "not_observed")

    def test_ambiguous_nearby_route_refuses_attribution(self):
        close = sample_line(tiles=[46703, 28883])
        result = match_service({"ok": True, "lines": [self.correct, close]}, self.od)
        self.assertEqual(result["status"], "ambiguous")

    def test_distant_route_rejected(self):
        far = sample_line(tiles=[1, 2])
        self.assertEqual(match_service({"ok": True, "lines": [far]}, self.od)["status"],
                         "not_observed")

    def test_unreadable_telemetry_rejected(self):
        self.assertEqual(match_service({"ok": False}, self.od)["status"],
                         "missing_telemetry")

    def test_event_fields(self):
        event = ("OPEX 1974-8-18 RAIL_BUILD line=33 src=46958 dst=29140 "
                 "cargo=COAL pred_profit=36330 cost=80279 site_repair=1")
        self.assertEqual(event_date(event), (1974, 8, 18))
        self.assertEqual(event_int(event, "cost"), 80279)
        self.assertEqual(event_int(event, "src"), 46958)
        self.assertIsNone(event_int(event, "missing"))

    def test_manhattan_never_wraps_map_edge(self):
        self.assertEqual(manhattan(255, 256), 256)


if __name__ == "__main__":
    unittest.main()
