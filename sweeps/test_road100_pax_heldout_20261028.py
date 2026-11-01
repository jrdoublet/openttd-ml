"""Synthetic-only contracts for V24 ON PAX train/heldout diagnostic."""

import contextlib
import gzip
import io
import json
import math
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_road100_pax_heldout_20261028 import (
    HELDOUT_SEEDS, POLICY, TRAIN_SEEDS, analyze, main, parse_log,
    render_markdown,
)


def event(line=0, age=2, year=1972, pred_rev=100, real_rev=400,
          pred_prof=10, real_prof=30, vehs=2, kind="pax", mode="road"):
    """Synthetic data shaped like the frozen engine's LINE_REVENUE events."""
    return (
        "[2026-10-28 05:20:00] dbg: [script:4] [0] [I] "
        f"OPEX 1972-1-25 LINE_REVENUE line={line} mode={mode} "
        f"kind={kind} cargo=PASS year={year} age={age} "
        f"pred_rev={pred_rev} real_rev={real_rev} "
        f"pred_prof={pred_prof} real_prof={real_prof} "
        f"pred_run=600 real_run=1200 vehs={vehs} "
        "n_stops_a=1 n_stops_b=1 cap=35\n"
    )


class PAXHeldoutContracts(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.logs = self.root / "engine"
        self.logs.mkdir()

    def log(self, seed, content=None, arm=POLICY, repeat=0, gz=False):
        path = self.logs / f"{arm}_seed{seed}_r{repeat}.log"
        if gz:
            path = path.with_suffix(".log.gz")
        content = content if content is not None else event()
        if gz:
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                stream.write(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def five_seeds(self, replacements=None):
        replacements = replacements or {}
        result = {}
        for seed in TRAIN_SEEDS + HELDOUT_SEEDS:
            result[seed] = self.log(seed, replacements.get(seed, event()))
        return result

    def test_median_train_ratio_and_heldout_log_error_without_refitting(self):
        self.five_seeds({
            7: event(real_rev=200, real_prof=30),
            42: event(real_rev=400, real_prof=30),
            100: event(real_rev=800, real_prof=90),
            999: event(real_rev=800, real_prof=90),
            2026: event(real_rev=200, real_prof=30),
        })
        report = analyze([self.logs])
        factors = report["factors_train_median_real_over_pred"]
        self.assertEqual(factors, {"revenue": 4.0, "profit": 3.0})
        rev = report["heldout"]["revenue"]
        self.assertEqual(rev["n_positive_real_pred"], 2)
        self.assertAlmostEqual(rev["maLE_raw"], math.log(4), places=5)
        self.assertAlmostEqual(rev["maLE_calibrated"], math.log(2), places=5)
        self.assertEqual(rev["n_heldout_seeds_with_valid_pairs"], 2)
        profit = report["heldout"]["profit"]
        self.assertAlmostEqual(profit["maLE_calibrated"], math.log(3) / 2, places=5)
        self.assertEqual(report["training_seeds"], [7, 42, 100])
        self.assertEqual(report["heldout_seeds"], [999, 2026])
        self.assertIn("Biais de selection", report["warning"])

    def test_age_filter_unique_line_age_and_latest_vehicle_proxy(self):
        self.five_seeds({
            7: (event(line=1, age=1, year=1971, real_rev=999999)
                + event(line=1, age=2, real_rev=200, vehs=2)
                + event(line=1, age=3, year=1973, real_rev=400, vehs=4)
                + event(line=2, age=2, real_rev=200, vehs=1)
                + event(line=3, age=0, year=1970)),
            42: event(line=1, real_rev=200),
            100: event(line=1, real_rev=200),
        })
        report = analyze([self.logs])
        seed7 = report["by_seed"]["7"]
        self.assertEqual(seed7["pax_events"], 5)
        self.assertEqual(seed7["immature_age_lt_2"], 2)
        self.assertEqual(seed7["mature_events"], 3)
        self.assertEqual(seed7["distinct_mature_lines"], 2)
        self.assertEqual(seed7["vehicle_sum_latest_mature_age_per_line_proxy"], 5)
        self.assertEqual(report["train_coverage"]["distinct_mature_lines"], 4)
        # 7 contributes ratios 2, 4, 2; 42 and 100 contribute ratio 2.
        self.assertEqual(report["factors_train_median_real_over_pred"]["revenue"], 2)

    def test_only_road_pax_is_used_and_other_arm_in_directory_ignored(self):
        self.five_seeds({
            7: (event(real_rev=200)
                + event(line=6, mode="air", real_rev=100000)
                + event(line=7, kind="freight", real_rev=100000)),
        })
        self.log(7, event(real_rev=900000), arm="reference")
        report = analyze([self.logs])
        self.assertEqual(report["by_seed"]["7"]["pax_events"], 1)
        self.assertEqual(report["train_ratio_support"]["revenue"]["n_positive_real_pred"], 3)

    def test_duplicate_identity_rejected_even_if_duplicate_is_immature(self):
        self.five_seeds({7: event(age=1) + event(age=1)})
        with self.assertRaisesRegex(ValueError, r"duplicate \(seed,line,age\)"):
            analyze([self.logs])

    def test_different_age_same_line_and_same_line_across_seeds_are_valid(self):
        self.five_seeds({7: event(age=2) + event(age=3, year=1973)})
        self.assertEqual(analyze([self.logs])["train_coverage"]["mature_line_age_rows"], 4)

    def test_missing_log_repeat_or_other_policy_is_not_train_data(self):
        paths = self.five_seeds()
        paths[999].unlink()
        with self.assertRaisesRegex(ValueError, "missing V24 ON logs"):
            analyze([self.logs])
        self.log(999, repeat=1)
        with self.assertRaisesRegex(ValueError, "unexpected seed/repetition"):
            analyze([self.logs])
        self.log(999)
        self.log(999, arm="reference")
        with self.assertRaisesRegex(ValueError, "not a V24 ON policy"):
            analyze([self.logs / "reference_seed999_r0.log"])

    def test_same_seed_multiple_files_rejected(self):
        paths = self.five_seeds()
        self.log(7, gz=True)
        with self.assertRaisesRegex(ValueError, "duplicate ON policy log"):
            analyze([self.logs])
        paths[7].unlink()
        self.assertEqual(analyze([self.logs])["by_seed"]["7"]["pax_events"], 1)

    def test_nonpositive_profit_is_censored_not_silently_pseudocounted(self):
        self.five_seeds({
            999: event(pred_prof=0, real_prof=30),
            2026: event(pred_prof=10, real_prof=-12),
        })
        report = analyze([self.logs])
        score = report["heldout"]["profit"]
        self.assertIsNone(score["maLE_raw"])
        self.assertIsNone(score["maLE_calibrated"])
        self.assertEqual(score["n_positive_real_pred"], 0)
        self.assertEqual(score["n_excluded_nonpositive_or_unusable"], 2)
        self.assertEqual(report["heldout"]["revenue"]["n_positive_real_pred"], 2)

    def test_invalid_age_number_and_vehicle_count_rejected(self):
        cases = (
            (event(age=-1), "age below"),
            (event(pred_rev="nan"), "non-finite pred_rev"),
            (event(real_prof="inf"), "non-finite real_prof"),
            (event(vehs=-1), "vehs below"),
            (event(line="oops"), "invalid line"),
        )
        for content, error in cases:
            with self.subTest(error=error):
                path = self.log(42, content)
                with self.assertRaisesRegex(ValueError, error):
                    parse_log(path, 42)

    def test_console_md_json_no_output_default_and_exclusive_optional_file(self):
        self.five_seeds()
        original_files = sorted(self.logs.iterdir())
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            report = main(["--logs", str(self.logs)])
        self.assertIn("# ROAD100 PAX V24 ON", stdout.getvalue())
        self.assertIn("biais", stdout.getvalue().lower())
        self.assertEqual(sorted(self.logs.iterdir()), original_files)
        self.assertFalse((self.root / "report.json").exists())
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            main(["--logs", str(self.logs), "--format", "json"])
        self.assertEqual(json.loads(stdout.getvalue()), report)
        output = self.root / "report.json"
        with contextlib.redirect_stdout(io.StringIO()):
            main(["--logs", str(self.logs), "--out", str(output)])
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), report)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(["--logs", str(self.logs), "--out", str(output)])
        self.assertIn("| revenue |", render_markdown(report))


if __name__ == "__main__":
    unittest.main()
