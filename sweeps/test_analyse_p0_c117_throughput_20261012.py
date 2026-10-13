"""Fixtures C117 : pas de preuve de causalite ou profit comptable."""

import unittest

from analyse_p0_c117_throughput_20261012 import parse, summarize, year_line


SAMPLE = ("OPEX 1972-7-14 C117_AIR_THROUGHPUT line=3 build_date=719800 age_bucket=7 "
          "period_days=30 samples=15 live_avg=1.0 live_last=1 "
          "pax=200 seat_legs=400 trips=4 profit=3000 load_factor=0.5 "
          "rating_a=100 rating_b=120 wait_a=4 wait_b=6 "
          "invalid_order_samples=0 unobserved_transitions=0")


class C117Tests(unittest.TestCase):
    def test_parse_and_quality(self):
        parsed = parse(SAMPLE)
        self.assertEqual((parsed["year"], parsed["line"], parsed["period_days"]), (1972, 3, 30))
        self.assertIsNone(parse("une autre ligne"))
        with self.assertRaises(ValueError):
            parse(SAMPLE.replace("period_days=30", "period_days=0"))

    def test_weighted_year(self):
        first = parse(SAMPLE)
        second = dict(first, month=8, age_bucket=8, period_days=60, pax=100, seat_legs=400,
                      trips=2, profit=6000, live_avg=2.0, live_last=2,
                      invalid_order_samples=2)
        summary = year_line([second, first])
        self.assertEqual(summary["period_days_total"], 90)
        self.assertAlmostEqual(summary["load_factor_observed"], 300/800)
        self.assertEqual(summary["last_fleet"], 2)
        self.assertEqual(summary["invalid_order_samples"], 2)
        self.assertAlmostEqual(summary["vehicle_profit_per_aircraft_year_exposure"],
                               9000 * 365.25 / 150)

    def test_fleet_change_not_profit_sign(self):
        old = parse(SAMPLE)
        new = dict(old, year=1973, live_last=2, live_avg=2.0, profit=-1000)
        groups = summarize([old, new], 42)["fleet_groups"]
        self.assertEqual(groups["increase"]["count"], 1)
        self.assertEqual(groups["constant"]["count"], 0)
        self.assertLess(groups["increase"]["lines"][0]["delta_profit_per_aircraft_year"], 0)

    def test_zero_seats_not_false_zero_load(self):
        row = parse(SAMPLE)
        row["seat_legs"] = 0
        self.assertIsNone(year_line([row])["load_factor_observed"])

    def test_reject_duplicate_bucket(self):
        row = parse(SAMPLE)
        with self.assertRaises(ValueError):
            summarize([row, dict(row)], 42)

    def test_reject_recycled_line_id(self):
        row = parse(SAMPLE)
        with self.assertRaises(ValueError):
            summarize([row, dict(row, age_bucket=8, build_date=720300)], 42)


if __name__ == "__main__":
    unittest.main()
