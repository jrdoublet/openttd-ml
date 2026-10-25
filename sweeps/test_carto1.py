"""Host-only CARTO-1 log-contract fixtures; never starts OpenTTD or Docker."""

from __future__ import annotations

import contextlib
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_carto1 as carto


def event(tag, fields="", day="1971-4-5"):
    return (
        f"[2026-10-24 13:54:33] dbg: [script:4] [0] [I] "
        f"OPEX {day} {tag} {fields}\n"
    )


def pair(key, cost, outcome, iters, *, cost_after_end=False):
    price = event(
        "CARTO1_COST",
        f"key={key} direct={cost // 2} route={cost} blocks=12 "
        "route_blocks=8 water=1 relief=2 town=3 valid=1",
    )
    search = [
        event("CARTO1_QUEUE", f"key={key} source=astar"),
        event("CARTO1_ASTAR", f"phase=start key={key}"),
        event("CARTO1_ASTAR",
              f"phase=end key={key} outcome={outcome} iters={iters} ops={iters * 12} ticks=7"),
    ]
    return search + [price] if cost_after_end else [price] + search


class CartoParserTests(unittest.TestCase):
    def test_async_cost_after_end_and_last_summary(self):
        key = "freight:COAL:101:202"
        raw = [
            event("CARTO1_START",
                  "mapx=128 mapy=128 side=8 total_blocks=256 pattern=full6 bit=25"),
            event("CARTO1_QUEUE", f"key={key} source=portfolio"),
            event("CARTO1_BLOCK",
                  "bx=4 by=5 id=645 cost=200 ops=350 ticks=1 water=3 relief=2 town=1"),
            event("CARTO1_BLOCK", "bx=4 by=5 id=645 ops=100 ticks=0 water=2 relief=1 town=0"),
            event("CARTO1_BLOCK", "bx=5 by=5 id=646 ops=200 ticks=2 water=0 relief=3 town=2"),
            event("CARTO1_ASTAR", f"phase=start key={key}"),
            event("CARTO1_ASTAR",
                  f"phase=end key={key} outcome=ABND iters=10000 ops=2700000 ticks=700"),
            event("CARTO1_SUMMARY",
                  "total_blocks=256 read=1 requests=2 costs=0 ops=600 ticks=3 overruns=0"),
            event("CARTO1_COST",
                  f"key={key} direct=80 route=150 blocks=25 route_blocks=18 "
                  "water=4 relief=7 town=2 valid=1"),
            event("CARTO1_SUMMARY",
                  "total_blocks=256 read=2 requests=2 costs=1 "
                  "ops=650 work_ops=2300 scans=4 ticks=5 overruns=0"),
        ]
        data, joined = carto.parse_lines(raw)
        self.assertEqual((data["seed"], data["repeat"], data["policy"]), (42, 0, "reference"))
        self.assertEqual(data["summary_count"], 2)
        self.assertEqual(data["last_summary"]["costs"], "1")
        self.assertEqual(data["carto_start"]["pattern"], "full6")
        self.assertEqual(data["summary_work"]["work_ops"], 2300)
        self.assertEqual(data["summary_work"]["scans"], 4)
        self.assertEqual(data["coverage"]["percent"], 0.781)
        self.assertEqual(data["coverage"]["observed_unique_blocks"], 2)
        self.assertEqual(data["blocks"]["events"], 3)
        self.assertEqual(data["blocks"]["ops"]["sum"], 650)
        self.assertEqual(data["blocks"]["ticks"]["sum"], 3)
        self.assertEqual(data["blocks"]["by_block"][0]["reads"], 2)
        self.assertEqual(data["queue_sources"], {"portfolio": 1})
        self.assertEqual(data["astar"]["outcomes"], {"ABND": 1})
        self.assertEqual(data["astar"]["unpaired_ends"], 0)
        self.assertEqual(data["joined"]["n"], 1)
        self.assertEqual(data["joined"]["by_outcome"]["ABND"]["iters"]["sum"], 10000)
        self.assertEqual(data["joined"]["by_outcome"]["ABND"]["route_per_block"]
                         ["median"], round(150 / 18, 6))
        self.assertEqual(data["blocks"]["by_block"][0]["cost"], 200)
        self.assertEqual(joined[0]["route"], 150)

    def test_cost_correlation_success_abandon_iterations(self):
        inputs = []
        inputs += pair("freight:COAL:1:11", 10, "OK", 100)
        inputs += pair("freight:COAL:2:12", 20, "ABND", 200, cost_after_end=True)
        inputs += pair("freight:COAL:3:13", 30, "DEAD", 300)
        data, joined = carto.parse_lines(inputs)
        self.assertEqual(data["joined"]["n"], 3)
        self.assertEqual(data["joined"]["correlations"]["route"]["iters"], {"n": 3, "r": 1.0})
        self.assertLess(data["joined"]["correlations"]["route"]["success"]["r"], 0)
        self.assertGreater(data["joined"]["correlations"]["route"]["abandoned"]["r"], 0)
        self.assertEqual(data["joined"]["by_outcome"]["OK"]["direct"]["median"], 5)
        self.assertEqual(data["joined"]["by_outcome"]["ABND"]["route"]["median"], 20)
        self.assertEqual(data["joined"]["by_outcome"]["DEAD"]["iters"]["median"], 300)
        self.assertEqual(len(joined), 3)

    def test_unpaired_invalid_and_duplicate_keys_do_not_invent_observations(self):
        repeat = "freight:WOOD:3:5"
        incomplete = "freight:WOOD:7:9"
        raw = [
            event("CARTO1_COST", f"key={incomplete} direct=-1 route=-1 valid=0"),
            event("CARTO1_ASTAR", f"phase=end key={incomplete} outcome=OK iters=10"),
        ]
        raw += pair(repeat, 20, "OK", 10)
        raw += pair(repeat, 30, "ABND", 100, cost_after_end=True)
        raw += [
            event("CARTO1_ASTAR", f"phase=start key={incomplete}"),
            event("CARTO1_BLOCK", "bx=-1 by=2 id=-1 ops=3 ticks=1"),
            event("CARTO1_BLOCK", "bx=4 by=2 ops=-1 ticks=-1"),
        ]
        result, joined = carto.parse_lines(raw)
        self.assertEqual(result["astar"]["unpaired_ends"], 1)
        self.assertEqual(result["astar"]["unpaired_starts"], 1)
        self.assertEqual(result["joined"]["repeated_keys"], [repeat])
        self.assertEqual(result["joined"]["n"], 1)
        self.assertEqual(result["joined"]["by_outcome"]["ABND"]["route"]["median"], 30)
        self.assertEqual(result["blocks"]["ops"]["n"], 0)
        self.assertEqual(result["blocks"]["unique"], 1)
        self.assertEqual(len(joined), 1)

    def test_real_rail_events_kept_separate_and_sentinels_excluded(self):
        raw = [
            event("RAIL_ATTEMPT",
                  "src=23 dst=42 kind=freight manh=98 ok=1 reason=- "
                  "iters=143 ops=350000 search_ops=300000 phases=10/40/30/20/10"),
            event("RAIL_ATTEMPT",
                  "src=25 dst=40 kind=pax manh=121 ok=0 reason=ABND "
                  "iters=10000 ops=900000 search_ops=-1"),
            event("RAIL_SEARCH", "type=resumable outcome=ABND iters=10000 budget=10000"),
            event("P5_RAIL_SEARCH",
                  "id=7 kind=primary src=25 dst=40 iters=10000 ops=2500000 "
                  "slices=200 ticks=700 outcome=ABND result=cap budget=10000"),
            event("C56_TASK RAIL_SEARCH_END",
                  "name=primary cycle=3 src=23 dst=42 outcome=OK result=found "
                  "iters=143 len=50 weight=120 budget=10000 days=2 ticks=100"),
        ]
        data, joined = carto.parse_lines(raw)
        rail = data["rail_diagnostics"]
        self.assertEqual(rail["RAIL_ATTEMPT"]["count"], 2)
        self.assertEqual(rail["RAIL_ATTEMPT"]["outcomes"], {"ABND": 1, "OK": 1})
        self.assertEqual(rail["RAIL_ATTEMPT"]["search_ops"]["n"], 1)
        self.assertEqual(rail["RAIL_ATTEMPT"]["search_ops"]["sum"], 300000)
        self.assertEqual(rail["RAIL_SEARCH"]["outcomes"], {"ABND": 1})
        self.assertEqual(rail["P5_RAIL_SEARCH"]["ticks"]["sum"], 700)
        self.assertEqual(rail["C56_RAIL_SEARCH_END"]["ticks"]["sum"], 100)
        self.assertEqual(data["joined"]["n"], 0)
        self.assertEqual(joined, [])

    def test_missing_summary_undefined_coverage_and_constant_cost_no_spurious_r(self):
        data, joined = carto.parse_lines(pair("freight:IRON:2:3", 20, "OK", 50))
        self.assertIsNone(data["last_summary"])
        self.assertIsNone(data["coverage"]["percent"])
        self.assertEqual(data["joined"]["correlations"]["route"]["success"],
                         {"n": 1, "r": None})
        self.assertEqual(joined[0]["iters"], 50)
        self.assertEqual(carto.correlation([{"x": 1, "y": 0},
                                            {"x": 1, "y": 1},
                                            {"x": 1, "y": 2}], "x", "y"),
                         {"n": 3, "r": None})

    def test_nopa_without_start_is_real_engine_outcome_and_skips_reported(self):
        key = "freight:4:12345:67890"
        data, joined = carto.parse_lines([
            event("CARTO1_START", "mapx=128 mapy=128 side=8 total_blocks=256"),
            event("CARTO1_QUEUE", f"key={key} source=astar steps=10 pending=1"),
            event("CARTO1_ASTAR", f"phase=end key={key} outcome=NOPA iters=0"),
            event("CARTO1_COST", f"key={key} src=12345 dst=67890 direct=1000 "
                  "route=240 blocks=12 route_blocks=3 water=0 relief=0 town=2 valid=1"),
            event("CARTO1_SKIP",
                  "key=freight:5:200:300 reason=corridor_too_large blocks=421"),
            event("CARTO1_BLOCK",
                  "id=1 bx=1 by=0 cost=100 water=0 town=0 relief=0 ops=1500 ticks=0"),
        ])
        self.assertEqual(data["astar"]["outcomes"], {"NOPA": 1})
        self.assertEqual(data["astar"]["unpaired_ends"], 0)
        self.assertEqual(data["skip_reasons"], {"corridor_too_large": 1})
        self.assertEqual(data["coverage"]["total_blocks"], 256)
        self.assertEqual(data["coverage"]["read_source"], "observed_blocks")
        self.assertEqual(data["coverage"]["read"], 1)
        self.assertEqual(data["joined"]["n"], 1)
        self.assertEqual(data["joined"]["by_outcome"]["NOPA"]["route_per_block"]
                         ["median"], 80)
        self.assertEqual(joined[0]["outcome"], "NOPA")

    def test_stock_astar_ok_end_without_start_has_queue_and_cost(self):
        key = "freight:1:19055:26996"
        data, joined = carto.parse_lines([
            event("CARTO1_QUEUE",
                  f"key={key} source=astar src=19055 dst=26996 steps=4 pending=1"),
            event("CARTO1_ASTAR",
                  f"phase=end key={key} outcome=OK iters=29 src=19055 dst=26996"),
            event("CARTO1_COST",
                  f"key={key} src=19055 dst=26996 direct=7570 route=1516 "
                  "blocks=23 route_blocks=5 water=0 town=104 relief=26 valid=1"),
            event("CARTO1_SUMMARY",
                  "total_blocks=1024 read=23 requests=1 costs=1 queued=0 active=0 "
                  "drops=0 ops=30000 work_ops=60000 ticks=0 overruns=0"),
        ])
        self.assertEqual(data["astar"]["starts"], 0)
        self.assertEqual(data["astar"]["ends_without_start_with_queue"], 1)
        self.assertEqual(data["joined"]["n"], 1)
        self.assertEqual(joined[0]["route_per_block"], 303.2)
        self.assertEqual(data["joined"]["by_outcome"]["OK"]["iters"]["median"], 29)
        self.assertIn("route_per_block", carto.render_markdown(carto.analyze_sources(
            [("reference_seed42_r0.log", [
                event("CARTO1_QUEUE", f"key={key} source=astar"),
                event("CARTO1_ASTAR", f"phase=end key={key} outcome=OK iters=29"),
                event("CARTO1_COST", f"key={key} direct=7570 route=1516 "
                      "blocks=23 route_blocks=5 water=0 town=104 relief=26 valid=1"),
            ])])))


