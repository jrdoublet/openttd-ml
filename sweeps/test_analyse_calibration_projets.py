"""V306: calibration on held-out seeds, without running a game."""
import math
import unittest

from analyse_calibration_projets import analyse, cross_validate


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


if __name__ == "__main__":
    unittest.main()
