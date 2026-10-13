"""Synthetic logs for causal joins; never treat an unrelated build as a flip."""
import tempfile
import unittest
from pathlib import Path
from analyse_scores_p4_chain_20261013 import analyse_one

PFX = "[2026-10-13 13:00:00] dbg: [script:4] [0] [I] "
H = ("P4_FLIP_HEAD id=1 year=1972 month=5 tier=0 "
     "legacy=rail/pax/0/1/2 stable=air/pax/0/3/4")
A = "P4_FLIP_ATTEMPT id=1 year=1972 rank=0 project=air/pax/0/3/4"


def fixture(*events):
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "p4_chain_test.log"
        path.write_text("".join(PFX + event + "\n" for event in events), encoding="utf8")
        return analyse_one(path)


class ChainLogTests(unittest.TestCase):
    def test_air_build_matched_by_id_and_before_outcome(self):
        result = fixture(H, A, "OPEX 1972-5-15 PROJECT_CHOSEN mode=air src=3 dst=4",
                         "OPEX 1972-5-15 AIR_BUILD line=7 src=3 dst=4",
                         "P4_FLIP_OUTCOME id=1 outcome=built new_line=7 line_delta=1",
                         "OPEX 1974-1-01 LINE_REVENUE line=7 age=2 real_prof=200 pred_prof=300")
        ep = result["episodes"][0]
        self.assertTrue(ep["direct_builder_confirmed"])
        self.assertEqual(ep["new_line"], 7)
        self.assertEqual(len(ep["revenue"]), 1)
        self.assertFalse(result["issues"])

    def test_builder_id_mismatch_fails_closed(self):
        result = fixture(H, A, "OPEX 1972-5-15 AIR_BUILD line=6",
                         "P4_FLIP_OUTCOME id=1 outcome=built new_line=7 line_delta=1")
        self.assertFalse(result["episodes"][0]["direct_builder_confirmed"])
        self.assertTrue(any("builder result built" in e for e in result["issues"]))

    def test_pending_not_built_until_reconciled_rail_resume(self):
        result = fixture(H, "P4_FLIP_ATTEMPT id=1 year=1972 rank=0 project=rail/pax/0/1/2",
                         "P4_FLIP_OUTCOME id=1 outcome=pending new_line=-1 line_delta=0",
                         "OPEX 1972-6-01 RAIL_BUILD line=11",
                         "P4_FLIP_RESUME id=1 year=1972 outcome=built new_line=11")
        ep = result["episodes"][0]
        self.assertTrue(ep["direct_builder_confirmed"])
        self.assertEqual(ep["new_line"], 11)
        self.assertEqual(ep["resumable"], ["built"])
        self.assertFalse(result["issues"])

    def test_head_without_constructor_is_not_a_build(self):
        result = fixture(H)
        self.assertEqual(result["counts"]["heads"], 1)
        self.assertEqual(result["counts"]["attempts"], 0)
        self.assertEqual(result["counts"]["confirmed_completed_builds"], 0)


if __name__ == "__main__":
    unittest.main()
