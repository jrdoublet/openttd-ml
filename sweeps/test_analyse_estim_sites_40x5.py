"""Regression checks for ESTIM/sites economic and diagnostic log postprocessing."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


SRC = Path(__file__).with_name("analyse_estim_sites_40x5.py")
SPEC = importlib.util.spec_from_file_location("analyse_estim_sites_40x5", SRC)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def event(ymd, tag, attrs):
    return f"[date] dbg: [script:4] [0] [I] OPEX {ymd} {tag} {attrs}\n"


class DiagnosticsTest(unittest.TestCase):
    def test_span_exclusive_no_double_count_and_nonconstruction(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fake_seed42_r0.log"
            path.write_text("".join([
                event("1970-1-2", "SPAN", "id=2 par=1 dep=1 n=catalog.refresh op=40 tk=1"),
                event("1970-1-2", "SPAN", "id=1 par=0 dep=0 n=loop.orch op=100 tk=2"),
                event("1970-1-3", "V309_IDLE", "loops=10 useless=1 useless_ops=20 "
                      "sleep_ops=5 blocks=1 cash_below=6 cash_below_days=3 "
                      "stable_unfunded_loops=4 stable_unfunded_ops=88"),
                event("1970-1-3", "C63_INVEST", "phase=empty_probe cause=all_unaffordable"),
                event("1970-1-4", "C69_BOTTLENECK", "phase=c75_pass stop=cash built=0"),
                event("1971-1-2", "C69_BOTTLENECK", "phase=vivier_year year=1970 "
                      "mode=road examined=30 rej_origin_served=20 produced=0 after_topk=0 "
                      "to_select=3 affordable=2 selected=1"),
                event("1973-1-4", "ESTIM_SPEND", "mode=rail actual_paid=-1 ok=0"),
                event("1973-1-5", "ESTIM_SPEND", "mode=air actual_paid=123 ok=1"),
                event("1973-1-5", "AIR_BUILD", "line=9 cost=180 planes=1 arm=newpair"),
                event("1973-1-5", "AIR_FLEET", "action=refuse line=9 reason=O planes=1"),
                event("1973-1-6", "AIR_FLEET", "action=grow line=9 added=2"),
                event("1973-1-6", "ESTIM_OUTCOME", "mode=air outcome=built reason=ok"),
                event("1973-1-7", "ESTIM_PASS", "top_k=10"),
            ]), encoding="utf-8")
            data = MODULE.read_log(path)
        self.assertEqual(data["root_op_by_year"][1970], 100)
        self.assertEqual(data["ops_by_name"]["loop.orch"], 60)
        self.assertEqual(data["ops_by_name"]["catalog.refresh"], 40)
        self.assertEqual(data["empty"][(1970, "all_unaffordable")], 1)
        self.assertEqual(data["stops"][(1970, "cash")], 1)
        self.assertEqual(data["v309"][1970]["cash_below"], 6)
        self.assertEqual(data["vivier_counts"][(1970, "road", "examined")], 30)
        self.assertEqual(data["vivier_counts"][(1970, "road", "rej_origin_served")], 20)
        self.assertEqual(data["vivier_records"][(1970, "road")], 1)
        self.assertEqual(data["payments"][(1973, "air")], 123)
        self.assertEqual(data["spend_na"], 1)
        self.assertEqual(len(data["topk_months"]), 1)
        self.assertEqual(data["air_build_quote"][1973], 180)
        self.assertEqual(data["air_fleet_decisions"][(1973, "refuse", "O")], 1)
        self.assertEqual(data["air_fleet_added"][1973], 2)

    def test_unknown_vs_zero_paid(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fake_seed5_r0.log"
            path.write_text(
                event("1973-2-1", "ESTIM_SPEND", "mode=rail actual_paid=0") +
                event("1973-2-2", "ESTIM_SPEND", "mode=rail actual_paid=-1") +
                event("1973-2-3", "ESTIM_SPEND", "mode=rail actual_paid=none"),
                encoding="utf-8")
            data = MODULE.read_log(path)
        self.assertEqual(data["payments_count"][(1973, "rail")], 1)
        self.assertEqual(data["payments"][(1973, "rail")], 0)
        self.assertEqual(data["spend_na"], 2)

    def test_category_and_stats(self):
        self.assertEqual(MODULE.span_category("build.air.airport_a"), "construction")
        self.assertEqual(MODULE.span_category("astar.build"), "rail_astar")
        self.assertEqual(MODULE.stat([0, None, 20])["mean"], 10)
        self.assertEqual(MODULE.stat([None])["mean"], None)


if __name__ == "__main__":
    unittest.main()
