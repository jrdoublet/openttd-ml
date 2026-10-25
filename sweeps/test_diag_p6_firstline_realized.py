"""Host-only first-line AIR calibration: distinguish decision quotes from realized years."""

import contextlib
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_p6_firstline_realized import analyze, main, _ranks, _pearson


CAMPAIGN = "fixture_air_defaults_40x5"


def build(stations=(0, 1), predicted=400, actual=900, target=1200):
    return (
        "[2026-10-25 10:00:00] dbg: [script:4] [0] [I] "
        "C121_BUILD line=0 arm=newpair new_airports=2 "
        f"station_id_a={stations[0]} station_id_b={stations[1]} "
        f"decision_profit={predicted} decision_capital=100 "
        f"actual_profit={actual} target_profit={target} decision_n=2\n"
    )


def snapshot(seed, day, profit=100, ids=(8, 10), stations=(0, 1),
             ok=True, error=None, repeat=0):
    line = {
        "mode": "air", "station_ids": list(stations),
        "vehicle_ids": list(ids),
        "vehicles": len(ids), "profit_this_year_gbp": profit,
        "profit_last_year_gbp": 999999,
    }
    return {
        "run": ["OpexAI", seed, repeat], "date": day,
        "campaign_id": CAMPAIGN, "duel_policy_id": "air_defaults",
        "policy_id": "air_defaults", "source_bundle_sha256": "a" * 64,
        "game_id": f"{CAMPAIGN}:policy=air_defaults:s{seed}:r{repeat}",
        "line_telemetry": {"ok": ok, "error": error, "lines": [line]},
    }


