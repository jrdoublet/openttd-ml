"""Protect semantic distinctions in the per-pass diagnostic decoder."""
import unittest

from analyse_p0_funnel_reasons_20261012 import parse


class P0FunnelReasonTests(unittest.TestCase):
    def test_per_pass_not_per_month_and_unique_keys(self):
        events = [
            "[I] OPEX 1973-7-13 MONTHLY_FUNNEL considered=12 accepted=2 funded=1 attempted=1 built=0 r_batch_plan_dead=2",
            "[I] OPEX 1973-7-14 MONTHLY_FUNNEL considered=12 accepted=2 funded=1 attempted=1 built=1 r_batch_plan_dead=1",
            "[I] OPEX 1973-7-13 PROJECT_DISCARD mode=air src=15 dst=16 reason=batch_plan_dead",
            "[I] OPEX 1973-7-14 PROJECT_DISCARD mode=air src=15 dst=16 reason=batch_plan_dead",
            "[I] OPEX 1973-7-14 P5_BUILD_LINE mode=rail src=22 dst=33",
            "[I] OPEX 1973-7-14 P2_PASS in_best=0 n_built=1",
        ]
        d = parse(events)["1973"]
        self.assertEqual(2, d["funnel"]["events"])
        self.assertEqual(24, d["funnel"]["considered"])
        self.assertEqual(3, d["funnel_reason"]["batch_plan_dead"])
        self.assertEqual(2, d["discards"]["air/batch_plan_dead"])
        self.assertEqual(1, d["discard_unique_OD_month"]["air/batch_plan_dead"])
        self.assertEqual(1, d["builds"]["rail"])
        self.assertEqual(1, d["p2"]["initially_empty"])

    def test_fallback_and_modes_do_not_conflate(self):
        d = parse(["[I] OPEX 1972-5-6 FREIGHT_CARGO_FALLBACK from=0 to=2 tried=2 candidates=10",
                   "[I] OPEX 1972-5-6 P5_BUILD_LINE mode=road",
                   "[I] OPEX 1972-5-6 PROJECT_CHOSEN mode=air"])["1972"]
        self.assertEqual({"0->2": 1}, d["fallback"])
        self.assertEqual({"road": 1}, d["builds"])
        self.assertEqual({"air": 1}, d["chosen"])

    def test_empty_or_garbled_log_no_spurious_entries(self):
        self.assertEqual({}, parse(["OPEX NOAI ERROR", "unknown 1973-1-1"] ))


if __name__ == "__main__":
    unittest.main()
