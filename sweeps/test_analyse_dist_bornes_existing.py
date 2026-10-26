"""Regression guards for snapshot identity and geometrical provenance."""

import json
import tempfile
import unittest
from pathlib import Path

from analyse_dist_bornes_existing import collect, distance_from_stations


class DistBornesExistingTest(unittest.TestCase):
    def test_station_coordinates_require_correct_map(self):
        line = {"ordered_station_tiles": [15, 16]}
        self.assertEqual(distance_from_stations(line, 16), 16)
        self.assertIsNone(distance_from_stations(line, 4))
        self.assertIsNone(distance_from_stations({"ordered_station_tiles": []}, 16))

    def test_only_latest_checkpoint_and_unknown_not_zero(self):
        def row(date, lines):
            return {"run": ["OpexAI", 42, 0], "date": date,
                    "duel_policy_id": "reference",
                    "line_telemetry": {"ok": True, "lines": lines}}

        earlier = {"mode": "rail", "ordered_station_tiles": [1, 5],
                   "profit_this_year_gbp": 300, "profit_last_year_gbp": 0}
        latest = {"mode": "rail", "ordered_station_tiles": [1, 2],
                  "profit_this_year_gbp": 0, "profit_last_year_gbp": None}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshots.jsonl"
            path.write_text("\n".join(json.dumps(p) for p in (
                row("1974-01-01", [earlier]), row("1974-12-01", [latest]))) + "\n",
                encoding="utf-8")
            summary = collect(path, 16, 1974)["OpexAI|reference|rail"]
            self.assertEqual(summary["lines"], 1)
            self.assertEqual(summary["median_manhattan_station"], 1)
            self.assertEqual(summary["profit_ytd_total_gbp"], 0)
            self.assertEqual(summary["profit_ytd_observed"], 1)
            self.assertEqual(summary["profit_prior_observed"], 0)


if __name__ == "__main__":
    unittest.main()
