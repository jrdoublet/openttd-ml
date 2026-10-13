"""Contracts for the isolated P0 end-of-tick shadow, without a game engine."""

import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def body(source, signature):
    """Return one Squirrel function body with brace nesting, ignoring comments/strings."""
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    quoted = False
    escaped = False
    comment = None
    for i in range(opening, len(source)):
        c = source[i]
        following = source[i:i + 2]
        if comment == "line":
            if c == "\n":
                comment = None
            continue
        if comment == "block":
            if following == "*/":
                comment = None
            continue
        if quoted:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
            continue
        if following == "//":
            comment = "line"
            continue
        if following == "/*":
            comment = "block"
            continue
        if c == '"':
            quoted = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:i]
    raise ValueError(f"unbalanced function {signature}")


class TailShadowContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probes = (AI / "probes.nut").read_text(encoding="utf-8")
        cls.info = (AI / "info.nut").read_text(encoding="utf-8")
        cls.settings = (AI / "settings.nut").read_text(encoding="utf-8")
        cls.globals = (AI / "globals_pre.nut").read_text(encoding="utf-8")
        cls.main = (AI / "main.nut").read_text(encoding="utf-8")
        cls.terrain = (AI / "task_terrain.nut").read_text(encoding="utf-8")

    def test_off_by_default_and_gated_by_loop_probe(self):
        decl = re.search(r'AddSetting\(\{\s*name = "probe_tail_shadow",(.*?)\}\);',
                         self.info, re.S)
        self.assertIsNotNone(decl)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(decl[1], rf"\b{difficulty}_value\s*=\s*0\b")
        self.assertIn("PROBE_TAIL_SHADOW <- false;", self.globals)
        self.assertRegex(self.settings, r"PROBE_TAIL_SHADOW\s*=\s*PROBE_LOOP_OPS\s*&&\s*"
                         r'AIController.GetSetting\("probe_tail_shadow"\)\s*!=\s*0;')
        self.assertRegex(self.main, r"if \(PROBE_LOOP_OPS\) this\._mainLoopProfiled\(\)")

    def test_exactly_once_at_tail_after_c67_and_before_sleep(self):
        loop = body(self.probes, "function OpexAI::_mainLoopProfiled()")
        self.assertEqual(loop.count("OpexTailShadowSample(this);"), 1)
        self.assertLess(loop.index("this._c67SlackHook();"),
                        loop.index("OpexTailShadowSample(this);"))
        self.assertLess(loop.index("OpexTailShadowSample(this);"),
                        loop.index("AIController.Sleep(1);"))
        self.assertIn("if (PROBE_TAIL_SHADOW) {", loop)
        self.assertIn("OpexLoopProfAdd(\"tail_shadow\", tailMark);", loop)
        self.assertLess(loop.index("OpexTailShadowSample(this);"),
                        loop.index('OpexLoopProfAdd("tail_shadow", tailMark);'))
        self.assertIn('OpexLoopProfAddRaw("sleep_left", leftAtSleep, 0);', loop)
        self.assertIn("this._refreshSaveProjection();", loop)
        self.assertIn("OpexC121StationFluxStep(this._catalog);", loop)

    def test_bound_is_identical_to_c67_contract(self):
        floor = int(re.search(r"C67_SLACK_MIN\s*<-\s*(\d+)", self.terrain)[1])
        reserve = int(re.search(r"C67_SLACK_RESERVE\s*<-\s*(\d+)", self.terrain)[1])
        self.assertEqual((floor, reserve), (4000, 3000))
        budget = body(self.probes, "function OpexTailShadowBudget(left)")
        self.assertIn("left >= C67_SLACK_MIN ? left - C67_SLACK_RESERVE : 0", budget)
        for left, expected in ((0, 0), (2999, 0), (3999, 0), (4000, 1000),
                               (8000, 5000), (10000, 7000)):
            self.assertEqual((left - reserve) if left >= floor else 0, expected)

    def test_only_constant_time_reads_no_work_is_dispatched(self):
        sample = body(self.probes, "function OpexTailShadowSample(ai)")
        classify = body(self.probes, "function OpexTailShadowClass(")
        for section in (sample, classify):
            self.assertNotRegex(section, r"\b(?:foreach|for|while)\s*\(")
            for forbidden in ("OpexWorkerStep", "OpexC56WorkerStep", "_runOrchestratorTick",
                              "_dispatch", "OpexReselectProjects", "Sleep(", ".Step(",
                              "_popReactive", "AILog.Info", "GetVehicle", "GetCargoWaiting"):
                self.assertNotIn(forbidden, section)
        self.assertIn("ai._reactiveQueue.len()", sample)
        self.assertIn("ai._activeWorker", sample)
        self.assertIn("ai._railSearch", sample)
        self.assertIn("ai._c121RailPrepHold", sample)
        self.assertIn("C67_SLACK_HOOK", sample)
        self.assertIn('"isC121RailPrep" in search', classify)
        self.assertIn('".orphan_hold"', classify)
        self.assertIn('"unknown" : "none"', classify)

    def test_cost_and_tick_crossing_cannot_report_fictitious_budget(self):
        sample = body(self.probes, "function OpexTailShadowSample(ai)")
        self.assertLess(sample.index("if (left0 < C67_SLACK_MIN)"),
                        sample.index("ai._reactiveQueue.len()"))
        self.assertIn("local crossed = tick1 != tick0;", sample)
        self.assertIn("local afterCap = crossed ? 0 : OpexTailShadowBudget(left1);", sample)
        self.assertIn("s.guardOps += guardOps;", sample)
        self.assertIn("if (crossed) s.crosses++;", sample)
        span = body(self.probes, "function OpexTailShadowOps(")
        self.assertIn("startLeft + (elapsed - 1) * OPS_PER_TICK + (OPS_PER_TICK - endLeft)", span)
        for start_tick, left0, end_tick, left1, expected in (
            (1, 7000, 1, 6500, 500),
            (1, 7000, 2, 9900, 7100),
            (1, 7000, 3, 9800, 17200),
        ):
            n = end_tick - start_tick
            actual = max(0, left0 - left1) if n == 0 else left0 + (n - 1) * 10000 + 10000 - left1
            self.assertEqual(actual, expected)

    def test_annual_only_logging_and_no_persisted_state(self):
        sample = body(self.probes, "function OpexTailShadowSample(ai)")
        flush = body(self.probes, "function OpexTailShadowFlush(year)")
        year = body(self.probes, "function OpexLoopProfFlushIfNewYear()")
        self.assertNotIn("AILog.", sample)
        self.assertEqual(flush.count('AILog.Info("TAIL_SHADOW'), 2)
        self.assertIn("OPEX_TAIL_SHADOW = null;", flush)
        self.assertIn("if (PROBE_TAIL_SHADOW) OpexTailShadowFlush(OPEX_LOOP_PROF_YEAR);", year)
        self.assertLess(year.index("if (year == OPEX_LOOP_PROF_YEAR) return;"),
                        year.index("OpexTailShadowFlush(OPEX_LOOP_PROF_YEAR)"))
        persisted = (AI / "persist.nut").read_text(encoding="utf-8")
        self.assertNotIn("OPEX_TAIL_SHADOW", persisted)
        self.assertNotIn("PROBE_TAIL_SHADOW", persisted)


if __name__ == "__main__":
    unittest.main()
