"""RVA-08 contracts, synthetic geometry and volumes, no engine evidence."""
import unittest
from rva_demand import catchment, endpoint, endpoints


class Demand(unittest.TestCase):
    def producer(self, identity, tiles, pax=12, mail=3):
        return {"producer_id": identity, "tiles": tiles, "cargos": {
            "pax": {"monthly": pax, "source": "fixture_production"},
            "mail": {"monthly": mail, "source": "fixture_production"}}}

    def compute(self, tiles, producers, cargo="pax", services=(), complete=True):
        return endpoint(tiles, producers, cargo, inventory_complete=complete, services=services)

    def test_real_tiles_union_clipping_and_gap_is_not_station_rectangle(self):
        actual = catchment([(1, 1, 1), (8, 1, 1), (1, 1, 1)], 10, 6)
        self.assertEqual(len(actual), 18)
        self.assertNotIn((4, 1), actual)
        self.assertEqual(catchment([(0, 0, 1)], 10, 6), {(0, 0), (0, 1), (1, 0), (1, 1)})
        with self.assertRaises(ValueError):
            catchment([(1, 1, None)], 10, 6)

    def test_no_overlap_separate_directions_and_separate_cargos(self):
        producers = [self.producer("house-a", [(1, 1)]), self.producer("house-b", [(8, 1)], 24, 6)]
        a = self.compute({(1, 1)}, producers)
        b = self.compute({(8, 1)}, producers)
        pair = endpoints(a, b)
        self.assertEqual(pair["production_total_month"], 36)
        self.assertEqual((pair["a"]["production_month"], pair["b"]["production_month"]), (12, 24))
        self.assertEqual(self.compute({(1, 1)}, producers, "mail")["production_month"], 3)
        self.assertIsNone(pair["line_demand_month"])
        with self.assertRaises(ValueError):
            endpoints(a, self.compute({(8, 1)}, producers, "mail"))

    def test_partial_overlap_and_saturation_do_not_subtract_demand(self):
        producers = [self.producer("a", [(1, 1), (2, 1)]), self.producer("b", [(3, 1)])]
        services = [{"service_id": "airport", "cargo": "pax", "coverage_tiles": {(1, 1)},
                     "capacity_month": 100, "carried_month": 100}]
        result = self.compute({(1, 1), (2, 1), (3, 1)}, producers, services=services)
        self.assertEqual(result["producer_count"], 2)
        self.assertEqual(result["production_month"], 24)
        overlap, = result["own_services"]
        self.assertEqual(overlap["producer_ids"], ["a"])
        self.assertEqual(overlap["spare_capacity_month"], 0)
        self.assertIsNone(overlap["displaced_month"])
        self.assertIsNone(result["company_increment_month"])

    def test_unknown_zero_incomplete_and_duplicate_producer(self):
        producers = [self.producer("a", [(1, 1)], None, 0)]
        result = self.compute({(1, 1)}, producers)
        self.assertIsNone(result["production_month"])
        self.assertEqual(result["missing_volume_ids"], ["a"])
        self.assertEqual(self.compute({(1, 1)}, producers, "mail")["production_month"], 0)
        self.assertIsNone(self.compute({(1, 1)}, producers, "mail", complete=False)["producer_count"])
        with self.assertRaises(ValueError):
            self.compute({(1, 1)}, producers + producers)
        for invalid in (float("nan"), float("inf"), -1, True):
            self.assertIsNone(self.compute({(1, 1)}, [self.producer("a", [(1, 1)], invalid)])["production_month"])

    def test_shared_producer_not_counted_twice_as_independent_demand(self):
        producers = [self.producer("industry", [(1, 1), (8, 1)])]
        pair = endpoints(self.compute({(1, 1)}, producers), self.compute({(8, 1)}, producers))
        self.assertEqual(pair["shared_producer_ids"], ["industry"])
        self.assertIsNone(pair["production_total_month"])
