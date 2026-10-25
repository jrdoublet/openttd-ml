"""V306: campaign ingestion and calibration on held-out seeds, without games."""
import gzip
import json
import math
from pathlib import Path
import tempfile
import unittest

from analyse_calibration_projets import analyse, cross_validate, load_campaign, num, ratio


def calibration_game(revenue_ratio, count=6):
    return {
        "rows": [
            {
                "mode": "rail",
                "cell": "rail|RAW|80-160|1974-1976",
                "scale": 1.0,
                "pred_rev": 100.0,
                "real_rev": 100.0 * revenue_ratio,
                "pred_run": 20.0,
                "real_run": 20.0,
                "pred_prof": 80.0,
                "real_prof": 100.0 * revenue_ratio - 20.0,
            }
            for _ in range(count)
        ],
        "costs": [],
        "unmatched": 0,
    }


class CalibrationNumericValidityTest(unittest.TestCase):
    def test_nonfinite_numbers_are_unknown_and_use_the_requested_default(self):
        for value in ("nan", "NaN", "inf", "+Infinity", "-inf", "1e999", "-1e999"):
            with self.subTest(value=value):
                self.assertIsNone(num(value))
                self.assertEqual(num(value, -1), -1)
        self.assertEqual(num("0"), 0.0)
        self.assertEqual(num("-120.5"), -120.5)
        self.assertEqual(num("1e3"), 1000.0)

    def test_nonfinite_ratio_inputs_and_overflow_do_not_become_factors(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            for index in range(3):
                args = [100.0, 100.0, 1.0]
                args[index] = value
                with self.subTest(value=value, argument=index):
                    self.assertIsNone(ratio(*args))
        self.assertIsNone(ratio(1e308, 1.0, 2.0))
        self.assertIsNone(ratio(1e308, 1e-308))
        self.assertAlmostEqual(ratio(1200.0, 800.0, 0.5), 0.75)


class CalibrationCrossValidationTest(unittest.TestCase):
    def test_new_test_seeds_are_all_scored_using_training_campaign(self):
        train = {
            ("reference_seed10_r0.log", 10): calibration_game(4.0),
            ("reference_seed20_r0.log", 20): calibration_game(4.0),
        }
        test = {
            ("variant_seed30_r0.log", 30): calibration_game(4.0, count=2),
            ("variant_seed40_r0.log", 40): calibration_game(4.0, count=3),
            ("variant_seed50_r0.log", 50): calibration_game(4.0, count=1),
        }

        report = analyse({"solo": train, "duel": test}, train="solo", test="duel")
        folds = report["cv_train_solo_test_duel"]
        self.assertEqual(report["campaigns"]["duel"]["line_years"], 6)
        self.assertEqual([fold["n"] for fold in folds], [3, 3])
        for fold in folds:
            with self.subTest(fold=fold["fold"]):
                self.assertEqual(fold["raw"], round(math.log(4.0), 4))
                self.assertEqual(fold["mode"], 0.0)
                self.assertEqual(fold["cell"], 0.0)

    def test_partial_overlap_keeps_new_seeds_and_holds_out_shared_seed(self):
        train = {
            ("reference_seed42_r0.log", 42): calibration_game(16.0),
            ("reference_seed100_r0.log", 100): calibration_game(2.0),
        }
        test = {
            ("variant_seed42_r0.log", 42): calibration_game(2.0, count=3),
            ("variant_seed999_r0.log", 999): calibration_game(9.0, count=3),
        }

        folds = cross_validate(train, test)
        self.assertEqual([fold["n"] for fold in folds], [3, 3])
        # Seed 42 must learn only from seed 100. Seed 999 can use both
        # training seeds, whose equally weighted median factor is 9.
        for fold, raw_ratio in zip(folds, (2.0, 9.0)):
            with self.subTest(fold=fold["fold"]):
                self.assertEqual(fold["raw"], round(math.log(raw_ratio), 4))
                self.assertEqual(fold["mode"], 0.0)
                self.assertEqual(fold["cell"], 0.0)

    def test_all_arms_and_repetitions_of_a_seed_are_held_out_together(self):
        train = {
            ("reference_seed42_r0.log", 42): calibration_game(16.0, count=3),
            ("variant_seed42_r1.log", 42): calibration_game(16.0, count=3),
            ("reference_seed100_r0.log", 100): calibration_game(2.0, count=3),
            ("variant_seed100_r1.log", 100): calibration_game(2.0, count=3),
        }
        test = {
            ("reference_seed42_r0.log", 42): calibration_game(2.0, count=3),
            ("variant_seed42_r1.log", 42): calibration_game(2.0, count=3),
            ("reference_seed100_r0.log", 100): calibration_game(16.0, count=3),
            ("variant_seed100_r1.log", 100): calibration_game(16.0, count=3),
        }

        folds = cross_validate(train, test)
        self.assertEqual([fold["n"] for fold in folds], [6, 6])
        for fold, raw_ratio in zip(folds, (2.0, 16.0)):
            with self.subTest(fold=fold["fold"]):
                self.assertEqual(fold["raw"], round(math.log(raw_ratio), 4))
                self.assertEqual(fold["mode"], 0.0)
                self.assertEqual(fold["cell"], 0.0)


class CalibrationSparseTableTest(unittest.TestCase):
    @staticmethod
    def cell_game(revenue_ratio, count=6, mode="rail", cargo="SECONDARY"):
        game = calibration_game(revenue_ratio, count)
        for row in game["rows"]:
            row.update(mode=mode, cell=f"{mode}|{cargo}|80-160|1974-1976")
        return game

    def test_cell_factor_requires_five_valid_training_observations(self):
        for count in (4, 5):
            with self.subTest(valid_training_rows=count):
                cell = self.cell_game(8.0, count)
                # Missing, zero, negative and overflowing ratios must not make
                # a four-observation cell eligible for its own factor.
                for real, pred in ((None, 100.0), (0.0, 100.0), (-100.0, 100.0),
                                   (1e308, 1e-308)):
                    row = dict(cell["rows"][0], real_rev=real, pred_rev=pred)
                    cell["rows"].append(row)
                train = {
                    ("reference_seed10_r0.log", 10): self.cell_game(2.0, cargo="RAW"),
                    ("reference_seed20_r0.log", 20): cell,
                }
                test = {("variant_seed30_r0.log", 30): self.cell_game(8.0, count=2)}

                report = analyse({"solo": train, "duel": test}, train="solo", test="duel")
                folds = report["cv_train_solo_test_duel"]
                self.assertEqual([fold["n"] for fold in folds], [2, 0])
                self.assertEqual(folds[0]["raw"], round(math.log(8.0), 4))
                self.assertEqual(folds[0]["mode"], round(math.log(4.0), 4))
                expected = math.log(4.0) if count == 4 else 0.0
                self.assertEqual(folds[0]["cell"], round(expected, 4))
                json.dumps(report, allow_nan=False)

    def test_held_out_seed_cannot_supply_the_fifth_cell_observation(self):
        train = {
            ("reference_seed10_r0.log", 10): self.cell_game(2.0, cargo="RAW"),
            ("reference_seed20_r0.log", 20): self.cell_game(8.0, count=4),
            ("reference_seed42_r0.log", 42): self.cell_game(8.0, count=1),
            ("variant_seed42_r1.log", 42): self.cell_game(8.0, count=1),
        }
        test = {("variant_seed42_r0.log", 42): self.cell_game(8.0, count=2)}

        folds = cross_validate(train, test)

        self.assertEqual([fold["n"] for fold in folds], [2, 0])
        # After excluding both copies of seed 42, only four cell samples
        # remain: use the mode factor 2, rather than the cell factor 8.
        self.assertEqual(folds[0]["raw"], round(math.log(8.0), 4))
        self.assertEqual(folds[0]["mode"], round(math.log(4.0), 4))
        self.assertEqual(folds[0]["cell"], round(math.log(4.0), 4))

    def test_missing_cell_or_mode_and_empty_training_preserve_test_coverage(self):
        invalid = self.cell_game(0.0)
        invalid["rows"][0]["real_rev"] = None
        cases = {
            "unseen_cell": (self.cell_game(2.0, cargo="RAW"), math.log(2.0)),
            "unseen_mode": (self.cell_game(2.0, mode="road"), math.log(4.0)),
            "no_valid_ratios": (invalid, math.log(4.0)),
            "no_training_games": (None, math.log(4.0)),
        }
        for name, (game, expected) in cases.items():
            with self.subTest(training=name):
                train = {("reference_seed10_r0.log", 10): game} if game else {}
                test = {("variant_seed42_r0.log", 42): self.cell_game(4.0, count=2)}

                folds = cross_validate(train, test)

                self.assertEqual([fold["n"] for fold in folds], [2, 0])
                self.assertEqual(folds[0]["raw"], round(math.log(4.0), 4))
                self.assertEqual(folds[0]["mode"], round(expected, 4))
                self.assertEqual(folds[0]["cell"], round(expected, 4))
                for metric in ("raw", "mode", "cell"):
                    self.assertIsNone(folds[1][metric])
                json.dumps(folds, allow_nan=False)


class CalibrationCampaignLoadingTest(unittest.TestCase):
    @staticmethod
    def game_log(real_revenue=1200):
        return "\n".join([
            "[0] [I] OPEX 1971-1-1 PROJECT_CHOSEN mode=rail src=1 dst=2 cost=1000 profit=500",
            "[0] [I] OPEX 1971-2-1 RAIL_BUILD line=3 src=1 dst=2 cargo=COAL dist=100 cost=1500 trains=2",
            "[0] [I] OPEX 1974-1-1 LINE_REVENUE line=3 mode=rail cargo=COAL year=1974 age=3 "
            f"pred_rev=800 real_rev={real_revenue} pred_prof=500 real_prof=700 "
            "pred_run=300 real_run=500 vehs=4",
            "[0] [I] OPEX 1975-1-1 LINE_REVENUE line=3 mode=rail cargo=COAL year=1975 age=4 "
            "pred_rev=800 real_rev=1600 pred_prof=500 real_prof=800 pred_run=300 real_run=800 vehs=4",
            "[0] [I] OPEX 1975-1-1 LINE_REVENUE line=9 mode=rail cargo=COAL year=1975 age=4 "
            "pred_rev=800 real_rev=400 vehs=2",
            "",
        ])

    @staticmethod
    def write_log(path, content):
        if path.suffix == ".gz":
            with gzip.open(path, "wt", encoding="utf-8") as fh:
                fh.write(content)
        else:
            path.write_text(content, encoding="utf-8")

    def test_text_and_gzip_copies_count_as_one_game(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reference_seed42_r0.log"
            zipped = path.with_suffix(".log.gz")
            self.write_log(path, self.game_log())
            plain_games = load_campaign(directory)
            self.write_log(zipped, self.game_log())
            duplicated_games = load_campaign(directory)
            path.unlink()
            gzip_games = load_campaign(directory)

        self.assertEqual(duplicated_games, plain_games)
        self.assertEqual(gzip_games, plain_games)
        report = analyse({"duel": duplicated_games})["campaigns"]["duel"]
        self.assertEqual(report["games"], 1)
        self.assertEqual(report["line_years"], 2)
        self.assertEqual(report["unmatched"], 1)
        self.assertEqual(report["cost"]["rail"]["n"], 1)
        self.assertEqual(report["revenue_cells"]["rail|RAW|80-160|1974-1976"]["n"], 2)
        self.assertEqual(sum(fold["n"] for fold in report["cv_same_campaign"]), 2)

    def test_deduplication_preserves_arms_seeds_and_repetitions(self):
        names = [
            "reference_seed42_r0.log",
            "variant_seed42_r0.log",
            "reference_seed42_r1.log",
            "reference_seed100_r0.log",
        ]
        with tempfile.TemporaryDirectory() as directory:
            for index, name in enumerate(names):
                path = Path(directory) / name
                content = self.game_log(real_revenue=1200 + index * 400)
                self.write_log(path, content)
                self.write_log(path.with_suffix(".log.gz"), content)
            games = load_campaign(directory)

        self.assertEqual(set(games), {(name, 100 if "seed100" in name else 42) for name in names})
        for index, name in enumerate(names):
            seed = 100 if "seed100" in name else 42
            self.assertEqual(games[(name, seed)]["rows"][0]["real_rev"], 1200 + index * 400)
        report = analyse({"duel": games})["campaigns"]["duel"]
        self.assertEqual(report["games"], 4)
        self.assertEqual(report["line_years"], 8)
        self.assertEqual(report["unmatched"], 4)
        self.assertEqual(report["cost"]["rail"]["n"], 4)
        self.assertEqual([fold["n"] for fold in report["cv_same_campaign"]], [6, 2])

    def test_conflicting_copies_are_reported_instead_of_selected_or_added(self):
        original = self.game_log()
        conflicting = {
            "revenue": original.replace("real_rev=1200", "real_rev=2400"),
            "cost": original.replace("cost=1500", "cost=2000"),
            "fleet": original.replace("trains=2", "trains=3"),
            "unmatched": original.replace("line=9", "line=3"),
        }
        for field, content in conflicting.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "reference_seed42_r0.log"
                zipped = path.with_suffix(".log.gz")
                self.write_log(path, original)
                self.write_log(zipped, content)
                with self.assertRaises(ValueError) as caught:
                    load_campaign(directory)
                self.assertIn(str(path), str(caught.exception))
                self.assertIn(str(zipped), str(caught.exception))

    def test_nonfinite_log_values_stay_unknown_in_text_and_gzip_reports(self):
        for token in ("nan", "inf", "-Infinity", "1e999"):
            for suffix in (".log", ".log.gz"):
                with self.subTest(token=token, suffix=suffix), tempfile.TemporaryDirectory() as directory:
                    content = self.game_log().replace("cost=1500", f"cost={token}")
                    content = content.replace("year=1974", f"year={token}")
                    content = content.replace("real_rev=1200", f"real_rev={token}")
                    content = content.replace("pred_prof=500", f"pred_prof={token}")
                    content = content.replace("real_run=500", f"real_run={token}")
                    path = Path(directory) / ("reference_seed42_r0" + suffix)
                    self.write_log(path, content)
                    games = load_campaign(directory)

                    row = next(iter(games.values()))["rows"][0]
                    for field in ("year", "real_rev", "pred_prof", "real_run"):
                        self.assertIsNone(row[field], field)
                    self.assertEqual(row["cell"], "rail|RAW|80-160|?")
                    report = analyse({"duel": games})
                    summary = report["campaigns"]["duel"]
                    self.assertEqual(summary["line_years"], 2)
                    self.assertEqual(summary["unmatched"], 1)
                    self.assertEqual(summary["cost"], {})
                    self.assertEqual(summary["revenue_cells"][row["cell"]], {"n": 0})
                    self.assertEqual(summary["profit_cells"][row["cell"]], {"n": 0})
                    self.assertEqual(summary["running_cells"][row["cell"]], {"n": 0})
                    # The following finite year still contributes exactly once.
                    self.assertEqual(summary["revenue_cells"]["rail|RAW|80-160|1974-1976"]["n"], 1)
                    self.assertEqual(sum(fold["n"] for fold in summary["cv_same_campaign"]), 1)
                    json.dumps(report, allow_nan=False)

    def test_overflowed_ratios_are_excluded_without_losing_observed_zero_cost(self):
        for suffix in (".log", ".log.gz"):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as directory:
                content = self.game_log().replace("cost=1000", "cost=1e-308")
                content = content.replace("cost=1500", "cost=1e308")
                content = content.replace("pred_rev=800", "pred_rev=1e-308")
                content = content.replace("real_rev=1200", "real_rev=1e308")
                # A zero operating cost is a known value, even though the log-error
                # metric deliberately requires a strictly positive ratio.
                content = content.replace("real_run=500", "real_run=0")
                path = Path(directory) / ("reference_seed42_r0" + suffix)
                self.write_log(path, content)
                games = load_campaign(directory)

                self.assertEqual(next(iter(games.values()))["rows"][0]["real_run"], 0.0)
                report = analyse({"duel": games})
                summary = report["campaigns"]["duel"]
                self.assertEqual(summary["cost"]["rail"], {"n": 0})
                self.assertEqual(summary["cost"]["rail|80-160"], {"n": 0})
                self.assertEqual(summary["revenue_cells"]["rail|RAW|80-160|1974-1976"], {"n": 0})
                self.assertEqual(sum(fold["n"] for fold in summary["cv_same_campaign"]), 0)
                json.dumps(report, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
