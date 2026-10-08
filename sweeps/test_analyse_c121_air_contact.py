import unittest
from analyse_c121_air_contact import allocation_fraction, airport_rect, intersects, endpoints


class ContactTests(unittest.TestCase):
    def test_engine_company_then_station_share(self):
        self.assertAlmostEqual(allocation_fraction(0, 200, {0: [200]}), 201 / 256)
        self.assertAlmostEqual(allocation_fraction(0, 200, {0: [200], 1: [200]}), 201 / 512)
        # A second station of AAA changes its internal sharing, not its company best.
        self.assertAlmostEqual(allocation_fraction(0, 200, {0: [200], 1: [200, 200]}), 201 / 512)
        groups = {0: [100, 200], 1: [150, 50]}
        total = sum(allocation_fraction(o, r, groups) for o, ratings in groups.items() for r in ratings)
        self.assertAlmostEqual(total, 201 / 256)
        self.assertEqual(allocation_fraction(0, 0, {0: [0]}), 0)
        with self.assertRaises(ValueError):
            allocation_fraction(0, 200, {0: [100]})

    def test_rectangle_edges_no_tile_wrap(self):
        a = airport_rect({"tile": 0, "width": 2, "height": 2}, 4, 256, 256)
        self.assertEqual(a, (0, 0, 5, 5))
        self.assertTrue(intersects(a, (5, 5, 8, 8)))
        self.assertFalse(intersects(a, (6, 5, 8, 8)))
        self.assertIsNone(airport_rect({"tile": 255, "width": 2, "height": 2}, 4, 256, 256))

    def test_unrated_and_duplicate_routes_not_extra_stations(self):
        e = {"station_id": 3, "airport": {"tile": 10, "width": 4, "height": 3},
             "cargo": {"5": {"rated": True, "rating": 100}}}
        row = {"line_telemetry": {"ok": True, "lines": [
            {"mode": "air", "endpoint_cargo_stats": [e]},
            {"mode": "air", "endpoint_cargo_stats": [e]}]}}
        self.assertEqual(len(endpoints(row, 5)), 1)
        self.assertEqual(endpoints(row, 0), {})
        e["cargo"]["5"]["rated"] = False
        self.assertEqual(endpoints(row, 5), {})


if __name__ == "__main__":
    unittest.main()
