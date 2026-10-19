"""19/10 : la note de gare se lit sur le bit Rating de GoodsEntry, pas sur Acceptance."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_1v1_5y_20seeds import _station_route_index  # noqa: E402


def _chunks(goods):
    return {"STNN": {"5": {"normal": [{"base": [{"town": 2, "owner": 0, "facilities": 1, "xy": 100}],
                                        "goods": goods}]}}}


class GoodsRatingBit(unittest.TestCase):
    def test_source_without_acceptance_is_rated(self):
        # Gare de mine : note (bit 1) sans acceptation (bit 0).
        goods = [{"status": 2, "rating": 180, "time_since_pickup": 3, "max_waiting_cargo": 40}]
        good = _station_route_index(_chunks(goods))[5]["goods"]["0"]
        self.assertTrue(good["rated"])
        self.assertFalse(good["accepts"])
        self.assertEqual(good["rating"], 180)

    def test_acceptance_alone_is_not_a_rating(self):
        # Gare de centrale : accepte (bit 0), jamais chargee : note par defaut non publiee.
        goods = [{"status": 1, "rating": 175, "time_since_pickup": 255, "max_waiting_cargo": 0},
                 {"status": 1, "rating": 175, "time_since_pickup": 4, "max_waiting_cargo": 0}]
        index = _station_route_index(_chunks(goods))[5]["goods"]
        for key in ("0", "1"):
            self.assertFalse(index[key]["rated"])
            self.assertTrue(index[key]["accepts"])
            self.assertIsNone(index[key]["rating"])


if __name__ == "__main__":
    unittest.main()
