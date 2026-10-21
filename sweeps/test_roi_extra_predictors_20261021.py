#!/usr/bin/env python3
"""Verifier la chronologie et les variables supplementaires, sans Docker."""
import os
import tempfile
import unittest
import importlib.util

if importlib.util.find_spec("numpy") is None:
    raise unittest.SkipTest("optional numpy dependency is unavailable")

from analyse_roi_extra_predictors_20261021 import (
    add_features, cross_validate, features_per_build,
)
from analyse_roi_predictors_20261021 import parse


class ExtraPredictorTests(unittest.TestCase):
    def test_network_feature_snapshot_and_post_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            f = os.path.join(folder, "reference_seed42_r0.log")
            with open(f, "w", encoding="utf-8") as fp:
                fp.write("\n".join([
                    "[0] [I] OPEX 1970-1-1 PROJECT_CHOSEN mode=air src=1 dst=2 cargo=PASS cost=1000 profit=500 roi=500",
                    "[0] [I] OPEX 1970-1-1 AIR_BUILD line=1 arm=newpair src=1 dst=2 cargo=PASS dist=100 cost=1000 planes=1 engine=223",
                    "[0] [I] OPEX 1970-1-2 PROJECT_CHOSEN mode=air src=1 dst=3 cargo=PASS cost=1000 profit=500 roi=500",
                    "[0] [I] OPEX 1970-1-2 AIR_BUILD line=2 arm=hubsite src=1 dst=3 cargo=PASS dist=100 cost=1000 planes=1 engine=223",
                    "[0] [I] OPEX 1970-1-3 PROJECT_CHOSEN mode=rail src=4 dst=5 cargo=COAL cost=1000 profit=500 roi=500",
                    "[0] [I] OPEX 1970-1-3 RAIL_ATTEMPT src=4 dst=5 ok=1 len=115 quote=1500 model=1000 pre=900 iters=50 pred_astar=250",
                    "[0] [I] OPEX 1970-1-3 RAIL_BUILD line=3 src=4 dst=5 cargo=COAL dist=100 cost=1500 trains=2 wagons=4",
                    "[0] [I] OPEX 1972-1-1 LINE_REVENUE line=1 mode=air age=2 year=1972 cargo=PASS real_prof=100 pred_prof=500 vehs=1",
                    "[0] [I] OPEX 1972-1-1 LINE_REVENUE line=2 mode=air age=2 year=1972 cargo=PASS real_prof=200 pred_prof=500 vehs=1",
                    "[0] [I] OPEX 1972-1-1 LINE_REVENUE line=3 mode=rail age=2 year=1972 cargo=COAL real_prof=200 pred_prof=500 vehs=2",
                ]) + "\n")
            x, counts = features_per_build(folder)
            a = x[(42, "air", "1")]
            b = x[(42, "air", "2")]
            rail = x[(42, "rail", "3")]
            self.assertEqual(a["prior_stage"], 0)
            self.assertEqual(a["prior_src_degree"], 0)
            self.assertEqual(b["prior_stage"], 1)
            self.assertEqual(b["prior_src_degree"], 1)
            self.assertEqual(b["prior_dst_degree"], 0)
            self.assertEqual(rail["prior_stage"], 0)  # mode-separated
            self.assertEqual(rail["post_route_length"], 115)
            self.assertEqual(counts.get("no_prechoice_snapshot", 0), 0)
            base, _ = parse(folder, "duel")
            matched, stats = add_features(base, folder)
            self.assertEqual(len(matched), 3)
            self.assertEqual(stats["joined_mature"], 3)

    def test_no_games_returns_no_scores(self):
        self.assertEqual(cross_validate([]), {})


if __name__ == "__main__":
    unittest.main()
