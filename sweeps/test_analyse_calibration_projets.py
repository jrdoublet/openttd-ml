"""V306: campaign ingestion and calibration on held-out seeds, without games."""
import gzip
import math
from pathlib import Path
import tempfile
import unittest

from analyse_calibration_projets import analyse, cross_validate, load_campaign


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


if __name__ == "__main__":
    unittest.main()
