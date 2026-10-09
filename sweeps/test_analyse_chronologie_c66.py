"""Contrats ciblés du décodeur de chronologie C66.3."""

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from analyse_chronologie_c66 import main


def _row(seed, arm, profit, year="1970"):
    return {
        "run": [arm, seed, 0], "date": f"{year}-12-01",
        "duel_policy_id": "baseline", "profit_year": profit,
        "profit_year_coverage": "partial" if year == "1970" else "complete",
        "company_value": 1000 + profit, "money": 40, "n_vehicles": 3,
        "n_stations": 2, "air_primary_vehicles": 2, "air_airports": 2,
        "performance_history": 100, "median_station_rating": 128,
        "air_passenger_capacity": 120,
        "airport_slots_opex": 2, "airport_slots_aaahogex": 2,
        "airport_towns_opex_present": 2, "airport_towns_aaahogex_present": 2,
        "primary_vehicles_by_mode": {"air": 2, "rail": 1, "road": 0, "water": 0},
        "stations_by_facility": {"airport": 2, "rail": 1, "bus": 1, "truck": 0, "dock": 0},
    }


class ChronologieC66Tests(unittest.TestCase):
    def _fixture(self, folder, rows=None, duplicate_snapshot=False):
        folder = Path(folder)
        path = folder / "chronologie.json"
        if rows is None:
            rows = [
                _row(42, "OpexAI", 100), _row(42, "AAAHogEx", 80),
                _row(100, "OpexAI", 70), _row(100, "AAAHogEx", 90),
                _row(42, "OpexAI", 200, "1971"), _row(42, "AAAHogEx", 100, "1971"),
                _row(100, "OpexAI", 140, "1971"), _row(100, "AAAHogEx", 190, "1971"),
            ]
        snaps = [{"duel_policy_id": "baseline", "arm": arm, "seed": seed, "repeat": 0,
                  "date": f"{year}-12-01", "ok": True, "lines": [
                      {"mode": "air", "vehicles": 2, "profit_this_year_gbp": 250.0}]}
                 for year in (1970, 1971) for seed in (42, 100)
                 for arm in ("OpexAI", "AAAHogEx")]
        if duplicate_snapshot:
            snaps.append(dict(snaps[0]))
        report = {"years": 2, "seeds": [42, 100], "policy_id": "baseline",
                  "campaign_id": "fixture", "games": [{}, {}], "failed_runs": [],
                  "line_telemetry": {"snapshots": snaps}}
        path.write_text(json.dumps(report), encoding="utf8")
        path.with_suffix(".jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf8")
        return path

    def _run(self, path):
        with patch.object(sys, "argv", ["analyse_chronologie_c66.py", str(path)]), \
                contextlib.redirect_stdout(io.StringIO()):
            main()
        return json.loads(path.with_suffix(".analysis.json").read_text(encoding="utf8"))

    def test_matched_years_are_independent_and_not_annualized(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self._run(self._fixture(folder))
            self.assertEqual(result["warnings"], [])
            self.assertEqual([row["year"] for row in result["annual"]], [1970, 1971])
            self.assertEqual(result["annual"][0]["arms"]["OpexAI"]["metrics"]["profit_year"], 85)
            self.assertEqual(result["annual"][0]["paired"]["profit_year"], {
                "n": 2, "mean_delta": 0, "median_delta": 0, "wins": 1, "losses": 1, "ties": 0})
            self.assertEqual(result["annual"][1]["paired"]["profit_year"]["mean_delta"], 25)
            self.assertEqual(result["annual"][0]["arms"]["OpexAI"]["profit_coverage"], {"partial": 2})
            self.assertEqual(result["annual"][0]["arms"]["AAAHogEx"]["lines"]["by_mode"]["air"]["mean_vehicle_profit_ytd"], 250)
            self.assertEqual(len(result["per_seed"]), 4)
            self.assertTrue(Path(folder, "chronologie.annual.csv").is_file())

    def test_duplicate_game_checkpoint_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self._fixture(folder)
            with path.with_suffix(".jsonl").open("a", encoding="utf8") as dest:
                dest.write(json.dumps(_row(42, "OpexAI", 100)) + "\n")
            with self.assertRaisesRegex(ValueError, "duplicate checkpoint"):
                self._run(path)

    def test_duplicate_line_snapshot_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "duplicate line snapshot"):
                self._run(self._fixture(folder, duplicate_snapshot=True))


if __name__ == "__main__":
    unittest.main()
