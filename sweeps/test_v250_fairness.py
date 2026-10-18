"""V250 : garde d'equite sur le profit des rivaux (v250_rival_profit_pct)."""
import re
import unittest
from pathlib import Path

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class V250FairnessTest(unittest.TestCase):
    def setUp(self):
        self.task = (AI / "task_v250.nut").read_text()
        self.info = (AI / "info.nut").read_text()

    def test_threshold_is_80(self):
        glob = (AI / "globals_pre.nut").read_text()
        self.assertIn("V250_RIVAL_PROFIT_PCT <- 80;", glob)
        self.assertNotIn("v250_rival_profit_pct", self.info)

    def test_gate_before_any_purchase(self):
        body = self.task[self.task.index("function OpexAI::_dispatchV250Rights"):]
        body = body[:body.index("\n}\n")]
        gate = body.index("OpexV250RivalEarnsEnough()")
        self.assertLess(gate, body.index("OpexV250RunTest"))
        self.assertLess(gate, body.index("OpexV250RunNormal"))
        self.assertLess(body.index("this._v250Month = ym"), gate)

    def test_integer_comparison_and_zero_disables(self):
        fn = self.task[self.task.index("function OpexV250RivalEarnsEnough"):]
        fn = fn[:fn.index("\n}\n")]
        self.assertIn("if (V250_RIVAL_PROFIT_PCT <= 0) return true;", fn)
        self.assertIn("best * 100 >= V250_RIVAL_PROFIT_PCT * mine", fn)
        self.assertIn("if (quarters <= 0) return false;", fn)


if __name__ == "__main__":
    unittest.main()
