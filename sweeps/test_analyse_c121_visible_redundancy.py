import unittest
from analyse_c121_visible_redundancy import decode, summarise


class RedundancyTests(unittest.TestCase):
    def test_only_temporally_matched_cases_measure_gain(self):
        trace = "[0] [I] C121_VISIBLE_REDUNDANCY_CASE case=1 stable=1 equal=1 reason=hit_epoch have=2 cap=4 fallback=0 target_ops=100 before_ops=30 after_ops=40 fused_ops=110\n"
        trace += "[0] [I] C121_VISIBLE_REDUNDANCY_CASE case=2 stable=0 equal=0 reason=hit_age_epoch have=4 cap=4 fallback=1 target_ops=1000 before_ops=300 after_ops=400 fused_ops=50\n"
        result = summarise(decode(trace))
        self.assertEqual(result["saved_ops"], 60)
        self.assertEqual(result["matched_cases"], 1)
        self.assertEqual(result["date_crossing_cases"], 1)
        self.assertEqual(result["rebuild_reasons_all_cases"]["hit_epoch"], 1)
        self.assertFalse(result["adoption"])

    def test_missing_duplicate_or_unequal_outputs_rejected(self):
        trace = "[0] [I] C121_VISIBLE_REDUNDANCY_CASE case=1 stable=1 equal=1 reason=cold have=1 cap=4 fallback=0 target_ops=100 before_ops=30 after_ops=40 fused_ops=110\n"
        for invalid in (trace+trace, trace.replace("equal=1", "equal=0"),
                        trace.replace("after_ops=40", ""), trace.replace("fallback=0", "fallback=3")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                decode(invalid)


if __name__ == "__main__":
    unittest.main()
