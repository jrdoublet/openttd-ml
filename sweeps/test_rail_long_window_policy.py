"""Contract tests for the offline staged-window policy (no AI mutation)."""

import unittest

from sweeps.rail_long_window_policy import (
    DistanceBand, RailLongWindowPolicy, fresh_bands, window,
)


class TestRailLongWindow(unittest.TestCase):
    def test_initial_and_widening_only_fresh_tiles(self):
        self.assertEqual(window(0), DistanceBand(224, 288))
        self.assertEqual(fresh_bands(0), (DistanceBand(224, 288),))
        self.assertEqual(window(1), DistanceBand(208, 304))
        self.assertEqual(fresh_bands(1),
                         (DistanceBand(208, 223), DistanceBand(289, 304)))
        self.assertEqual(window(2), DistanceBand(201, 320))
        self.assertEqual(fresh_bands(2),
                         (DistanceBand(201, 207), DistanceBand(305, 320)))
        self.assertEqual(fresh_bands(3), (DistanceBand(321, 336),))
        self.assertEqual(window(-1), None)

    def test_map_span_and_no_duplicated_normal_band(self):
        self.assertIsNone(window(0, map_width=64, map_height=64))
        self.assertEqual(window(0, map_width=128, map_height=128),
                         DistanceBand(224, 254))
        self.assertEqual(fresh_bands(1, map_width=128, map_height=128),
                         (DistanceBand(208, 223),))
        self.assertEqual(window(10, map_width=128, map_height=128),
                         DistanceBand(201, 254))
        self.assertEqual(fresh_bands(10, map_width=128, map_height=128), ())

    def test_no_early_air_coverage_and_no_automatic_freight(self):
        p = RailLongWindowPolicy()
        for y in (1970, 1971, 1972):
            out = p.observe(y, 12, mode_air=True,
                            air_top30={1970: 0.67, 1971: 0.91, 1972: 0.97}[y],
                            available_cash=1_000_000)
            self.assertEqual(out, ())
        out = p.observe(1973, 12, mode_air=True, air_top30=0.98,
                        available_cash=1_000_000)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].mode, "pax")
        self.assertEqual(out[0].reason, "coverage_plateau")
        self.assertEqual(p.freight.stage, -1)

    def test_freight_is_independent_from_air_and_rail_pax(self):
        p = RailLongWindowPolicy()
        self.assertEqual(p.observe(1972, 1, mode_air=True, air_top30=0.2,
                        freight_short_startable=0, available_cash=200_000), ())
        out = p.observe(1972, 2, mode_air=True, air_top30=0.2,
                        freight_short_startable=1, available_cash=200_000)
        self.assertEqual([(e.mode, e.stage) for e in out], [("freight", 0)])
        self.assertEqual(p.pax.stage, -1)

    def test_rail_only_pax_shortage_fallback(self):
        p = RailLongWindowPolicy()
        p.observe(1972, 1, mode_air=False, rail_pax_top30=0.0,
                  pax_short_startable=0, available_cash=200_000)
        out = p.observe(1972, 2, mode_air=False, rail_pax_top30=0.0,
                        pax_short_startable=0, available_cash=200_000)
        self.assertEqual([(e.mode, e.reason) for e in out],
                         [("pax", "short_pax_pool")])

    def test_monthly_idempotence_and_12_month_cadence(self):
        p = RailLongWindowPolicy()
        p.observe(1972, 1, mode_air=False,
                  freight_short_startable=0, available_cash=300_000)
        p.observe(1972, 2, mode_air=False,
                  freight_short_startable=0, available_cash=300_000)
        self.assertEqual(p.observe(1972, 2, mode_air=False,
                         freight_short_startable=0, available_cash=300_000), ())
        for m in range(3, 13):
            self.assertEqual(p.observe(1972, m, mode_air=False,
                             freight_short_startable=0, available_cash=300_000), ())
        self.assertEqual(p.observe(1973, 1, mode_air=False,
                         freight_short_startable=0, available_cash=300_000), ())
        out = p.observe(1973, 2, mode_air=False,
                        freight_short_startable=0, available_cash=300_000)
        self.assertEqual([(e.mode, e.stage, e.new_bands) for e in out],
                         [("freight", 1, (
                             DistanceBand(208, 223), DistanceBand(289, 304)))])

    def test_cash_guard_and_no_trigger_if_rail_disabled(self):
        p = RailLongWindowPolicy()
        for month in range(1, 12):
            self.assertEqual(p.observe(1972, month, mode_air=False,
                             freight_short_startable=0, available_cash=1_000), ())
        self.assertEqual(p.observe(1972, 12, mode_air=False,
                         mode_rail=False, freight_short_startable=0,
                         available_cash=1_000_000), ())
        self.assertEqual(p.freight.stage, -1)


if __name__ == "__main__":
    unittest.main()
