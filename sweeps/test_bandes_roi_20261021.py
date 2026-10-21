#!/usr/bin/env python3
"""Tests des seuils existants, des kilometres AIR et de la neutralite intermodale."""
import os
import tempfile
import unittest

from evaluer_bandes_roi_20261021 import (
    assign, factor_table, groups_for_distance, linear_cost_params,
    top5_counterfactual,
)


BOUNDS = (7, 7, 200, 7, 200, 200, 200, 512)


class BandsTests(unittest.TestCase):
    def test_stage_boundaries_and_subdivision(self):
        self.assertEqual(groups_for_distance(7, BOUNDS)[0], "road")
        self.assertEqual(groups_for_distance(8, BOUNDS)[0], "rail")
        self.assertEqual(groups_for_distance(199, BOUNDS)[0], "rail")
        self.assertEqual(groups_for_distance(200, BOUNDS)[0], "air_rail")
        self.assertEqual(groups_for_distance(201, BOUNDS)[0], "air")
        self.assertEqual(groups_for_distance(513, BOUNDS)[0], "long")
        self.assertEqual(groups_for_distance(100, BOUNDS)[-1]["rail_quarter_points"],
                         [55, 103, 151])

    def test_air_build_distance_not_manhattan(self):
        # src town (x=10,y=20), dst town (x=160,y=100), Manhattan=230;
        # built flight distance may be ~170. It must NOT be in rail band.
        src = 10 + 20*256
        dst = 160 + 100*256
        rows = [{"mode":"air", "src_tile":src, "dst_tile":dst, "dist":170.},
                {"mode":"rail", "src_tile":src, "dst_tile":dst, "dist":170.}]
        assign(rows, BOUNDS)
        self.assertEqual(rows[0]["band_dist"],230.)
        self.assertEqual(rows[0]["cascade_band"],"air")
        self.assertEqual(rows[1]["cascade_band"],"rail")

    def test_only_rail_has_learned_cost_modifiers(self):
        rows = []
        for mode in ("air","rail","road"):
            for d in (50.,100.,150.,200.):
                k=1.0+0.004*d
                rows.append({"mode":mode,"dist":d,"capital":10000.,
                             "real_capital":10000*k,"sub4_band":"d"+str(d)})
        linear = linear_cost_params(rows)
        self.assertAlmostEqual(linear["slope_per_tile"], .004, 6)
        self.assertAlmostEqual(linear["intercept"], 1., 6)
        factors = factor_table(rows)
        self.assertEqual(factors[("air","__fallback__")], 1.)
        self.assertEqual(factors[("road","__fallback__")], 1.)
        self.assertTrue(any(factors[("rail","d"+str(d))]!=1. for d in (50.,200.)))

    def test_uniform_minus_20_percent_mean_in_every_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            f = os.path.join(folder, "reference_seed42_r0.log")
            with open(f, "w", encoding="utf-8") as output:
                output.write("\n".join([
                    "[0] [I] OPEX 1972-1-1 PORTFOLIO_RANK rank=0 mode=air dist=230 rank_score=300",
                    "[0] [I] OPEX 1972-1-1 PORTFOLIO_RANK rank=1 mode=rail dist=70 rank_score=200",
                    "[0] [I] OPEX 1972-1-1 PORTFOLIO_RANK rank=2 mode=road dist=30 rank_score=100",
                    "[0] [I] OPEX 1972-2-1 PORTFOLIO_RANK rank=0 mode=fleet dist=0 rank_score=150",
                    "[0] [I] OPEX 1972-2-1 PORTFOLIO_RANK rank=1 mode=rail dist=180 rank_score=100",
                ]) + "\n")
            fct = {("air","__fallback__"):1.,("road","__fallback__"):1.,
                   ("rail","__fallback__"):1.,
                   ("rail","rail_r2"):1.25,("rail","rail_r4"):.75}
            result = top5_counterfactual(folder, BOUNDS, fct)
            self.assertEqual(result["snapshots"], 2)
            self.assertEqual(result["multi_family_snapshots"], 2)
            for mode in ("air","road","rail"):
                self.assertAlmostEqual(
                    result["score_mass_by_family"][mode]["weighted_mean_new_multiplier"], .8)
            self.assertEqual(result["score_mass_by_family"]["air"]["ranked_entries"], 2)
            self.assertAlmostEqual(result["score_mass_by_family"]["air"]["min_multiplier"], .8)
            self.assertAlmostEqual(result["score_mass_by_family"]["road"]["min_multiplier"], .8)


if __name__ == "__main__":
    unittest.main()
