"""Regression des ratios annuels apparies et de la censure des donnees ROAD."""
import json
from pathlib import Path
import tempfile
import unittest

import analyse_road100 as road100


class AnalyseRoad100Tests(unittest.TestCase):
    def test_december_only_latest_date_and_invalid_records(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "checkpoints.jsonl"
            rows = [
                {"run": ["OpexAI", 42, 0], "date": "1970-11-01", "profit_year": 50},
                {"run": ["OpexAI", 42, 0], "date": "1970-12-01", "profit_year": 75},
                {"run": ["OpexAI", 42, 0], "date": "1970-12-19", "profit_year": 99},
                {"run": ["AAAHogEx", 42, 0], "date": "1970-12-01", "profit_year": 100},
                {"run": ["OpexAI", 42, 1], "date": "1970-12-01", "profit_year": 800},
                {"run": ["OpexAI", 42, 0], "date": "1971-12-01", "profit_year": 500},
            ]
            path.write_text("bad-json\n" + "\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            annual, counts = road100.read_annual_checkpoints(path, 1970, 1)
            self.assertEqual(annual[("OpexAI", 42, 1970)]["profit_year"], 99)
            self.assertNotIn(("OpexAI", 42, 1971), annual)
            self.assertEqual(counts[("OpexAI", 42, 1970)], 3)

    def test_ratio_of_means_and_missing_seed_fail_closed(self):
        result = {"seeds": [1, 2], "start_year": 1970, "years": 2,
                  "campaign_id": "small", "games": [], "summary": [],
                  "failed_runs": [], "map_size": 8}
        checkpoints = {
            ("OpexAI", 1, 1970): {"profit_year": 100},
            ("AAAHogEx", 1, 1970): {"profit_year": 50},
            ("OpexAI", 2, 1970): {"profit_year": 200},
            ("AAAHogEx", 2, 1970): {"profit_year": 250},
            ("OpexAI", 1, 1971): {"profit_year": 500},
        }
        out = road100.analyse(result, checkpoints, {})
        first, second = out["years"]
        self.assertEqual(first["pairs"], 2)
        self.assertEqual(first["profit_ratio_of_means"], 1.0)
        self.assertEqual(first["wins"], 1)
        self.assertTrue(first["target_100_pct_reached"])
        self.assertEqual(second["pairs"], 0)
        self.assertIsNone(second["target_100_pct_reached"])

    def test_zero_adversary_profit_is_not_parity(self):
        result = {"seeds": [1], "start_year": 1970, "years": 1,
                  "campaign_id": "small", "games": [], "summary": [],
                  "failed_runs": [], "map_size": 8}
        checkpoints = {("OpexAI", 1, 1970): {"profit_year": 5},
                       ("AAAHogEx", 1, 1970): {"profit_year": 0}}
        out = road100.analyse(result, checkpoints, {})
        self.assertIsNone(out["years"][0]["profit_ratio_of_means"])
        self.assertIsNone(out["years"][0]["target_100_pct_reached"])

    def test_filter_policies_prevents_mixing_reference_and_variant(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "checkpoints.jsonl"
            records = []
            for pol, profit in (("reference", 12), ("variant", 30)):
                for arm, p in (("OpexAI", profit), ("AAAHogEx", 20)):
                    records.append({"run": [arm, 1, 0], "duel_policy_id": pol,
                                    "date": "1970-12-01", "profit_year": p})
            path.write_text("\n".join(json.dumps(rec) for rec in records), encoding="utf-8")
            result = {"seeds": [1], "start_year": 1970, "years": 1,
                      "campaign_id": "two", "games": [], "summary": [],
                      "failed_runs": [], "map_size": 8}
            for pol, wanted in (("reference", 0.6), ("variant", 1.5)):
                rec, obs = road100.read_annual_checkpoints(path, 1970, 1, pol)
                data = road100.analyse(result, rec, obs, pol)
                self.assertAlmostEqual(data["years"][0]["profit_ratio_of_means"], wanted)


if __name__ == "__main__":
    unittest.main()
