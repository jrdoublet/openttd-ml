"""C117: ratios réseau calculés sur des fenêtres de support apparié."""

import math
import unittest

from sweeps.analyse_c117_aggregate import network_weighted


def window(pax, seats, base, shadow, pred, days=30.4):
    return {
        "pax": pax, "seat_legs": seats, "base_monthly": base,
        "shadow_monthly": shadow, "pred_carried": pred,
        "period_days": days,
    }


class NetworkWeightedContracts(unittest.TestCase):
    def test_missing_denominators_never_borrow_passengers(self):
        windows = [
            window(100, 200, 100, 100, 100),
            window(100, None, None, 0, None),
        ]
        got = network_weighted(windows)
        self.assertEqual(got["realized_base_ratio"], 1.0)
        self.assertEqual(got["realized_shadow_ratio"], 1.0)
        self.assertEqual(got["realized_pred_carried_ratio"], 1.0)
        self.assertEqual(got["load_factor"], 0.5)

    def test_each_denominator_has_its_own_observation_population(self):
        windows = [
            window(100, 200, 100, None, 100),
            window(60, 120, None, 60, None),
            window(0, 0, 50, 50, 50),
        ]
        got = network_weighted(windows)
        self.assertAlmostEqual(got["realized_base_ratio"], 100 / 150)
        self.assertAlmostEqual(got["realized_shadow_ratio"], 60 / 110)
        self.assertAlmostEqual(got["realized_pred_carried_ratio"], 100 / 150)
        self.assertAlmostEqual(got["load_factor"], 160 / 320)

    def test_nonfinite_invalid_and_missing_pax_do_not_contaminate_network(self):
        windows = [
            window(20, 40, 20, 20, 20),
            window(500, math.nan, math.inf, -100, math.nan),
            window(None, 200, 200, 200, 200),
            window(100, 200, 100, 100, 100, days=math.inf),
            window(100, 200, 100, 100, 100, days=-1),
            window(0, 0, 20, 20, 20),
        ]
        got = network_weighted(windows)
        for name in ("realized_base_ratio", "realized_shadow_ratio",
                     "realized_pred_carried_ratio"):
            self.assertEqual(got[name], 0.5)
        self.assertEqual(got["load_factor"], 0.5)

    def test_no_comparable_support_returns_missing_ratios(self):
        got = network_weighted([window(10, None, None, None, None)])
        self.assertTrue(all(value is None for value in got.values()))


if __name__ == "__main__":
    unittest.main()
