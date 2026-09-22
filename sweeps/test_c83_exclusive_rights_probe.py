import unittest

from sweeps.diag_1v1_shared_monthly import (
    _iso_to_ottd_day,
    parse_c83_rights_events,
    summarize_c83_exclusive_rights,
)

class C83ExclusiveRightsProbeTests(unittest.TestCase):
    def test_parser_and_shared_town_summary(self):
        output = ("[script:0] [0] [I] OPEX 1972-1-16 C83_RIGHTS "
                  "year=1972 rank=0 town=7 pop=3100 available=1 cost=64000 probe_ok=1 error=0 "
                  "exclusive_company=-1 exclusive_duration=0 rating=5 bank=500000 available_capital=400000\n")
        parsed = parse_c83_rights_events(output)
        airport = {
            "count": 1,
            "stations": [{
                "id": 1,
                "facilities": ["airport"],
                "build_date": _iso_to_ottd_day("1972-01-10"),
            }],
        }
        rows = [
            {"seed": 42, "date": "1972-01-01", "arm": "OpexAI", "stations_by_town": {}, "c83_rights": parsed["1972-01"]},
            {"seed": 42, "date": "1972-01-01", "arm": "AAAHogEx", "stations_by_town": {}},
            {"seed": 42, "date": "1972-02-01", "arm": "OpexAI", "stations_by_town": {"7": airport}},
            {"seed": 42, "date": "1972-02-01", "arm": "AAAHogEx", "stations_by_town": {"7": airport}},
        ]
        summary = summarize_c83_exclusive_rights(rows)
        shared = summary["shared_airport_towns"]
        self.assertEqual(shared["observations"], 1)
        self.assertEqual(shared["available"], 1)
        self.assertEqual(shared["cost_median"], 64000)
        self.assertAlmostEqual(shared["cost_to_bank_median_pct"], 12.8)
        self.assertEqual(summary["observations"][0]["source_snapshot"], "1972-01-01")
        self.assertEqual(summary["observations"][0]["snapshot"], "1972-02-01")

if __name__ == "__main__":
    unittest.main()
