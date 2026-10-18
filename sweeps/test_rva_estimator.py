import unittest
from rva_demand import station_allocation, local_demand


class Allocation(unittest.TestCase):
    def st(self, sid, owner, rating):
        return dict(station=sid, owner=owner, rating_raw=rating)

    def test_engine_company_then_station_rule(self):
        result = station_allocation(256, [self.st('a', 0, 100), self.st('b', 0, 50), self.st('c', 1, 75)])
        self.assertAlmostEqual(sum(result.values()), 101)
        self.assertAlmostEqual(result['a'] / result['b'], 2)
        self.assertAlmostEqual((result['a'] + result['b']) / result['c'], 100/75)

    def test_no_rival_constant_and_zero_rating(self):
        self.assertIsNone(station_allocation(10, [self.st('x', 1, None)]))
        self.assertEqual(station_allocation(10, [self.st('x', 1, 0)]), {'x': 0})

    def test_real_coverage_partial_overlap_and_no_double_charge(self):
        st = self.st('new', 0, 100)
        result = local_demand(256, {1: 1, 2: 1}, [1], {1: [self.st('old', 0, 100)]}, st)
        self.assertEqual(result['line_month'], 101/4)
        self.assertEqual(result['own_delta_month'], 0)
        self.assertEqual(result['station_delta_month']['old'], -101/4)
        free = local_demand(256, {1: 1, 2: 1}, [2], {2: []}, st)
        self.assertEqual(free['line_month'], 101/2)

    def test_unknown_and_separate_cargo_inventory(self):
        self.assertIsNone(local_demand(None, {1: 1}, [1], {1: []}, self.st('x',0,100))['line_month'])
        self.assertIsNone(local_demand(0, {}, [], {}, self.st('x',0,100))['line_month'])
        self.assertEqual(local_demand(0, {1: 1}, [1], {1: []}, self.st('x',0,100))['line_month'], 0)


if __name__ == '__main__':
    unittest.main()
