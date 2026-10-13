"""Tests for separated profiled P2/P5 and paired C66 conversion funnel."""
import unittest

from analyse_p0_conversion_funnel_20261012 import (
    first_negative_gap, join, physical, valid_rows,
)


def point(arm, date, seed=42, profit=2):
    return {"run": [arm, seed, 0], "date": date,
            "vehs_chunk_valid": True, "stnn_chunk_valid": True,
            "primary_vehicles_by_mode": {"air": 2, "rail": 1},
            "stations_by_facility": {"airport": 2, "rail": 1},
            "profit_year": profit, "company_value": profit,
            "profit_year_coverage": "complete", "profit_year_quarters_valid": 4,
            "primary_vehicles": 3, "n_stations": 3}


class ConversionFunnelTests(unittest.TestCase):
    def test_duplicate_month_rejected(self):
        rows = [point("OpexAI", "1970-12-01")]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            valid_rows(rows + rows, (42,))

    def test_missing_year_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            valid_rows([point("OpexAI", "1970-12-01")], (42,))

    def test_first_negative_gap_not_claimed_decision(self):
        d = {(42, "OpexAI"): {"1971-01-01": point("OpexAI", "1971-01-01", profit=3),
                                  "1971-02-01": point("OpexAI", "1971-02-01", profit=2)},
             (42, "AAAHogEx"): {"1971-01-01": point("AAAHogEx", "1971-01-01", profit=2),
                                    "1971-02-01": point("AAAHogEx", "1971-02-01", profit=3)}}
        self.assertEqual("1971-02-01", first_negative_gap(d, 42, "profit_year"))

    def test_invalid_stocks_are_not_zero(self):
        p = point("OpexAI", "1971-12-01")
        p["stnn_chunk_valid"] = False
        with self.assertRaisesRegex(ValueError, "invalid physical"):
            physical(p)

    def test_partial_profit_skipped_until_both_arms_full_year(self):
        p = point("OpexAI", "1971-01-01", profit=1)
        p["profit_year_coverage"] = "partial"
        q = point("OpexAI", "1971-02-01", profit=1)
        a = point("AAAHogEx", "1971-01-01", profit=3)
        b = point("AAAHogEx", "1971-02-01", profit=3)
        d = {(42, "OpexAI"): {"1971-01-01": p, "1971-02-01": q},
             (42, "AAAHogEx"): {"1971-01-01": a, "1971-02-01": b}}
        self.assertEqual("1971-02-01", first_negative_gap(d, 42, "profit_year"))

    def test_profiled_vs_unprofiled_separated(self):
        dates = [f"{year}-12-01" for year in (1970, 1971, 1972, 1973)]
        checkpoints = valid_rows([point(arm, date) for arm in ("OpexAI", "AAAHogEx") for date in dates], (42,))
        p2 = {"by_seed": {"42": {str(y): {"passes": 2, "start_empty": 1, "months": {}} for y in range(1970, 1974)}}}
        p5 = {"by_seed": {"42": {str(y): {"lines_by_mode": {"air": 1},
                                      "search_paid_calls": 0, "search_window_ops": 0,
                                      "search_days": 0, "lines_by_month": {}} for y in range(1970, 1974)}}}
        output = join(checkpoints, p2, p5, (42,))
        r = output["by_seed"]["42"]["by_year"]["1973"]
        self.assertEqual({"air": 1}, r["profiled_net_new_line_events"])
        self.assertEqual(0, r["unprofiled_paired_economy"]["opex_minus_aaa"]["profit_year"])
        self.assertTrue(any("MUST NOT" in s for s in output["limitations"]))


if __name__ == "__main__":
    unittest.main()
