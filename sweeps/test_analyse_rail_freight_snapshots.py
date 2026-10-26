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
        self.assertEqual(opex["runs"], [{"seed": 42, "repeat": 0}])
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

    def test_repetitions_of_same_seed_remain_independent_snapshots(self):
        def snapshot(repeat, trains):
            return {
                "date": "1975-12-01", "duel_policy_id": "reference", "arm": "OpexAI",
                "seed": 42, "repeat": repeat, "ok": True,
                "lines": [{"mode": "rail", "capacity_by_cargo": {"1": 30},
                           "vehicles": trains, "profit_this_year_gbp": trains * 100}],
            }
        for snapshots in ([snapshot(0, 1), snapshot(1, 3)],
                          [snapshot(1, 3), snapshot(0, 1)]):
            with self.subTest(order=[r["repeat"] for r in snapshots]):
                result = analyse({"line_telemetry": {"snapshots": snapshots}})
                annual = result["annual"][0]
                self.assertEqual(annual["samples"], 2)
                self.assertEqual(annual["mean_trains"]["freight"], 2)
                self.assertEqual(annual["mean_profit_ytd_gbp"]["freight"], 200)
                self.assertEqual(annual["runs"], [{"seed": 42, "repeat": 0},
                                                  {"seed": 42, "repeat": 1}])
                self.assertEqual(len(result["per_seed"]), 2)

    def test_jsonl_crosscheck_does_not_hide_one_repetition_mismatch(self):
        snapshots = [
            {"date": "1975-12-01", "duel_policy_id": "reference", "arm": "OpexAI",
             "seed": 42, "repeat": rep, "ok": True,
             "lines": [{"mode": "rail", "capacity_by_cargo": {"1": 1},
                        "vehicles": count, "profit_this_year_gbp": 0}]}
            for rep, count in ((0, 1), (1, 3))
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "snap.jsonl"
            raw = [
                {"duel_policy_id": "reference", "date": "1975-12-01",
                 "run": ["OpexAI", 42, rep], "vehs_chunk_valid": True,
                 "primary_vehicles_by_mode": {"rail": count}}
                for rep, count in ((0, 1), (1, 4))
            ]
            path.write_text("".join(json.dumps(item) + "\n" for item in raw), encoding="utf-8")
            result = check_against_jsonl(analyse({"line_telemetry": {"snapshots": snapshots}}), path)
            validation = result["physical_count_validation"]
            self.assertEqual(validation["per_seed_snapshots"], 2)
            self.assertFalse(validation["all_equal"])
            self.assertEqual(len(validation["mismatches"]), 1)
            self.assertEqual(validation["mismatches"][0]["reason"], "train_count_diff")
            self.assertEqual(validation["mismatches"][0]["key"], (1975, 42, 1, "OpexAI"))
            self.assertEqual(result["annual"][0]["raw_rail_check"]["samples"], 2)

    def test_jsonl_without_repetition_identity_is_not_verified(self):
        snapshot = {"date": "1972-12-01", "duel_policy_id": "reference", "arm": "OpexAI",
                    "seed": 42, "repeat": 0, "ok": True, "lines": []}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "snap.jsonl"
            path.write_text(json.dumps({
                "duel_policy_id": "reference", "date": "1972-12-01",
                "run": ["OpexAI", 42], "vehs_chunk_valid": True,
                "primary_vehicles_by_mode": {"rail": 0},
            }) + "\n", encoding="utf-8")
            result = check_against_jsonl(
                analyse({"line_telemetry": {"snapshots": [snapshot]}}), path)
            self.assertFalse(result["physical_count_validation"]["all_equal"])
            self.assertEqual(result["physical_count_validation"]["mismatches"][0]["reason"],
                             "missing_raw_snapshot")


if __name__ == "__main__":
    unittest.main()
