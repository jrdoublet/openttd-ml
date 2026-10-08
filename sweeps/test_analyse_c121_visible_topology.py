import unittest
from analyse_c121_visible_topology import decode, summarise

TRACE = """[0] [I] C121_VISIBLE_TOPOLOGY_INVALIDATE reason=age kept=1 entries=2
[0] [I] C121_VISIBLE_TOPOLOGY_INVALIDATE reason=station_lines kept=0 entries=2
[0] [I] C121_VISIBLE_TOPOLOGY_CASE case=1 station=5 old_hit=0 new_hit=1 tiles=20 original_ops=500 shadow_ops=30
[0] [I] C121_VISIBLE_TOPOLOGY_DEPTH extra=0 have=4 cap=4 fallback=1 equal=1
[0] [I] C121_VISIBLE_TOPOLOGY_DEPTH extra=1 have=5 cap=4 fallback=2 equal=1
"""


class TopologyTests(unittest.TestCase):
    def test_costs_and_physical_invalidation(self):
        result = summarise(*decode(TRACE))
        self.assertEqual(result["saved_ops"], 470)
        self.assertEqual(result["avoided_materialisations"], 1)
        self.assertEqual(result["kept_invalidations_with_nonempty_shadow"], 1)
        self.assertFalse(result["adoption"])

    def test_missing_or_wrong_depth_and_suppressed_physical_reset(self):
        for invalid in (TRACE.replace("fallback=2", "fallback=0"),
                        TRACE.replace("reason=station_lines kept=0", "reason=station_lines kept=1"),
                        TRACE.replace("original_ops=500", ""),
                        TRACE+TRACE, TRACE.replace("equal=1", "equal=0")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                decode(invalid)

    def test_scoped_station_revisions_keep_other_station_geometry(self):
        scoped = TRACE.replace("reason=station_lines kept=0", "reason=station_lines kept=1")
        self.assertEqual(summarise(*decode(scoped, scoped=True))["avoided_materialisations"], 1)
        with self.assertRaises(ValueError):
            decode(scoped.replace("reason=station_lines", "reason=site_reset"), scoped=True)


if __name__ == "__main__":
    unittest.main()
