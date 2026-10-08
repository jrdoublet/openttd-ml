import copy
import unittest
from unittest import mock

from station_supply import extract_station_supply, supply_intervals, extract_town_month


def chunks():
    return {"DATE": {"0": {"economy_date": 1000}},
            "STNN": {"0": {"normal": [{"base": [{"owner": 0, "facilities": 8,
                                                   "xy": 42, "build_date": 900}]}]},
                     "1": {"normal": [{"base": [{"owner": 1, "facilities": 8,
                                                   "xy": 84, "build_date": 900}]}]}},
            "LGRP": {"7": {"cargo": 5, "last_compression": 950,
                           "nodes": [{"station": 0, "xy": 42, "supply": 100, "last_update": 999},
                                     {"station": 1, "xy": 84, "supply": 200, "last_update": 999}]}}}


class StationSupplyTests(unittest.TestCase):
    def test_town_month_api_equivalent_no_partial_or_hidden_history(self):
        c = {"CITY": {"9": {"valid_history": 2, "supplied": [{"cargo": 5, "history": [
            {"production": 9999, "transported": 9999},
            {"production": 200, "transported": 80},
            {"production": 7777, "transported": 7777}]}]}}}
        out = extract_town_month(c)
        self.assertTrue(out["ok"])
        self.assertEqual(out["towns"], [{"town": 9, "cargo": 5, "production": 200, "supplied_all_companies": 80}])
        c["CITY"]["9"]["valid_history"] = 0
        self.assertEqual(extract_town_month(c)["towns"], [])
        c["CITY"]["9"]["valid_history"] = 2
        c["CITY"]["9"]["supplied"][0]["history"][1]["transported"] = 201
        self.assertFalse(extract_town_month(c)["ok"])
    def pair(self):
        a = chunks()
        b = copy.deepcopy(a)
        b["DATE"]["0"]["economy_date"] = 1030
        b["LGRP"]["7"]["nodes"][0].update(supply=160, last_update=1029)
        return extract_station_supply(a, 0), extract_station_supply(b, 0)

    def test_exact_new_cargo_direct_station_id_nonzero_cargo(self):
        a, b = self.pair()
        self.assertTrue(a["ok"])
        self.assertEqual([(n["station"], n["cargo"]) for n in a["nodes"]], [(0, 5)])
        row = supply_intervals(a, b)[0]
        self.assertTrue(row["exact"])
        self.assertEqual(row["arrivals"], 60)
        self.assertAlmostEqual(row["monthly_captured"], 60.8)

    def test_compression_merge_rebuild_reset_missing_unknown(self):
        for field, value in (("compression", 960), ("graph", "8"), ("membership", []),
                             ("build_date", 1001), ("xy", 66), ("supply", 90), ("last_update", 998)):
            with self.subTest(field=field):
                a, b = self.pair()
                b["nodes"][0][field] = value
                self.assertIsNone(supply_intervals(a, b)[0]["arrivals"])
        a, b = self.pair()
        b["nodes"] = []
        self.assertIsNone(supply_intervals(a, b)[0]["arrivals"])

    def test_zero_observed_distinct_from_unknown(self):
        a, b = self.pair()
        b["nodes"][0].update(supply=100, last_update=999)
        self.assertEqual(supply_intervals(a, b)[0]["arrivals"], 0)
        a["ok"] = False
        self.assertIsNone(supply_intervals(a, b)[0]["arrivals"])

    def test_missing_malformed_duplicate_counters(self):
        for field in ("DATE", "LGRP", "STNN"):
            c = chunks()
            del c[field]
            self.assertFalse(extract_station_supply(c, 0)["ok"])
        c = chunks()
        c["LGRP"]["7"]["nodes"][0]["supply"] = -1
        self.assertFalse(extract_station_supply(c, 0)["ok"])
        c = chunks()
        c["LGRP"]["8"] = copy.deepcopy(c["LGRP"]["7"])
        self.assertFalse(extract_station_supply(c, 0)["ok"])

    def test_non_monthly_and_invalid_time_unknown(self):
        for days in (0, -1, 33):
            a, b = self.pair()
            b["economy_date"] = a["economy_date"] + days
            self.assertIsNone(supply_intervals(a, b)[0]["arrivals"])

    def test_harness_keep_optional_tuple_and_both_owners(self):
        import bench_1v1_5y_20seeds as harness
        row = {"chunks": chunks(), "date": "1970-01-01", "experiment": {"seed": 42}}
        with mock.patch.object(harness, "STATION_SUPPLY_TELEMETRY", False):
            off = harness.keep(row)
        with mock.patch.object(harness, "STATION_SUPPLY_TELEMETRY", True):
            on = harness.keep(row)
        self.assertIsInstance(on, tuple)
        self.assertEqual(len(on), 2)
        self.assertNotIn("station_supply", off[0])
        self.assertEqual([r["station_supply"]["nodes"][0]["station"] for r in on], [0, 1])
        self.assertEqual(off[0].get("profit_year"), on[0].get("profit_year"))


if __name__ == "__main__":
    unittest.main()