class CartoCLITests(unittest.TestCase):
    def test_policy_seed_isolation_gzip_and_markdown_json_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            p1 = folder / "reference_seed42_r0.log"
            p2 = folder / "candidate_seed42_r0.log.gz"
            p3 = folder / "reference_seed100_r1.log"
            p1.write_text("".join(pair("freight:COAL:1:2", 40, "OK", 55)
                                  + [event("CARTO1_SUMMARY",
                                           "total_blocks=64 read=8 ops=10 work_ops=40 scans=2")]),
                          encoding="utf-8")
            with gzip.open(p2, "wt", encoding="utf-8") as stream:
                stream.write("".join(pair("freight:COAL:1:2", 50, "ABND", 200)))
            p3.write_text("".join(pair("freight:WOOD:3:4", 60, "OK", 90)),
                          encoding="utf-8")
            (folder / "noise.log").write_text(event("CARTO1_SUMMARY", "read=999"),
                                               encoding="utf-8")

            analysis = carto.analyze_paths([folder, p1])
            self.assertEqual(set(analysis["policies"]), {"candidate", "reference"})
            self.assertEqual(len(analysis["policies"]["reference"]["seeds"]), 2)
            self.assertEqual(analysis["policies"]["reference"]["pooled_joined"]["n"], 2)
            self.assertEqual(analysis["policies"]["candidate"]["pooled_joined"]["n"], 1)
            self.assertEqual(analysis["policies"]["candidate"]["seeds"][0]["astar"]
                             ["outcomes"], {"ABND": 1})
            markdown = carto.render_markdown(analysis)
            self.assertIn("Graine/rép.", markdown)
            self.assertIn("Coûts par issue", markdown)

            destination = folder / "summary.json"
            carto.main([str(folder), "--policy", "candidate", "--format", "json",
                        "--out", str(destination)])
            saved = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(set(saved["policies"]), {"candidate"})
            self.assertEqual(saved["policies"]["candidate"]["seeds"][0]["seed"], 42)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                carto.main([str(p1)])
            self.assertIn("reference", out.getvalue())

    def test_invalid_input_and_filename(self):
        with self.assertRaises(ValueError):
            carto.identity("unexpected.log")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "garbage.log").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Aucun journal"):
                carto.analyze_paths([tmp])


if __name__ == "__main__":
    unittest.main()
