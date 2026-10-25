"""No-engine tests for GOOD line capacity snapshots and V284 correlation."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from analyse_good_capacity_offline import read_logs, summarize


class GoodCapacityOfflineTest(unittest.TestCase):
    def test_positive_saturated_line_and_repeated_v284_events(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "reference_seed42_r0.log"
            path.write_text("\n".join([
                "OPEX 1978-1-5 V284 action=skip line=5 reason=geometry waiting=250",
                "OPEX 1979-1-1 V284 action=pick line=5 kind=wagon waiting=150 capacity=50",
                "OPEX 1979-1-2 V284 action=done line=5 kind=wagon capacity=75",
                "OPEX 1979-1-7 LINE_REVENUE line=5 mode=rail kind=freight cargo=GOOD "
                "year=1979 age=4 wait_a=175 cap=50 real_prof=32000 vehs=1 src_prod=80",
                "OPEX 1979-1-7 LINE_REVENUE line=6 mode=rail kind=freight cargo=COAL "
                "year=1979 age=7 wait_a=10000 cap=20 real_prof=99999 vehs=1 src_prod=900",
            ]), encoding="utf-8")
            records, actions = read_logs([path])
            result = summarize(records, actions)
            o = result["overview"]
            self.assertEqual(o["mature_lines"], 1)
            self.assertEqual(o["real_profit_sum"], 32000)
            self.assertEqual(o["wait_ge_3_capacity"], 1)
            self.assertEqual(o["v284_skip_geometry"], 1)
            self.assertEqual(o["v284_pick_wagon"], 1)
            self.assertEqual(o["v284_done_wagon"], 1)

    def test_snapshot_filters_immature_and_unknown_wait(self):
        rows = [
            {"file":"seed1.log", "line":1, "year":1979, "age":1,
             "cap":50, "wait_a":500, "real_prof":700, "src_prod":20, "vehs":1},
            {"file":"seed1.log", "line":2, "year":1979, "age":3,
             "cap":50, "wait_a":-1, "real_prof":500, "src_prod":20, "vehs":1},
            {"file":"seed1.log", "line":3, "year":1979, "age":3,
             "cap":100, "wait_a":300, "real_prof":-22, "src_prod":600, "vehs":1},
        ]
        overview = summarize(rows, {}, 1979)["overview"]
        self.assertEqual(overview["mature_lines"], 1)
        self.assertEqual(overview["wait_ge_3_capacity"], 1)
        self.assertEqual(overview.get("profit_positive_wait_ge_capacity", 0), 0)
        self.assertEqual(overview["real_profit_sum"], -22)


if __name__ == "__main__":
    unittest.main()
