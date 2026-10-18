"""Tests unitaires pour sweeps/v253_decomposition_v252.py."""

import unittest
from sweeps.v253_decomposition_v252 import (
    parse_v252_replace_line,
    categorize_replacements,
    build_telemetry_indices,
    compute_group_financials,
    synthesize_decomposition,
    ENGINES_INFO,
)


class TestV253Decomposition(unittest.TestCase):
    def test_parse_v252_replace_line(self):
        sample = (
            "dbg: [script:4] [0] [I] OPEX 1973-5-3 V252_REPLACE line=5 old_engine=223 "
            "new_engine=218 old_veh=38 new_veh=290 price=153808 age=991 profit=64069 "
            "demand_old=417 demand_now=214"
        )
        parsed = parse_v252_replace_line(sample, seed=42)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["seed"], 42)
        self.assertEqual(parsed["year"], 1973)
        self.assertEqual(parsed["month"], 5)
        self.assertEqual(parsed["day"], 3)
        self.assertEqual(parsed["line_id"], 5)
        self.assertEqual(parsed["old_engine"], 223)
        self.assertEqual(parsed["new_engine"], 218)
        self.assertEqual(parsed["old_veh"], 38)
        self.assertEqual(parsed["new_veh"], 290)
        self.assertEqual(parsed["price"], 153808)
        self.assertEqual(parsed["age"], 991)
        self.assertEqual(parsed["profit_logged"], 64069.0)

    def test_parse_invalid_line(self):
        self.assertIsNone(parse_v252_replace_line("random log line"))

    def test_categorize_replacements(self):
        replaces = [
            {"old_engine": 223, "new_engine": 217},
            {"old_engine": 228, "new_engine": 217},
            {"old_engine": 220, "new_engine": 217},
            {"old_engine": 223, "new_engine": 218},
            {"old_engine": 223, "new_engine": 228},
            {"old_engine": 223, "new_engine": 227},
        ]
        cats = categorize_replacements(replaces)
        self.assertEqual(len(cats["to_217_from_223"]), 1)
        self.assertEqual(len(cats["to_217_from_228"]), 1)
        self.assertEqual(len(cats["to_217_from_other"]), 1)
        self.assertEqual(len(cats["to_218"]), 1)
        self.assertEqual(len(cats["to_228"]), 1)
        self.assertEqual(len(cats["other"]), 1)

    def test_financials_aggregation_synthetic(self):
        snapshots = [
            {
                "seed": 42,
                "duel_policy_id": "v252m2",
                "year": 1972,
                "lines": [
                    {
                        "market_key": "air|1,2",
                        "vehicle_ids": [10],
                        "vehicle_financials": [{"vehicle_id": 10, "profit_last_year_gbp": 20000.0}],
                        "profit_this_year_gbp": 25000.0,
                        "endpoint_cargo_stats": [{"cargo": {"0": {"rated": True, "rating": 150, "max_waiting_cargo": 10}}}],
                    }
                ],
            },
            {
                "seed": 42,
                "duel_policy_id": "v252m2",
                "year": 1974,
                "lines": [
                    {
                        "market_key": "air|1,2",
                        "vehicle_ids": [20],
                        "vehicle_financials": [{"vehicle_id": 20, "profit_last_year_gbp": 15000.0}],
                        "profit_this_year_gbp": 30000.0,
                        "endpoint_cargo_stats": [{"cargo": {"0": {"rated": True, "rating": 160, "max_waiting_cargo": 8}}}],
                    }
                ],
            },
            {
                "seed": 42,
                "duel_policy_id": "reference",
                "year": 1972,
                "lines": [
                    {
                        "market_key": "air|1,2",
                        "profit_this_year_gbp": 24000.0,
                    }
                ],
            },
            {
                "seed": 42,
                "duel_policy_id": "reference",
                "year": 1974,
                "lines": [
                    {
                        "market_key": "air|1,2",
                        "profit_this_year_gbp": 26000.0,
                    }
                ],
            },
        ]
        veh_idx, mkt_idx = build_telemetry_indices(snapshots)
        reps = [{"seed": 42, "year": 1973, "old_veh": 10, "new_veh": 20, "old_engine": 223, "new_engine": 218}]
        res = compute_group_financials(reps, veh_idx, mkt_idx)

        self.assertEqual(res["n_events"], 1)
        self.assertEqual(res["n_matched_lines"], 1)
        self.assertEqual(res["line_profit_before"], 25000.0)
        self.assertEqual(res["line_profit_after"], 30000.0)
        self.assertEqual(res["delta_line_profit"], 5000.0)
        self.assertEqual(res["ref_line_profit_before"], 24000.0)
        self.assertEqual(res["ref_line_profit_after"], 26000.0)
        self.assertEqual(res["delta_ref_line_profit"], 2000.0)
        self.assertEqual(res["surperformance_vs_ref"], 3000.0)
        self.assertEqual(res["delta_rating"], 10.0)
        self.assertEqual(res["delta_waiting"], -2.0)

    def test_engine_info_completeness(self):
        for eid in (217, 218, 223, 228):
            self.assertIn(eid, ENGINES_INFO)
            info = ENGINES_INFO[eid]
            self.assertGreater(info["running"], 0)
            self.assertGreater(info["max_age_years"], 10)


if __name__ == "__main__":
    unittest.main()