class FirstlineContracts(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.logs = self.root / "engine"
        self.logs.mkdir()
        self.snapshots = self.root / "snapshots.jsonl"

    def log(self, seed, content=None, name=None):
        if content is None:
            content = build()
        path = self.logs / (name or f"air_defaults_seed{seed}_r0.log")
        if path.name.endswith(".gz"):
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                handle.write(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def write_snapshots(self, rows):
        self.snapshots.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )

    def test_inverted_station_pair_and_january_this_year_profit_only(self):
        self.log(42, build(stations=(1, 0), predicted=400, actual=800, target=1300))
        self.write_snapshots([
            snapshot(42, "1970-02-01", profit=0),
            snapshot(42, "1971-01-01", profit=200),
            snapshot(42, "1972-01-01", profit=150, ids=(8, 10)),
            snapshot(42, "1973-01-01", profit=120, ids=(10, 20)),
        ])
        result = analyze(self.logs, self.snapshots, 1)
        year1970 = result["rows"][0]
        self.assertEqual(year1970["stations"], (0, 1))
        self.assertEqual(year1970["observed_profit_year"], 200)
        self.assertEqual(year1970["decision_profit"], 400)
        self.assertEqual(year1970["actual_profit_second_quote"], 800)
        self.assertEqual(year1970["target_profit_quote"], 1300)
        self.assertEqual(result["years"]["1970"]["ratio_sum_observed_to_decision_pct"], 50)
        self.assertEqual(result["years"]["1970"]["bias_decision_minus_observed"], 200)
        self.assertEqual(result["rows"][2]["fleet_changed_since_first_observation"], True)

    def test_other_company_and_wrong_station_are_never_used(self):
        self.log(42)
        aaa = snapshot(42, "1971-01-01", 90000)
        aaa["run"][0] = "AAAHogEx"
        wrong = snapshot(42, "1971-01-01", 12, stations=(8, 9))
        self.write_snapshots([aaa, wrong])
        result = analyze(self.logs, self.snapshots, 1)
        self.assertEqual(result["years"]["1970"]["observed_games"], 0)
        self.assertEqual(result["rows"][0]["observation_error"], "no_matching_air_line")
        self.assertIsNone(result["rows"][0]["observed_profit_year"])

    def test_missing_january_is_unknown_even_if_february_previous_profit_exists(self):
        self.log(42)
        self.write_snapshots([snapshot(42, "1971-02-01", profit=500)])
        report = analyze(self.logs, self.snapshots, 1)
        self.assertEqual(report["years"]["1970"]["missing_games"], 1)
        self.assertEqual(report["rows"][0]["observation_error"], "missing_january_checkpoint")
        self.assertIsNone(report["rows"][0]["observed_profit_year"])

    def test_invalid_telemetry_is_missing_not_zero(self):
        self.log(42)
        self.write_snapshots([snapshot(42, "1971-01-01", ok=False, error="save_probe")])
        report = analyze(self.logs, self.snapshots, 1)
        self.assertEqual(report["years"]["1970"]["observed_games"], 0)
        self.assertEqual(report["rows"][0]["observation_error"], "save_probe")

    def test_real_zero_profit_is_observed_zero(self):
        self.log(42)
        self.write_snapshots([snapshot(42, "1971-01-01", profit=0)])
        report = analyze(self.logs, self.snapshots, 1)
        self.assertEqual(report["years"]["1970"]["observed_games"], 1)
        self.assertEqual(report["rows"][0]["observed_profit_year"], 0)

    def test_duplicate_january_or_ambiguous_pair_fails_closed(self):
        self.log(42)
        row = snapshot(42, "1971-01-01")
        self.write_snapshots([row, row])
        with self.assertRaisesRegex(ValueError, "duplicate January"):
            analyze(self.logs, self.snapshots, 1)
        row["line_telemetry"]["lines"].append(
            dict(row["line_telemetry"]["lines"][0]))
        self.write_snapshots([row])
        with self.assertRaisesRegex(ValueError, "ambiguous matching AIR"):
            analyze(self.logs, self.snapshots, 1)

    def test_log_gzip_copy_identity_and_conflicting_content(self):
        self.log(42)
        self.log(42, name="air_defaults_seed42_r0.log.gz")
        self.write_snapshots([snapshot(42, "1971-01-01")])
        self.assertEqual(analyze(self.logs, self.snapshots, 1)["games"], 1)
        self.log(42, build(predicted=1000), name="air_defaults_seed42_r0.log.gz")
        with self.assertRaisesRegex(ValueError, "contradictory first-line logs"):
            analyze(self.logs, self.snapshots, 1)

    def test_seed_alias_or_duplicate_first_line_rejected(self):
        self.log(42)
        self.log(42, name="air_defaults_seed042_r0.log")
        self.write_snapshots([snapshot(42, "1971-01-01")])
        with self.assertRaisesRegex(ValueError, "ambiguous or contradictory"):
            analyze(self.logs, self.snapshots, 1)
        (self.logs / "air_defaults_seed042_r0.log").unlink()
        self.log(42, build() + build())
        with self.assertRaisesRegex(ValueError, "expected one first-line"):
            analyze(self.logs, self.snapshots, 1)

    def test_provenance_and_counts_are_strict(self):
        self.log(42)
        wrong = snapshot(42, "1971-01-01")
        wrong["source_bundle_sha256"] = "b" * 64
        self.write_snapshots([wrong, snapshot(42, "1972-01-01")])
        with self.assertRaisesRegex(ValueError, "campaign provenance changed"):
            analyze(self.logs, self.snapshots, 1)
        self.write_snapshots([wrong])
        with self.assertRaisesRegex(ValueError, "expected 2 independent games"):
            analyze(self.logs, self.snapshots, 2)

    def test_pearson_and_spearman_with_tied_predictions(self):
        self.assertEqual(_ranks([20, 10, 20, 40]), [2.5, 1, 2.5, 4])
        self.assertAlmostEqual(_pearson([1, 2, 3], [1, 2, 3]), 1)
        self.assertAlmostEqual(_pearson(_ranks([1, 2, 3]),
                                        _ranks([3, 2, 1])), -1)

    def test_cli_stdout_only_and_no_extra_files(self):
        self.log(42)
        self.write_snapshots([snapshot(42, "1971-01-01")])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main(["--logs", str(self.logs), "--snapshots", str(self.snapshots),
                  "--expected-games", "1"])
        self.assertEqual(json.loads(output.getvalue())["games"], 1)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),
                         ["engine", "snapshots.jsonl"])


if __name__ == "__main__":
    unittest.main()
