import unittest
from analyse_c121_visible_fused import decode, summarise


class FusedBodyTests(unittest.TestCase):
    def test_input_and_date_equality_required_for_gain(self):
        text = "[0] [I] C121_VISIBLE_FUSED_CASE case=1 stable=1 input_equal=1 equal=1 original_ops=500 candidate_ops=400 samples=0\n"
        text += "[0] [I] C121_VISIBLE_FUSED_CASE case=2 stable=1 input_equal=0 equal=0 original_ops=5000 candidate_ops=100 samples=0\n"
        text += "[0] [I] C121_VISIBLE_FUSED_CASE case=3 stable=0 input_equal=1 equal=1 original_ops=5000 candidate_ops=100 samples=0\n"
        result = summarise(decode(text))
        self.assertEqual(result["saved_pct"], 20)
        self.assertEqual(result["matched_cases"], 1)
        self.assertEqual(result["stable_date_changed_inputs"], 1)
        self.assertEqual(result["date_crossing_cases"], 1)

    def test_missing_match_field_or_unequal_matched_outputs_rejected(self):
        text = "[0] [I] C121_VISIBLE_FUSED_CASE case=1 stable=1 input_equal=1 equal=1 original_ops=500 candidate_ops=400 samples=1\n"
        for bad in (text+text, text.replace("input_equal=1", ""), text.replace("equal=1 original", "equal=0 original")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                decode(bad)


if __name__ == "__main__":
    unittest.main()
