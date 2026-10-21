#!/usr/bin/env python3
"""Tests de l'analyse cout/profit, sans partie OpenTTD."""
import os
import tempfile
import unittest

from analyse_calibration_quartiles import describe, parse_logs, percentile, report


class QuartileCalibrationTests(unittest.TestCase):
    def test_percentile_and_quartile_boundaries(self):
        self.assertEqual(percentile([10, 20, 30, 40], .25), 17.5)
        self.assertEqual(percentile([10, 20, 30, 40], .5), 25)
        self.assertEqual(percentile([10, 20, 30, 40], .75), 32.5)
        self.assertIsNone(percentile([], .25))

    def test_cost_profit_and_exclusions(self):
        with tempfile.TemporaryDirectory() as root:
            log = os.path.join(root, "reference_seed42_r0.log")
            with open(log, "w", encoding="utf-8") as f:
                f.write("\n".join([
                    "[0] [I] OPEX 1970-1-1 PROJECT_CHOSEN mode=rail src=1 dst=2 cargo=COAL cost=1000 profit=500",
                    "[0] [I] OPEX 1970-1-2 RAIL_BUILD line=1 src=1 dst=2 cargo=COAL dist=80 cost=1500 trains=2",
                    "[0] [I] OPEX 1973-1-1 LINE_REVENUE line=1 mode=rail cargo=COAL year=1973 age=3 pred_prof=500 real_prof=-400 vehs=4",
                    "[0] [I] OPEX 1974-1-1 LINE_REVENUE line=1 mode=rail cargo=COAL year=1974 age=4 pred_prof=500 real_prof=500 vehs=2",
                    "[0] [I] OPEX 1971-1-1 PROJECT_CHOSEN mode=road src=3 dst=4 cargo=PASS cost=200 profit=100",
                    "[0] [I] OPEX 1971-1-2 ROAD_BUILD line=2 src=3 dst=4 cargo=PASS dist=20 cost=-100 vehicles=1",
                    "[0] [I] OPEX 1974-1-1 LINE_REVENUE line=2 mode=road cargo=PASS year=1974 age=3 pred_prof=100 real_prof=20 vehs=1",
                    "[1] [I] OPEX 1974-1-1 RAIL_BUILD line=3 src=1 dst=2 cargo=COAL dist=90 cost=999 trains=1",
                ]) + "\n")
            builds, costs, profits, counts = parse_logs(root, "solo")
            self.assertEqual((len(builds), len(costs), len(profits)), (2, 1, 3))
            self.assertEqual(counts["cost_nonpositive_actual"], 1)
            self.assertEqual(costs[0]["ratio"], 1.5)
            rail = [r for r in profits if r["mode"] == "rail"]
            self.assertEqual([r["ratio"] for r in rail], [-0.4, 1.0])
            self.assertEqual(describe(rail, "profit")["negative_real"], 1)
            self.assertEqual(describe(rail, "profit")["lines"], 1)
            data = report({"solo": root, "duel": root})
            self.assertEqual(data["distance_cuts"]["rail"], [80, 80, 80])
            self.assertTrue(any(r["metric"] == "profit" and r["cargo"] == "COAL"
                                and r["quartile"] == 1 and r["n"] == 2
                                for r in data["rows"]))


if __name__ == "__main__":
    unittest.main()
