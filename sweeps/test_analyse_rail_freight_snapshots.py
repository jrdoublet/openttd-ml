import json
from pathlib import Path
import tempfile
import unittest

from analyse_rail_freight_snapshots import analyse, check_against_jsonl, rail_line_classification


class RailFreightSnapshotsTests(unittest.TestCase):
    def test_classification_keeps_mail_and_mixed_separate(self):
        cases = [
            ({"0": 30}, "passenger"),
            ({"2": 18}, "mail"),
            ({"1": 45}, "freight"),
            ({"0": 20, "1": 60}, "mixed"),
            ({"2": 10, "5": 40}, "mixed"),
            ({}, "unknown"),
        ]
        for capacities, expected in cases:
            self.assertEqual(rail_line_classification({"capacity_by_cargo": capacities}), expected)

    def test_only_latest_december_reference_and_rail(self):
        def snap(date, policy, arm, lines):
            return {"date": date, "duel_policy_id": policy, "arm": arm,
                    "seed": 42, "ok": True, "lines": lines, "unresolved_vehicles": []}
        def line(mode, cargo, trains, profit):
            return {"mode": mode, "capacity_by_cargo": cargo,
                    "vehicles": trains, "profit_this_year_gbp": profit}
        report = {"line_telemetry": {"snapshots": [
            snap("1972-12-01", "reference", "OpexAI", [line("rail", {"0": 60}, 1, 500)]),
            snap("1972-12-15", "reference", "OpexAI", [line("rail", {"1": 50}, 2, 1000),
                                                        line("road", {"1": 10}, 9, 4000)]),
            snap("1972-12-15", "variant", "OpexAI", [line("rail", {"0": 60}, 12, 10000)]),
            snap("1972-12-15", "reference", "AAAHogEx", []),
        ]}}
        result = analyse(report)
        opex = next(row for row in result["annual"] if row["arm"] == "OpexAI")
        self.assertEqual(opex["samples"], 1)
        self.assertEqual(opex["mean_trains"]["freight"], 2)
        self.assertEqual(opex["mean_trains"]["passenger"], 0)
        self.assertEqual(opex["mean_profit_ytd_gbp"]["freight"], 1000)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "snap.jsonl"
            rows = [
                {"duel_policy_id": "reference", "date": "1972-12-15", "run": ["OpexAI", 42, 0],
                 "vehs_chunk_valid": True, "primary_vehicles_by_mode": {"rail": 2}},
                {"duel_policy_id": "reference", "date": "1972-12-15", "run": ["AAAHogEx", 42, 0],
                 "vehs_chunk_valid": True, "primary_vehicles_by_mode": {"rail": 0}},
            ]
            source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            verified = check_against_jsonl(result, source)
            self.assertTrue(verified["physical_count_validation"]["all_equal"])
            rows[0]["primary_vehicles_by_mode"]["rail"] = 3
            source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            verified = check_against_jsonl(result, source)
            self.assertFalse(verified["physical_count_validation"]["all_equal"])


if __name__ == "__main__":
    unittest.main()
