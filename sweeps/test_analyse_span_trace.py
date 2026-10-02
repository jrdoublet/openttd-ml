"""Contrats de l'analyseur de spans dates, sur journaux synthetiques."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyse_span_trace import (
    analyse_records_by_seed,
    build_seed_report,
    category_of,
    days_between,
    parse_log_text,
    render_markdown,
    seed_from_path,
)


LOG = """\
[script:4] [0] [I] OPEX 1970-1-1 SPAN id=1 par=0 dep=0 n=loop.orch ds=1970-1-1 t0=10 tk=20 op=1000
[script:4] [0] [I] OPEX 1970-1-2 SPAN id=2 par=1 dep=1 n=task.air ds=1970-1-1 t0=12 tk=8 op=400
[script:4] [0] [I] OPEX 1970-1-2 SPAN_AGG par=2 n=air.pair cnt=4 tk=6 op=250
[script:4] [0] [I] OPEX 1970-1-2 EVT k=line_built t0=18 mode=air towns=1,2 capital=100 planes=1
[script:4] [0] [I] OPEX 1970-1-3 SPAN id=3 par=0 dep=0 n=loop.sleep ds=1970-1-3 t0=30 tk=4 op=50 orphan=1
[script:4] [0] [I] OPEX 1970-1-4 SPAN id=4 par=0 dep=0 n=projects.pass ds=1970-1-3 t0=40 tk=9 op=90
[script:4] [0] [I] OPEX 1970-1-5 EVT k=line_built t0=48 mode=air towns=3,4 capital=200 planes=1
[script:4] [1] [I] OPEX 1970-1-1 SPAN id=9 par=0 dep=0 n=task.air ds=1970-1-1 t0=1 tk=1 op=999
"""

OTHER = """\
[script:4] [0] [I] OPEX 1970-1-1 SPAN id=1 par=0 dep=0 n=task.air ds=1970-1-1 t0=1 tk=2 op=10
[script:4] [0] [I] OPEX 1970-1-1 SPAN_SELF lines=3 agg_lines=1
"""


class AnalyseSpanTraceTest(unittest.TestCase):
    def test_tree_aggregates_orphans_and_path(self):
        records = parse_log_text(LOG, company_filter=0)
        self.assertEqual([item["kind"] for item in records], [
            "SPAN", "SPAN", "SPAN_AGG", "EVT", "SPAN", "SPAN", "EVT",
        ])
        report = build_seed_report(records)
        self.assertEqual(report["span_count"], 4)
        self.assertEqual(report["agg_count"], 1)
        self.assertEqual(report["orphan_count"], 1)
        names = [node["name"] for node in report["chronology"]]
        self.assertEqual(names, ["loop.orch", "loop.sleep", "projects.pass"])
        air = report["chronology"][0]["children"][0]
        self.assertEqual(air["name"], "task.air")
        self.assertEqual(air["days"], 1)
        self.assertEqual(air["aggs"][0]["name"], "air.pair")
        self.assertEqual(air["aggs"][0]["count"], 4)
        self.assertTrue(report["chronology"][1]["orphan"])
        self.assertEqual(report["chronology"][1]["days"], 0)

        self.assertEqual(report["categories"]["passenger_air"], 400)
        self.assertEqual(report["categories"]["shared"], 1000 - 400 + 90)
        self.assertEqual(report["categories"]["accounting"], 50)
        self.assertNotIn("rail", [node["name"] for node in report["chronology"]])
        pie = sum(report["categories"].values())
        self.assertEqual(pie, 400 + 600 + 50 + 90)
        self.assertEqual(report["by_name"]["air.pair"]["opcodes"], 250)
        self.assertEqual(report["by_name"]["air.pair"]["count"], 4)

        self.assertEqual(len(report["paths"]), 1)
        top = report["paths"][0]["top"]
        self.assertEqual(report["paths"][0]["from_tick"], 18)
        self.assertEqual(report["paths"][0]["to_tick"], 48)
        by_name = {item["name"]: item["overlap_ticks"] for item in top}
        self.assertEqual(by_name["loop.orch"], 12)
        self.assertEqual(by_name["task.air"], 2)
        self.assertEqual(by_name["loop.sleep"], 4)
        self.assertEqual(by_name["projects.pass"], 8)
        self.assertLessEqual(len(top), 15)

    def test_company_filter_and_span_self(self):
        kept = parse_log_text(LOG, company_filter=0)
        self.assertTrue(all(item["company"] == 0 for item in kept))
        other = parse_log_text(OTHER, company_filter=0)
        report = build_seed_report(other)
        self.assertEqual(report["span_self"][0]["lines"], 3)
        self.assertEqual(report["span_self"][0]["agg_lines"], 1)
        self.assertEqual(category_of("air.pair"), "passenger_air")
        self.assertEqual(category_of("select.full"), "shared")
        self.assertEqual(category_of("loop.sleep"), "accounting")
        self.assertEqual(days_between((1970, 1, 1), (1970, 1, 1)), 0)
        self.assertEqual(days_between((1970, 1, 31), (1970, 2, 1)), 1)

    def test_mean_median_and_depth(self):
        first = parse_log_text(LOG, 0)
        second = parse_log_text(OTHER, 0)
        combined = analyse_records_by_seed({"42": first, "100": second})
        air = combined["across"]["by_name"]["task.air"]
        self.assertEqual(air["mean"]["opcodes"], (400 + 10) / 2)
        self.assertEqual(air["median"]["opcodes"], 205)
        text = render_markdown(combined, depth=0)
        self.assertIn("- loop.orch debut=", text)
        self.assertNotIn("  - task.air debut=", text)
        self.assertIn("- task.air debut=1970-1-1", text)
        self.assertEqual(seed_from_path("/tmp/OpexAI_c121_42.log"), "42")
        self.assertEqual(seed_from_path("/tmp/notes.log"), "notes")


if __name__ == "__main__":
    unittest.main()
