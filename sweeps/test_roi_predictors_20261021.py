#!/usr/bin/env python3
"""Small read-only ROI-calibration parser checks, no simulation required."""
import os
import gzip
import tempfile
import unittest
import importlib.util

if importlib.util.find_spec("numpy") is None:
    raise unittest.SkipTest("optional numpy dependency is unavailable")

from analyse_roi_predictors_20261021 import parse, quartiles, predict


class RoiPredictorsTest(unittest.TestCase):
    @staticmethod
    def _one_rail_game():
        return "\n".join([
            "[0] [I] OPEX 1970-1-1 PROJECT_CHOSEN rank=1 mode=rail kind=freight cargo=COAL src=12 dst=22 cost=1000 profit=500",
            "[0] [I] OPEX 1970-1-2 RAIL_BUILD line=1 src=12 dst=22 cargo=COAL dist=100 cost=1500 trains=1",
            "[0] [I] OPEX 1972-1-1 LINE_REVENUE line=1 mode=rail cargo=COAL year=1972 age=2 real_prof=200 vehs=1",
        ]) + "\n"

    def test_compressed_log_only(self):
        with tempfile.TemporaryDirectory() as folder:
            with gzip.open(os.path.join(folder, "reference_seed42_r0.log.gz"), "wt", encoding="utf-8") as fh:
                fh.write(self._one_rail_game())
            rows, counts = parse(folder, "duel")
            self.assertEqual((len(rows), counts["games"], counts["matched_rail"]), (1, 1, 1))

    def test_plain_and_compressed_identical_are_one_game(self):
        with tempfile.TemporaryDirectory() as folder:
            data = self._one_rail_game()
            with open(os.path.join(folder, "reference_seed42_r0.log"), "w", encoding="utf-8") as fh:
                fh.write(data)
            with gzip.open(os.path.join(folder, "reference_seed42_r0.log.gz"), "wt", encoding="utf-8") as fh:
                fh.write(data)
            rows, counts = parse(folder, "duel")
            self.assertEqual((len(rows), counts["games"], counts["matched_rail"]), (1, 1, 1))

    def test_conflicting_copy_fails_even_when_count_same(self):
        with tempfile.TemporaryDirectory() as folder:
            with open(os.path.join(folder, "reference_seed42_r0.log"), "w", encoding="utf-8") as fh:
                fh.write(self._one_rail_game())
            with gzip.open(os.path.join(folder, "reference_seed42_r0.log.gz"), "wt", encoding="utf-8") as fh:
                fh.write(self._one_rail_game().replace("real_prof=200", "real_prof=205"))
            with self.assertRaisesRegex(ValueError, "copies de journal ROI contradictoires"):
                parse(folder, "duel")

    def test_numeric_seed_alias_is_not_an_independent_roi_game(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ("reference_seed1_r0.log", "reference_seed01_r0.log"):
                with open(os.path.join(folder, name), "w", encoding="utf-8") as fh:
                    fh.write(self._one_rail_game())
            with self.assertRaisesRegex(ValueError, "identite de partie ROI ambigue"):
                parse(folder, "duel")

    def test_numeric_repeat_alias_is_not_hidden_by_compression(self):
        with tempfile.TemporaryDirectory() as folder:
            with open(os.path.join(folder, "reference_seed42_r0.log"), "w", encoding="utf-8") as fh:
                fh.write(self._one_rail_game())
            with gzip.open(os.path.join(folder, "reference_seed42_r00.log.gz"),
                           "wt", encoding="utf-8") as fh:
                fh.write(self._one_rail_game())
            with self.assertRaisesRegex(ValueError, "identite de partie ROI ambigue"):
                parse(folder, "duel")

    def test_distinct_roi_arms_seeds_and_repeats_remain_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ("reference_seed42_r0.log", "variant_seed42_r0.log",
                         "reference_seed42_r1.log", "reference_seed100_r0.log"):
                with open(os.path.join(folder, name), "w", encoding="utf-8") as fh:
                    fh.write(self._one_rail_game())
            rows, counts = parse(folder, "duel")
            self.assertEqual((len(rows), counts["games"], counts["matched_rail"]),
                             (4, 4, 4))

    def test_roi_from_chosen_to_mature_build(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "reference_seed42_r0.log")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join([
                    "[0] [I] OPEX 1970-1-1 PROJECT_CHOSEN rank=1 mode=rail kind=freight cargo=COAL src=12 dst=22 dist=100 cost=1000 profit=500 roi=500",
                    "[0] [I] OPEX 1970-1-2 RAIL_BUILD line=1 src=12 dst=22 cargo=COAL dist=100 cost=1500 reuse=1 trains=2",
                    "[0] [I] OPEX 1971-1-1 LINE_REVENUE line=1 mode=rail cargo=COAL year=1971 age=1 pred_prof=500 real_prof=10000 vehs=2",
                    "[0] [I] OPEX 1972-1-1 LINE_REVENUE line=1 mode=rail cargo=COAL year=1972 age=2 pred_prof=500 real_prof=-200 vehs=4",
                    "[0] [I] OPEX 1973-1-1 LINE_REVENUE line=1 mode=rail cargo=COAL year=1973 age=3 pred_prof=500 real_prof=500 vehs=2",
                    "[0] [I] OPEX 1970-1-1 PROJECT_CHOSEN rank=0 mode=air cargo=PASS src=3 dst=4 dist=180 cost=1000 profit=1000 roi=1000",
                    "[0] [I] OPEX 1970-1-1 AIR_BUILD arm=hubsite line=2 src=3 dst=4 cargo=PASS dist=180 cost=1000 planes=1",
                    "[0] [I] OPEX 1972-1-1 LINE_REVENUE line=2 mode=air cargo=PASS year=1972 age=2 pred_prof=1000 real_prof=200 vehs=1",
                    "[1] [I] OPEX 1972-1-1 LINE_REVENUE line=2 mode=air cargo=PASS year=1972 age=2 pred_prof=1000 real_prof=999999 vehs=1",
                ]) + "\n")
            rows, counts = parse(directory, "duel")
            self.assertEqual(len(rows), 2)
            rail = next(r for r in rows if r["mode"] == "rail")
            air = next(r for r in rows if r["mode"] == "air")
            self.assertEqual(rail["n_years"], 2)
            self.assertEqual(rail["real_profit"], 200.)  # -100 and +500
            self.assertAlmostEqual(rail["roi_pred"], 50.)
            self.assertAlmostEqual(rail["roi_real"], 200. / 1500. * 100.)
            self.assertEqual(rail["reuse"], "1")
            self.assertEqual(air["subtype"], "hubsite")
            self.assertAlmostEqual(air["roi_real"], 20.)
            self.assertEqual(counts["matched_rail"], 1)
            self.assertEqual(counts["matched_air"], 1)

    def test_quartiles_and_ridge_basic(self):
        rows = []
        for seed in range(20):
            for i in range(4):
                roi = 15. + seed + i
                rows.append({
                    "seed": seed, "line": str(i), "mode": "rail",
                    "arm": "duel", "cargo": "COAL" if i % 2 else "WOOD",
                    "roi_pred": roi, "roi_real": .5 * roi + i * 2,
                    "dist": 20. + i * 10, "year": 1971 + i,
                    "rank": i, "capital": 1000. + seed,
                    "subtype": "freight", "reuse": "0",
                    "profit_ratio": 1., "n_years": 2,
                })
        train = [r for r in rows if r["seed"] < 16]
        test = [r for r in rows if r["seed"] >= 16]
        fit = predict(train, test, ("roi", "roi2", "dist"))
        self.assertEqual(len(fit), len(test))
        self.assertLess(max(abs(a - b["roi_real"]) for a,b in zip(fit,test)), 4)
        self.assertEqual(sum(x["n"] for x in quartiles(rows, "roi_pred")), 80)


if __name__ == "__main__":
    unittest.main()
