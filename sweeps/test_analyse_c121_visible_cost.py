import unittest
from analyse_c121_visible_cost import decode_cost


class CostTraceTests(unittest.TestCase):
    def test_reconciles_full_quotes_and_cached_calls(self):
        text = "[0] [I] C121_VISIBLE_COST_QUOTE line=2 ops=50000 ticks=5 vehicles=1\n"
        text += "[0] [I] C121_VISIBLE_COST_MONTH visible=1 month=23641 calls=4 quotes=1 quote_ops=50000 cached_ops=210 quote_ticks=5 cached_ticks=0\n"
        text += "[0] [I] C121_VISIBLE_COST_QUOTE line=2 ops=52000 ticks=6 vehicles=1\n"
        rows, pending = decode_cost(text)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(pending), 1)
        with self.assertRaises(ValueError):
            decode_cost(text.replace("quote_ops=50000", "quote_ops=0"))
        with self.assertRaises(ValueError):
            decode_cost(text.replace("quotes=1", "quotes=0"))

    def test_off_noop_and_duplicate_period(self):
        text = "[0] [I] C121_VISIBLE_COST_MONTH visible=0 month=23641 calls=3 quotes=0 quote_ops=0 cached_ops=40 quote_ticks=0 cached_ticks=0\n"
        rows, pending = decode_cost(text)
        self.assertEqual(rows[0]["quotes"], 0)
        self.assertEqual(pending, [])
        with self.assertRaises(ValueError):
            decode_cost(text+text)


if __name__ == "__main__":
    unittest.main()
