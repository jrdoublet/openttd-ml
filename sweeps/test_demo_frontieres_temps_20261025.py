"""FRONT-PAX-2 : comparaison physique PASS hors moteur, sans changer les bornes."""

import contextlib
import io
import json
import math
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

from demo_frontieres_temps_20261021 import (
    EVIDENCE,
    crossover,
    days_per_tile_boundary,
    days_per_tile_economy,
    demo,
    illustrative_pass_stop_sensitivity,
    main,
    maneuver_c100,
    optional_raw_duel_counts,
    passenger_crossover_with_stops,
)


class PassengerPhysicalCrossoverTest(unittest.TestCase):
    def test_same_unit_baseline_and_independent_fixed_times(self):
        ground = maneuver_c100(570.0)
        for converter in (days_per_tile_boundary, days_per_tile_economy):
            with self.subTest(converter=converter.__name__):
                tau_gap = converter(115.0) - converter(570.0)
                self.assertGreater(tau_gap, 0)
                base = crossover(115.0, 570.0, ground, converter)
                self.assertAlmostEqual(passenger_crossover_with_stops(
                    115.0, 570.0, ground, 0.0, 0.0, converter), base)
                loading = 41.0 / 74.0
                rail_stop = 640.0 / 74.0
                self.assertAlmostEqual(passenger_crossover_with_stops(
                    115.0, 570.0, ground, loading, rail_stop, converter),
                    base + (loading - rail_stop) / tau_gap)

    def test_nonpositive_tau_gap_has_no_rail_to_air_distance_switch(self):
        for rail_speed, air_speed in ((320.0, 320.0), (400.0, 320.0)):
            for converter in (days_per_tile_boundary, days_per_tile_economy):
                with self.subTest(rail=rail_speed, converter=converter.__name__):
                    self.assertIsNone(passenger_crossover_with_stops(
                        rail_speed, air_speed, 15.0, 0.55, 8.65, converter))

    def test_negative_or_zero_net_fixed_means_air_wins_from_zero(self):
        for rail_stop in (15.55, 20.0):
            self.assertEqual(passenger_crossover_with_stops(
                115.0, 570.0, 15.0, 0.55, rail_stop,
                days_per_tile_economy), 0.0)

    def test_illustrative_grid_preserves_conversion_and_label(self):
        s = illustrative_pass_stop_sensitivity()
        self.assertEqual(s["distance_definition"],
                         "unclamped Manhattan city-centre tiles; PASS only")
        cases = {c["scenario"]: c for c in s["cases"]}
        self.assertEqual(len(cases), 6)
        baseline = cases["rail_stop_zero__air_load_zero"]
        self.assertAlmostEqual(baseline["boundary_c100_pass_tiles"], 62.98, delta=0.02)
        self.assertAlmostEqual(baseline["economy_c121_pass_tiles"], 78.44, delta=0.02)
        five = cases["rail_stop_zero__air_pass100_5_departures"]
        two = cases["rail_stop_zero__air_pass100_2_departures"]
        rail_dwell = cases["rail_wagon40_v216f100__air_load_zero"]
        self.assertAlmostEqual(five["air_loading_days_per_visit"], 41.0 / 74.0)
        self.assertAlmostEqual(two["air_loading_days_per_visit"], 121.0 / 74.0)
        self.assertAlmostEqual(rail_dwell["rail_stop_days_per_loaded_trip"], 640.0 / 74.0)
        for field in ("boundary_c100_pass_tiles", "economy_c121_pass_tiles"):
            self.assertGreater(two[field], five[field])
            self.assertGreater(five[field], baseline[field])
            self.assertLess(rail_dwell[field], baseline[field])
        self.assertTrue(all(math.isfinite(c["boundary_c100_pass_tiles"])
                            for c in cases.values()))


class CliCompatibilityTest(unittest.TestCase):
    def test_optional_raw_distance_refuses_invalid_tile_ids(self):
        # Un sentinelle -1 se transformerait en colonne 255 et ligne -1,
        # et int(200.5) inventerait une position sur la carte.
        for bad in (-1.0, 65536.0, 200.5, float("nan"), float("inf"), 10 ** 500):
            with self.subTest(tile=bad):
                air = {"mode": "air", "src_tile": bad, "dst_tile": 200.0}
                with patch("analyse_roi_predictors_20261021.parse",
                           return_value=([air], {"games": 1})):
                    with self.assertRaisesRegex(ValueError, "identifiant de tuile invalide"):
                        optional_raw_duel_counts(Path("historical_duel"), 64)

    def test_optional_raw_distance_keeps_valid_map_edges(self):
        rows = [
            {"mode": "air", "src_tile": 0.0, "dst_tile": 200.0},
            {"mode": "air", "src_tile": 0.0, "dst_tile": 65535.0},
        ]
        with patch("analyse_roi_predictors_20261021.parse",
                   return_value=(rows, {"games": 1})):
            actual = optional_raw_duel_counts(Path("historical_duel"), 64)
        self.assertEqual(actual["mature_air_passengers"], 2)
        self.assertEqual(actual["air_center_manhattan_eq200"], 1)
        self.assertEqual(actual["air_center_manhattan_gt200"], 1)

    def test_demo_retains_existing_outputs_and_adds_separate_sensitivity(self):
        data = demo(EVIDENCE)
        self.assertIn("observed", data)
        self.assertIn("models_hypothetical", data)
        self.assertIn("passenger_reclassification", data)
        self.assertIn("hypothetical_road_to_rail_fare_sensitivity", data)
        self.assertIn("physical_pass_stop_sensitivity_hypothetical", data)
        self.assertEqual(data["models_hypothetical"]["1970_illustrative_rail115_air570"]
                         ["boundary_c100_direct"],
                         data["physical_pass_stop_sensitivity_hypothetical"]["cases"][0]
                         ["boundary_c100_pass_tiles"])

    def test_existing_json_and_text_cli_still_work(self):
        for flags in ([], ["--json"]):
            with self.subTest(flags=flags), patch.object(
                    sys, "argv", ["demo_frontieres_temps_20261021.py", *flags]):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    main()
                rendered = output.getvalue()
                if flags:
                    parsed = json.loads(rendered)
                    self.assertEqual(len(parsed["physical_pass_stop_sensitivity_hypothetical"]
                                         ["cases"]), 6)
                    self.assertIn("models_hypothetical", parsed)
                else:
                    self.assertIn("Frontieres rail->air", rendered)
                    self.assertIn("PASS physique, sensibilite", rendered)
                    self.assertIn("ROUTE->RAIL", rendered)


if __name__ == "__main__":
    unittest.main()
