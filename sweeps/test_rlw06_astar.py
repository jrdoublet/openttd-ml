"""RLW-06 shadow source contracts and engine-log analyser fixtures."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import re
import tempfile
import unittest

try:
    from sweeps import analyze_rlw06
except ImportError:
    import analyze_rlw06


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class RLW06RuntimeContracts(unittest.TestCase):
    def test_bit25_and_default_off_with_shadow_04b_dependency(self):
        self.assertIn("RLW06_SHADOW <- false;", read("globals_pre.nut"))
        self.assertIn("const RLW06_PROBE_BIT = 33554432;", read("rail_long_window_astar.nut"))
        settings = read("settings.nut")
        self.assertIn("RLW06_SHADOW = OpexProbeEnabled(33554432);", settings)
        self.assertIn(
            "RLW04B_SHADOW = OpexProbeEnabled(16777216) || RLW06_SHADOW;",
            settings,
        )
        self.assertIn("OPEX_PROBE_MASK <- 2;", read("globals_pre.nut"))
        self.assertEqual(2 & 33554432, 0)
        info = read("info.nut")
        self.assertEqual(info.count('name = "probes"'), 1)
        self.assertNotIn('name = "rlw06', info)

    def test_both_loops_and_module_order(self):
        main = read("main.nut")
        probes = read("probes.nut")
        self.assertIn('require("rail_long_window_enumerator.nut");', main)
        self.assertIn('require("rail_long_window_astar.nut");', main)
        self.assertLess(main.index('require("rail_long_window_enumerator.nut");'),
                        main.index('require("rail_long_window_astar.nut");'))
        for source in (main, probes):
            rail = source.index("this._advanceRailSearchThroughput();")
            scan = source.index("if (RLW04B_SHADOW) this._rlw04bAnd06Step();", rail)
            astar = scan
            self.assertLess(rail, scan)
            self.assertEqual(scan, astar)
        self.assertIn("function _rlw06Step();", main)
        self.assertIn("function OpexAI::_rlw06Step()", read("rail_long_window_astar.nut"))
        shadow = read("rail_long_window_astar.nut")
        self.assertIn("function OpexAI::_rlw04bAnd06Step()", shadow)
        self.assertLess(shadow.index("this._rlw04bStep();"), shadow.index("if (RLW06_SHADOW) this._rlw06Step();"))

    def test_priority_and_opcode_gates_on_each_slice(self):
        code = read("rail_long_window_astar.nut")
        self.assertIn("!RLW06_SHADOW || !MODE_RAIL", code)
        self.assertIn("this._rlw04bState.sources < 64", code)
        for prerequisite in (
            "this._activeWorker != null", "this._railSearch != null",
            "this._hasReactiveIntentions()", "this._po01cJob != null",
            "this._po01cPending", "this._projects == null",
            "this._projects.best == null",
            "this._c121RailPrepAirFundableCheap()",
            "AIController.GetOpsTillSuspend() < RLW06_MIN_LEFT",
            "job.phase == \"search\" ? RLW06_SEARCH_LEFT : RLW06_MIN_LEFT",
            "AIController.GetOpsTillSuspend() < required",
        ):
            with self.subTest(gate=prerequisite):
                self.assertIn(prerequisite, code)
        # Les autres tâches ont eu leur tranche de l'orchestrateur; les
        # recherches/projets actifs et AIR finançable restent préemptifs.
        self.assertLess(code.index("this._c121RailPrepAirFundableCheap()"),
                        code.index("if (this._rlw06Job == null)"))
        self.assertLess(code.index("AIController.GetOpsTillSuspend() < required"),
                        code.index("local mark = OpexOpsMeasureBegin();"))
        self.assertIn("OpexAdvanceSegmentedSearch(", code)
        self.assertIn("OpexAdvanceRailPathfinder(", code)
        self.assertIn("RLW06_SLICE_ITERS", code)

    def test_private_shadow_state_bounded_reuse_and_expiry(self):
        main = read("main.nut")
        enum = read("rail_long_window_enumerator.nut")
        astar = read("rail_long_window_astar.nut")
        for token in ("_rlw06Job = null;", "_rlw06Ready = null;",
                      "_rlw06Seen = null;", "_rlw06Cursor = 0;",
                      "_rlw06Stats = null;", "this._rlw06Ready = {};",
                      "this._rlw06Seen = {};"):
            self.assertIn(token, main)
        self.assertNotIn("_rlw06", read("persist.nut").lower())
        self.assertIn("const RLW06_BEST_CAP = 24;", enum)
        self.assertIn("s.best.len() > RLW06_BEST_CAP", enum)
        self.assertIn("if (RLW06_SHADOW && production > 0", enum)
        for token in (
            "this._rlw04bState.best", "if (this._rlw06Job == null)",
            "key in this._rlw06Seen || key in this._rlw06Ready",
            "this._rlw06Ready[job.key] <-",
            "today + RLW06_TTL_DAYS",
            "if (today > entry.expiry)",
            'OpexRLW06Event("REUSE"', 'OpexRLW06Event("READY"',
            'OpexRLW06Event("PAIR"', 'OpexRLW06Event("ASTAR"',
            'OpexRLW06Event("SUMMARY"',
            "stats.ops += spentOps;", "stats.ticks += crossed;",
            "stats.initOps += spentOps;", "stats.searchOps += spentOps;",
        ):
            with self.subTest(token=token):
                self.assertIn(token, astar)
        # A shadow cache must never be handed to the ordinary rail stock.
        self.assertNotRegex(astar, r"(?:this\.)?_railReadyStock\s*(?:<-|=(?!=)|\[)")
        self.assertNotRegex(astar, r"(?:this\.)?_projects\s*(?:<-|=(?!=)|\[)")

    def test_station_construction_only_inside_test_mode(self):
        code = read("rail_long_window_astar.nut")
        self.assertNotRegex(
            code,
            r"\b(?:AIRail|AIRoad|AIAirport|AIVehicle)\."
            r"(?:BuildRail|BuildVehicle|BuildRoad|BuildAirport|BuildRailTrack|"
            r"BuildRoadStation|BuildRailDepot)\s*\(",
        )
        # The sole station build call is enclosed in an AITestMode lexical scope.
        calls = list(re.finditer(r"\bAIRail\.BuildRailStation\s*\(", code))
        self.assertEqual(len(calls), 1)
        start = code.rfind("{", 0, calls[0].start())
        self.assertGreaterEqual(start, 0)
        self.assertIn("local probe = AITestMode();", code[start:calls[0].start()])
        self.assertIn("}", code[calls[0].end():])
        self.assertNotIn("BuildRailStation", read("rail_long_window_enumerator.nut"))


def synthetic_log(
    *,
    done=True,
    summary=True,
    second_summary=True,
    chain=True,
    ready=True,
    reuse=True,
):
    lines = ["Other engine line without OPEX"]
    if done:
        lines.append(
            "2026-10-24 INFO OPEX 1970-2-2 RLW04B_ENUM phase=done sources=10 "
            "slices=10 pairs=31 total_ops=90 overruns=0 ticks=0"
        )
    if summary:
        lines.append(
            "2026-10-24 INFO OPEX 1970-2-2 RLW06_SUMMARY key=- "
            "best=2 starts=0 failed=0 searches=0 ready=0 stored=0 reused=0 "
            "expired=0 deferred=5 slices=0 init_ops=0 astar_ops=0 "
            "finalize_ops=0 total_ops=0 ticks=0 cross=0 max_init=0 max_slice=0"
        )
    if chain:
        lines += [
            "OPEX 1970-2-3 RLW06_PAIR key=1|101|202 rank=1 cargo=COAL src=101 "
            "dst=202 score=999 distance=240",
            "OPEX 1970-2-3 RLW06_STEP key=1|101|202 stage=economics next=platforms "
            "reason=continue iters=0 opcodes=12 ticks=0",
            "OPEX 1970-2-4 RLW06_ASTAR key=1|101|202 iteration_budget=600 segmented=1",
            "OPEX 1970-2-4 RLW06_STEP key=1|101|202 stage=search next=finalize "
            "reason=OK iters=80 opcodes=70 ticks=1",
        ]
        if ready:
            lines.append(
                "OPEX 1970-2-5 RLW06_READY key=1|101|202 source=101 sink=202 "
                "len=270 iters=80 opcodes=82 days=2 ttl=365 shadow=1"
            )
        if reuse:
            lines.append(
                "OPEX 1970-2-6 RLW06_REUSE key=- pair=1|101|202 "
                "len=270 age=1 shadow=1"
            )
    if second_summary:
        lines.append(
            "OPEX 1970-5-2 RLW06_SUMMARY key=- best=2 starts=1 failed=0 "
            "searches=1 ready=1 stored=1 reused=1 expired=0 deferred=9 "
            "slices=2 init_ops=12 astar_ops=70 finalize_ops=40 total_ops=122 "
            "ticks=1 cross=1 max_init=12 max_slice=70"
        )
    return "\n".join(lines) + "\n"


class RLW06AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def write(self, seed, repeat, content):
        log = self.directory / f"reference_seed{seed}_r{repeat}.log"
        log.write_text(content, encoding="utf-8")
        return log

    def test_chain_and_latest_summary(self):
        row = analyze_rlw06.analyse(self.write(42, 0, synthetic_log()))
        self.assertEqual((row["seed"], row["repeat"]), (42, 0))
        self.assertTrue(row["enum_done"])
        self.assertEqual(row["summary_count"], 2)
        self.assertEqual(row["last_summary"]["total_ops"], 122)
        self.assertEqual(row["last_summary"]["deferred"], 9)
        self.assertEqual(
            row["chain_counts"],
            {"pair": 1, "pair_to_astar": 1, "pair_to_astar_to_ready": 1,
             "pair_to_astar_to_ready_to_reuse": 1},
        )
        chain = row["chains"][0]
        self.assertEqual(chain["key"], "1|101|202")
        self.assertEqual(chain["reuse"]["pair"], "1|101|202")
        self.assertEqual(row["observed_steps"]["steps"], 2)
        self.assertEqual(row["observed_steps"]["logged_ops"], 82)
        self.assertEqual(row["observed_steps"]["logged_ticks"], 1)
        self.assertEqual(row["observed_steps"]["crossed_steps"], 1)
        # Logged STEPs deliberately do not sum to the cumulative SUMMARY.
        self.assertNotEqual(row["observed_steps"]["logged_ops"],
                            row["last_summary"]["total_ops"])
        analyze_rlw06.check([row], require_complete=True)

    def test_incomplete_chain_cannot_be_reported_as_ready_or_reused(self):
        row = analyze_rlw06.analyse(self.write(
            100, 1, synthetic_log(ready=False, reuse=False)
        ))
        self.assertEqual(row["chain_counts"]["pair_to_astar"], 1)
        self.assertEqual(row["chain_counts"]["pair_to_astar_to_ready"], 0)
        self.assertEqual(row["chain_counts"]["pair_to_astar_to_ready_to_reuse"], 0)

    def test_missing_done_or_summary_fail_complete(self):
        row_no_done = analyze_rlw06.analyse(self.write(
            1, 0, synthetic_log(done=False)
        ))
        with self.assertRaisesRegex(ValueError, r"RLW04B_ENUM phase=done"):
            analyze_rlw06.check([row_no_done], require_complete=True)
        row_no_summary = analyze_rlw06.analyse(self.write(
            2, 0, synthetic_log(summary=False, second_summary=False)
        ))
        with self.assertRaisesRegex(ValueError, r"RLW06_SUMMARY absent"):
            analyze_rlw06.check([row_no_summary], require_complete=True)

    def test_expect_off_requires_no_04b_or_06_events(self):
        empty = self.write(1, 0, "OPEX 1970-1-1 OTHER key=1\n")
        analyze_rlw06.check([analyze_rlw06.analyse(empty)], expect_off=True)
        rlw06 = self.write(
            2, 0, "OPEX 1970-1-1 RLW06_SUMMARY key=- starts=0\n"
        )
        with self.assertRaisesRegex(ValueError, "RLW06_SUMMARY"):
            analyze_rlw06.check([analyze_rlw06.analyse(rlw06)], expect_off=True)
        rlw04 = self.write(
            3, 0, "OPEX 1970-1-1 RLW04B_ENUM phase=start sources=0\n"
        )
        with self.assertRaisesRegex(ValueError, "RLW04B_ENUM"):
            analyze_rlw06.check([analyze_rlw06.analyse(rlw04)], expect_off=True)

    def test_per_seed_aggregates_only_latest_summary_per_repeat(self):
        rows = [
            analyze_rlw06.analyse(self.write(42, 0, synthetic_log())),
            analyze_rlw06.analyse(self.write(42, 1, synthetic_log())),
            analyze_rlw06.analyse(self.write(
                100, 0, synthetic_log(chain=False, second_summary=False)
            )),
        ]
        result = analyze_rlw06.aggregate(rows)
        self.assertEqual(result["by_seed"]["42"]["runs"], 2)
        self.assertEqual(result["by_seed"]["42"]["last_summary_totals"]["total_ops"], 244)
        self.assertEqual(result["by_seed"]["42"]["last_summary_totals"]["starts"], 2)
        self.assertEqual(result["by_seed"]["42"]["chains"]
                         ["pair_to_astar_to_ready_to_reuse"], 2)
        self.assertEqual(result["by_seed"]["100"]["last_summary_totals"]["starts"], 0)
        self.assertEqual(result["totals"]["runs"], 3)

    def test_cli_output_flags_and_empty_directory(self):
        self.write(42, 0, synthetic_log())
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                analyze_rlw06.main([str(self.directory), "--require-complete"]), 0
            )
        self.assertEqual(json.loads(output.getvalue())["totals"]["runs"], 1)
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as caught:
            analyze_rlw06.main([str(self.directory), "--expect-off"])
        self.assertEqual(caught.exception.code, 2)
        with tempfile.TemporaryDirectory() as dirname:
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as caught:
                analyze_rlw06.main([dirname])
            self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
