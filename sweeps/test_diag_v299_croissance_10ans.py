"""Classification contracts for the V299 descriptive rail-cargo groups."""

import unittest

from sweeps.diag_v299_croissance_10ans import cargo_key, snapshot_metrics


def rail(cargos, end=200, profit=1000):
    return {
        "mode": "rail", "vehicles": 1, "profit_last_year_gbp": profit,
        "ordered_station_tiles": [0, end], "capacity_by_cargo": cargos,
    }


class LongFreightWithoutGoodsTests(unittest.TestCase):
    def classify(self, *lines):
        return snapshot_metrics({"ok": True, "lines": list(lines)}, 256)

    def test_pure_good_is_excluded_from_non_good_freight(self):
        report = self.classify(rail({"5": 50}))
        self.assertEqual(report["freight_long_gt160"]["lines"], 1)
        self.assertEqual(report["freight_long_non_good"]["lines"], 0)

    def test_good_mixed_with_mail_and_pass_is_also_excluded(self):
        mixed = rail({"5": 40, "0": 100, "2": 25})
        self.assertEqual(cargo_key(mixed), "GOOD+MAIL+PASS")
        report = self.classify(mixed)
        self.assertEqual(report["freight_long_gt160"]["lines"], 1)
        self.assertEqual(report["freight_long_non_good"]["lines"], 0)
        self.assertEqual(report["freight_long_non_good"]["profit_gbp"], 0)

    def test_coal_or_zero_good_capacity_remains_non_good(self):
        report = self.classify(rail({"1": 30, "2": 10}), rail({5: 0, 1: 20}, profit=500))
        self.assertEqual(report["freight_long_non_good"]["lines"], 2)
        self.assertEqual(report["freight_long_non_good"]["profit_gbp"], 1500)

    def test_short_good_mix_is_not_long_freight(self):
        report = self.classify(rail({5: 20, 0: 40}, end=40))
        self.assertEqual(report["freight_long_gt160"]["lines"], 0)
        self.assertEqual(report["freight_long_non_good"]["lines"], 0)


if __name__ == "__main__":
    unittest.main()
