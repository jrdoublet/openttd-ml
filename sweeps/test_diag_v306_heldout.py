"""V306 independent-seed transfer report; host-only, with no AI modification."""

import contextlib
import io
import json
import math
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_v306_heldout import analyze, evaluate, main
from sweeps.test_analyse_calibration_projets import calibration_game


def game_log(revenue_ratio):
    return (
        "[0] [I] OPEX 1971-1-1 RAIL_BUILD line=3 src=1 dst=2 "
        "cargo=COAL dist=100 cost=1500 trains=2\n"
        "[0] [I] OPEX 1974-1-1 LINE_REVENUE line=3 mode=rail cargo=COAL "
        f"year=1974 age=3 pred_rev=100 real_rev={100 * revenue_ratio} "
        "pred_prof=80 real_prof=300 pred_run=20 real_run=20 vehs=2\n"
    )


class HeldoutTransferContracts(unittest.TestCase):
    def test_disjoint_heldout_error_reconciles_with_mode_and_folds(self):
        train = {
            (f"reference_seed{seed}_r0.log", seed): calibration_game(4.0)
            for seed in (10, 20)
        }
        test = {
            (f"reference_seed{seed}_r0.log", seed): calibration_game(4.0, count=2)
            for seed in (30, 40, 50)
        }
        report = evaluate(train, test)
        self.assertEqual(report["train_and_heldout_seed_overlap"], [])
        self.assertEqual(report["training"]["games"], 2)
        self.assertEqual(report["heldout"]["distinct_seeds"], 3)
        self.assertEqual(report["heldout"]["valid_revenue_rows"], 6)
        self.assertEqual(report["heldout"]["invalid_or_missing_revenue_ratio_rows"], 0)
        self.assertEqual(report["heldout_median_abs_log_error"]["n"], 6)
        self.assertEqual(report["heldout_median_abs_log_error"]["raw"],
                         round(math.log(4), 4))
        self.assertEqual(report["heldout_median_abs_log_error"]["mode"], 0)
        self.assertEqual(report["heldout_median_abs_log_error"]["cell"], 0)
        self.assertEqual([fold["n"] for fold in report["heldout_seed_folds"]], [4, 2])
        self.assertEqual(report["heldout_error_by_mode"]["rail"]["n"], 6)
        json.dumps(report, allow_nan=False)

    def test_same_seed_across_arms_and_repetitions_is_never_independent(self):
        train = {("reference_seed42_r0.log", 42): calibration_game(4)}
        for test_name in ("reference_seed42_r1.log", "rail_cal_1_seed42_r0.log"):
            with self.subTest(test_name=test_name):
                test = {(test_name, 42): calibration_game(4)}
                with self.assertRaisesRegex(ValueError, "seeds overlap"):
                    evaluate(train, test)

    def test_unobserved_revenue_keeps_error_coverage_separate(self):
        train = {("reference_seed10_r0.log", 10): calibration_game(4.0)}
        candidate = calibration_game(4.0, count=3)
        candidate["rows"][1]["real_rev"] = None
        candidate["rows"][2]["pred_rev"] = 0
        test = {("reference_seed20_r0.log", 20): candidate}
        report = evaluate(train, test)
        self.assertEqual(report["heldout"]["mature_line_years"], 3)
        self.assertEqual(report["heldout"]["valid_revenue_rows"], 1)
        self.assertEqual(report["heldout"]["invalid_or_missing_revenue_ratio_rows"], 2)
        self.assertEqual(report["heldout_error_by_mode"]["rail"]["n"], 1)

    def test_empty_training_or_test_are_explicit_errors(self):
        one = {("reference_seed42_r0.log", 42): calibration_game(4)}
        with self.assertRaisesRegex(ValueError, "nonempty"):
            evaluate({}, one)
        with self.assertRaisesRegex(ValueError, "nonempty"):
            evaluate(one, {})

    def test_sparse_test_cell_does_not_invent_support_or_factor(self):
        train = {("reference_seed10_r0.log", 10): calibration_game(4.0, count=4)}
        test = {("reference_seed20_r0.log", 20): calibration_game(4.0, count=2)}
        report = evaluate(train, test)
        self.assertEqual(report["eligible_training_cells"], {})
        self.assertEqual(report["heldout_median_abs_log_error"]["mode"], 0)
        self.assertEqual(report["heldout_median_abs_log_error"]["cell"], 0)
        self.assertEqual(next(iter(report["heldout_cell_seed_support"].values()))["n_distinct_seeds"], 1)


class HeldoutArmFilterContracts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.train = self.folder / "train"
        self.heldout = self.folder / "heldout"
        self.train.mkdir()
        self.heldout.mkdir()
        (self.train / "reference_seed10_r0.log").write_text(game_log(4), encoding="utf-8")
        (self.heldout / "reference_seed20_r0.log").write_text(game_log(4), encoding="utf-8")
        # The intervention's rows cannot leak into the held-out reference.
        (self.heldout / "rail_cal_1_seed20_r0.log").write_text(
            game_log(1000), encoding="utf-8",
        )
        self.output = self.folder / "v306.json"

    def test_reference_filter_excludes_variant_before_calibration(self):
        report = analyze(self.train, self.heldout, expected_train=1, expected_heldout=1)
        self.assertEqual(report["heldout"]["games"], 1)
        self.assertEqual(report["heldout"]["valid_revenue_rows"], 1)
        self.assertEqual(report["heldout_median_abs_log_error"]["mode"], 0)
        self.assertEqual(report["sources"]["heldout_arm"], "reference")

    def test_exact_arm_or_expected_count_failure(self):
        with self.assertRaisesRegex(ValueError, "expected 1 training and 1 heldout"):
            analyze(self.train, self.heldout, heldout_arm="not_there",
                    expected_train=1, expected_heldout=1)
        with self.assertRaisesRegex(ValueError, "expected 1 training and 2 heldout"):
            analyze(self.train, self.heldout, expected_train=1, expected_heldout=2)

    def test_cli_json_no_overwrite(self):
        output = io.StringIO()
        args = ["--train", str(self.train), "--heldout", str(self.heldout),
                "--expected-train", "1", "--expected-heldout", "1",
                "--out", str(self.output)]
        with contextlib.redirect_stdout(output):
            main(args)
        self.assertEqual(json.loads(output.getvalue())["seed_overlap"], [])
        source = self.output.read_text(encoding="utf-8")
        self.assertEqual(json.loads(source)["heldout"]["games"], 1)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main(args)
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(self.output.read_text(encoding="utf-8"), source)


if __name__ == "__main__":
    unittest.main()
