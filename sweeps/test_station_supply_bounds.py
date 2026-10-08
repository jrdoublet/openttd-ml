import copy
import unittest
from station_supply_bounds import bounded_intervals


def pair(a=101, b=70):
    node = {"station": 2, "cargo": 3, "graph": "0", "membership": [[2, 99]],
            "xy": 99, "build_date": 0, "compression": 0, "supply": a, "last_update": 250}
    old = {"ok": True, "economy_date": 250, "nodes": [node]}
    new = copy.deepcopy(old)
    new["economy_date"] = 280
    new["nodes"][0].update(compression=130, supply=b, last_update=280)
    return old, new


class CompressionBoundsTests(unittest.TestCase):
    def test_contains_every_possible_before_after_split(self):
        for a in (0, 1, 100, 101):
            for u in range(12):
                for v in range(12):
                    old, new = pair(a, (a+u)//2+v)
                    row = bounded_intervals(old, new)[0]
                    self.assertTrue(row["bounded"])
                    self.assertLessEqual(row["lower"], u+v)
                    self.assertGreaterEqual(row["upper"], u+v)
                    self.assertFalse(row["exact"])

    def test_reject_merge_ambiguous_age_and_invalid_date(self):
        for field, value in (("graph", "1"), ("membership", [[2, 99], [3, 88]]),
                             ("compression", 50), ("xy", 100)):
            old, new = pair()
            new["nodes"][0][field] = value
            self.assertFalse(bounded_intervals(old, new)[0]["bounded"])
        old, new = pair()
        old["nodes"][0]["compression"] = -300
        self.assertFalse(bounded_intervals(old, new)[0]["bounded"])
        old, new = pair()
        old["nodes"][0]["compression"] = -230
        new["nodes"][0]["compression"] = 14
        self.assertFalse(bounded_intervals(old, new)[0]["bounded"])

    def test_exact_remains_exact(self):
        old, new = pair(100, 120)
        new["nodes"][0]["compression"] = 0
        row = bounded_intervals(old, new)[0]
        self.assertTrue(row["exact"])
        self.assertEqual((row["lower"], row["upper"]), (20, 20))

    def test_surviving_growth_separate_and_exact_without_compression(self):
        old, new = pair(100, 120)
        new["nodes"][0].update(compression=0, membership=[[2, 99], [3, 88]])
        self.assertFalse(bounded_intervals(old, new)[0]["bounded"])
        row = bounded_intervals(old, new, surviving_growth=True)[0]
        self.assertTrue(row["exact"])
        self.assertEqual((row["lower"], row["upper"]), (20, 20))
        self.assertEqual(row["continuity"], "surviving_graph_growth")

    def test_growth_compression_bounded_but_transferred_or_removed_not(self):
        old, new = pair()
        new["nodes"][0]["membership"] = [[2, 99], [3, 88]]
        self.assertTrue(bounded_intervals(old, new, surviving_growth=True)[0]["bounded"])
        new["nodes"][0]["graph"] = "1"
        self.assertFalse(bounded_intervals(old, new, surviving_growth=True)[0]["bounded"])
        new["nodes"][0]["graph"] = "0"
        old["nodes"][0]["membership"] = [[2, 99], [4, 77]]
        self.assertFalse(bounded_intervals(old, new, surviving_growth=True)[0]["bounded"])
        old["nodes"][0]["membership"] = [[2, 98]]
        self.assertFalse(bounded_intervals(old, new, surviving_growth=True)[0]["bounded"])

    def test_growth_reset_and_stale_update_rejected(self):
        for supply, update in ((90, 280), (120, 249), (120, 250)):
            old, new = pair(100, supply)
            new["nodes"][0].update(compression=0, membership=[[2, 99], [3, 88]], last_update=update)
            self.assertFalse(bounded_intervals(old, new, surviving_growth=True)[0]["bounded"])


if __name__ == "__main__":
    unittest.main()
