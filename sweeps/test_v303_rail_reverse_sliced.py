#!/usr/bin/env python3
"""Host contracts for opt-in V303 C80 reverse-pathfinder slicing.

These static checks deliberately do not claim Squirrel compilation or route
equivalence; those require an actual OpenTTD smoke and paired engine logs.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def body(source: str, symbol: str) -> str:
    start = source.index(f"function {symbol}(")
    brace = source.index("{", start)
    nesting = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            nesting += 1
        elif source[i] == "}":
            nesting -= 1
            if nesting == 0:
                return source[brace + 1:i]
    raise AssertionError(f"Unclosed function {symbol}")


class V303ReverseSliceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = read("info.nut")
        cls.globals = read("globals_pre.nut")
        cls.settings = read("settings.nut")
        cls.main = read("main.nut")
        cls.builder = read("builder_rail.nut")
        cls.rail = read("task_rail.nut")
        cls.scheduler = read("scheduler.nut")
        cls.orchestrator = read("orchestrator.nut")
        cls.persist = read("persist.nut")
        cls.start = body(cls.rail, "OpexAI::_startRailSearch")
        cls.advance = body(cls.rail, "OpexAI::_continueRailSearch")
        cls.slice = body(cls.builder, "OpexV303ReverseSlice")

    def test_mode_opt_in_four_defaults_and_setting_load(self):
        match = re.search(r'AddSetting\(\{\s*name\s*=\s*"v303_reverse_probe_sliced"(.*?)\}\);',
                          self.info, re.S)
        self.assertIsNotNone(match)
        block = match.group(1)
        for name in ("easy", "medium", "hard", "custom", "default"):
            self.assertRegex(block, rf"\b{name}_value\s*=\s*0\b")
        self.assertRegex(block, r"\bmin_value\s*=\s*0\b")
        self.assertRegex(block, r"\bmax_value\s*=\s*2\b")
        self.assertIn("V303_REVERSE_PROBE_SLICED <- 0;", self.globals)
        self.assertEqual(self.settings.count('GetSetting("v303_reverse_probe_sliced")'), 1)
        self.assertIn("V303_REVERSE_PROBE_SLICED = (v303Sliced == 1 || v303Sliced == 2) ? v303Sliced : 0;", self.settings)

    def test_off_shadow_use_same_historical_function(self):
        self.assertIn("if (V303_REVERSE_PROBE_SLICED == 2)", self.start)
        self.assertIn("} else {\n    local revSlice = OpexV294fReverseProbe(", self.start)
        self.assertEqual(self.start.count("OpexV294fReverseProbe("), 1)
        self.assertEqual(self.start.count("OpexPrepareRailRoute("), 1)
        self.assertNotIn("AITestMode()", self.start)

    def test_single_reverse_pf_and_forward_only_after_failure(self):
        reverse = self.start.split("if (V303_REVERSE_PROBE_SLICED == 2)", 1)[1].split("} else {", 1)[0]
        self.assertIn("OpexCreateRailPathfinder(plan.plansB, plan.plansA,", reverse)
        self.assertIn('phase = "reverse"', reverse)
        self.assertNotIn("OpexCreateSegmentedSearch(", reverse)
        fallback = body(self.rail, "OpexAI::_v303BeginForwardAfterProbe")
        self.assertLess(fallback.index("state.pathfinder = null;"),
                        fallback.index("OpexCreateRailPathfinder("))
        self.assertIn("OpexCreateSegmentedSearch(", fallback)
        self.assertIn('state.phase = "search";', fallback)
        self.assertIn('state.phase = "build";', fallback)
        self.assertIn("function _v303BeginForwardAfterProbe(state);", self.main)

    def test_reverse_helper_reuses_pathfinder_with_per_call_delta(self):
        self.assertEqual(self.slice.count("FindPath("), 1)
        self.assertIn("pathfinder.FindPath(limit)", self.slice)
        self.assertIn("pathfinder.LastConsumed()", self.slice)
        self.assertIn("remaining = iterationCap - spent", self.slice)
        self.assertIn("remaining < PATH_CHUNK ? remaining : PATH_CHUNK", self.slice)
        self.assertIn("used < 0 || used > limit", self.slice)
        self.assertIn("spent += used;", self.slice)
        self.assertIn('stop = "CONT"', self.slice)
        self.assertIn('stop = "NOPA"', self.slice)
        self.assertIn('stop = "ABND"', self.slice)
        self.assertIn('stop = "ERROR"', self.slice)
        self.assertIn("if (path != null && path != false)", self.slice)
        self.assertIn("tiles.reverse()", self.slice)
        v129 = read("pathfinder_v90/v129.nut")
        self.assertIn("this._consumed = pops;", v129)
        self.assertIn("LastConsumed() { return this._consumed; }", v129)

    def test_reverse_iteration_cap_and_six_slices(self):
        self.assertIn("reverseSpent = 0, reverseOps = 0, reverseSlices = 0", self.start)
        self.assertIn("reverseCap = V294_RAIL_REVERSE_PROBE", self.start)
        self.assertIn("state.reverseSpent = rev.iterations", self.advance)
        self.assertIn("state.reverseSlices++;", self.advance)
        self.assertIn("if (spent >= iterationCap)", self.slice)
        self.assertIn("if (used == 0)", self.slice)
        self.assertIn("const PATH_CHUNK = 50;", self.builder)
        self.assertIn("V294_RAIL_REVERSE_PROBE <- 300;", self.globals)

    def test_reverse_charges_ops_exactly_once_and_separately(self):
        self.assertIn('this._budget.end("build_search")', self.advance)
        self.assertIn("state.reverseOps += sliceOps;", self.advance)
        self.assertIn("state.plan.opcodes += sliceOps;", self.advance)
        self.assertIn("state.plan.phaseOps.search += sliceOps;", self.advance)
        self.assertIn("OpexAddRailSearchOps(state.candidate, sliceOps)", self.advance)
        self.assertIn('OpexDecide("V303_REVERSE"', self.advance)
        self.assertIn('" slice_ops=" + sliceOps', self.advance)
        self.assertIn('" slice_ticks=" + (AIController.GetTick() - sliceStartTick)', self.advance)

    def test_final_probe_event_only_after_completion(self):
        self.assertIn("if (!rev.done && !tooOld) return;", self.advance)
        completion = self.advance.index("if (!rev.done && !tooOld) return;")
        self.assertGreater(self.advance.index('OpexDecide("V294F_PROBE"'), completion)
        self.assertEqual(self.advance.count('OpexDecide("V294F_PROBE"'), 1)
        self.assertIn("this._v303BeginForwardAfterProbe(state);", self.advance)
        self.assertIn("state.pathfinder = null;", self.advance)
        self.assertIn("OpexCompleteRailRouteAfterSearch(", self.advance)
        self.assertIn('state.phase = "build";', self.advance)
        self.assertIn('OpexC56TaskLog("V303_REVERSE_END"', self.advance)

    def test_scheduler_and_worker_dont_drop_reverse_pending(self):
        self.assertIn('this._railSearch.phase == "reverse"', self.scheduler)
        step = body(self.orchestrator, "OpexWorkerRailSearchStep")
        self.assertIn('ai._railSearch.phase != "reverse"', step)
        self.assertIn("ai._advanceRailSearchSliceWithLedgers();", step)
        self.assertIn("wasReverse ? sliceState.reverseSpent : sliceState.spent", self.scheduler)

    def test_load_abandons_transient_pathfinder(self):
        self.assertIn("railSearchPending = this._railSearch != null", self.persist)
        self.assertIn("this._railSearch = null;", self.persist)
        self.assertIn("this._projects = null;", self.persist)
        self.assertIn("this._portfolioInvalidated = true;", self.persist)
        self.assertNotIn("reversePf", self.persist)
        self.assertNotIn("reverseSpent", self.persist)


if __name__ == "__main__":
    unittest.main()
