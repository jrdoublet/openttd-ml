"""Host-only V303 reverse-probe coverage contracts on synthetic engine logs."""

import contextlib
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_v303_reverse_probe import analyze, main


def entry(ok, iters, distance, year=1972):
    return (f"[2026-10-21 17:24:15] dbg: [script:4] "
            f"[0] [I] OPEX {year}-1-26 V294F_PROBE "
            f"ok={ok} iters={iters} manh={distance}\n")


class V303ReadOnlyContracts(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def write(self, name, content):
        path = self.root / name
        if path.suffix == ".gz":
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                stream.write(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def test_exact_counters_years_and_distance_boundaries(self):
        self.write("reference_seed42_r0.log", (
            entry(1, 76, 79) + entry(1, 99, 80) +
            entry(0, 300, 159) + entry(0, 300, 160) +
            entry(0, 0, 249) + entry(1, 250, 250, 1973)
        ))
        result = analyze(self.root, expected_games=1)
        self.assertEqual(result["overall"]["attempts"], 6)
        self.assertEqual(result["overall"]["found"], 3)
        self.assertEqual(result["overall"]["at_iteration_cap"], 2)
        self.assertEqual(result["overall"]["iterations_sum"], 1025)
        self.assertEqual(result["overall"]["found_pct"], 50)
        self.assertEqual([result["by_manhattan_band"][b]["attempts"] for b in
                          ("0-79", "80-159", "160-249", "250+")], [1, 2, 2, 1])
        self.assertEqual(result["by_year"]["1972"]["attempts"], 5)
        self.assertEqual(result["by_year"]["1973"]["attempts"], 1)
        self.assertIsNone(result["by_manhattan_band"]["0-79"]
                          ["not_found_iterations_median"])

    def test_zero_observation_is_missing_rate_not_zero_success(self):
        self.write("reference_seed42_r0.log", "[0] [I] OPEX 1972-1-1 TASK name=report\n")
        result = analyze(self.root, expected_games=1)
        self.assertEqual(result["games_without_events"], 1)
        self.assertEqual(result["overall"]["attempts"], 0)
        self.assertIsNone(result["overall"]["found_pct"])
        self.assertIsNone(result["overall"]["iterations_median"])

    def test_arm_seed_and_repeat_remain_independent(self):
        self.write("reference_seed42_r0.log", entry(1, 55, 22))
        self.write("reference_seed42_r1.log", entry(0, 300, 99))
        self.write("variant_seed42_r0.log", entry(0, 300, 99))
        result = analyze(self.root, expected_games=2)
        self.assertEqual(result["games"], 2)
        self.assertEqual(result["overall"]["attempts"], 2)
        self.assertEqual(result["overall"]["found"], 1)
        self.assertEqual([x["repeat"] for x in result["per_game"]], [0, 1])

    def test_same_log_and_gzip_collapsed_once(self):
        data = entry(1, 99, 80) + "unrelated extra\n"
        self.write("reference_seed42_r0.log", data)
        self.write("reference_seed42_r0.log.gz", data)
        result = analyze(self.root, expected_games=1)
        self.assertEqual(result["log_gzip_copies_collapsed"], 1)
        self.assertEqual(result["overall"]["attempts"], 1)

    def test_contradictory_gzip_even_same_probe_lines_rejected(self):
        self.write("reference_seed42_r0.log", entry(1, 99, 80) + "other=A\n")
        self.write("reference_seed42_r0.log.gz", entry(1, 99, 80) + "other=B\n")
        with self.assertRaisesRegex(ValueError, "contradictory or ambiguous"):
            analyze(self.root, expected_games=1)

    def test_alias_seed_spelling_rejected_instead_of_double_count(self):
        self.write("reference_seed01_r0.log", entry(1, 99, 80))
        self.write("reference_seed1_r0.log", entry(1, 99, 80))
        with self.assertRaisesRegex(ValueError, "contradictory or ambiguous"):
            analyze(self.root, expected_games=1)

    def test_malformed_duplicate_missing_and_invalid_ranges_fail_closed(self):
        samples = [
            (entry(1, 99, 80).replace("ok=1", "ok=1 ok=0"), "duplicate"),
            (entry(1, 99, 80).replace(" manh=80", ""), "missing"),
            (entry(1, 99, 80).replace("iters=99", "iters=301"), "out of range"),
            (entry(1, 99, 80).replace("iters=99", "iters=0"), "without iterations"),
            (entry(1, 99, 80).replace("iters=99", "iters=n/a"), "invalid"),
            (entry(1, 99, 80) + "[0] [I] OPEX 1971-1-1 "
             "V294F_PROBE ok=0 iters=300 extra junk manh=99\n", "malformed"),
        ]
        for content, expected in samples:
            with self.subTest(error=expected):
                self.write("reference_seed42_r0.log", content)
                with self.assertRaisesRegex(ValueError, expected):
                    analyze(self.root, expected_games=1)

    def test_truncated_gzip_reports_cli_error(self):
        path = self.write("reference_seed42_r0.log.gz", entry(1, 99, 80))
        path.write_bytes(path.read_bytes()[:-8])
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main([str(self.root), "--expected-games", "1"])
        self.assertEqual(caught.exception.code, 2)

    def test_cli_outputs_json_and_does_not_write_file(self):
        self.write("reference_seed42_r0.log", entry(1, 99, 80))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main([str(self.root), "--expected-games", "1"])
        self.assertEqual(json.loads(output.getvalue())["overall"]["found"], 1)
        self.assertEqual([file.name for file in self.root.iterdir()],
                         ["reference_seed42_r0.log"])

    def test_expected_game_count_rejects_partial_dataset(self):
        self.write("reference_seed42_r0.log", entry(1, 99, 80))
        with self.assertRaisesRegex(ValueError, "expected 2 games"):
            analyze(self.root, expected_games=2)


if __name__ == "__main__":
    unittest.main()
