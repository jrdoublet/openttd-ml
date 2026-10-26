"""P6 opt-in first AIR catalog window: bounded publication, no new search, Save/Load.

The behavioral tests describe the externally observable wait/release contract;
the source checks tie that contract to the existing C78 publication and project
execution sites without running a second, synthetic AIR planner.
"""

from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def body(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for pos in range(opening, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start:pos + 1]
    raise AssertionError(f"unclosed function {signature}")


def release_reason(scan_exists, phase, cursor_done, extra_published,
                   waited_ticks, extra_scan_ops, viable_pairs):
    """Model the observable stop rule over already-published projects."""
    if not scan_exists or phase == "apply" or cursor_done:
        return "scan_done"
    if extra_published:
        return "published"
    if waited_ticks < 0 or waited_ticks >= 32:
        return "tick_limit"
    if extra_scan_ops < 0 or extra_scan_ops >= 160000:
        return "ops_limit"
    if viable_pairs < 2:
        return "viability_lost"
    if viable_pairs >= 3:
        return "third_pair"
    return None


class P6FirstlineContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scheduler = read("scheduler_tasks.nut")
        cls.check = body(cls.scheduler, "function OpexP6FirstlineWindowHold(owner)")
        cls.dispatch = body(cls.scheduler, "function OpexAI::_dispatchProjects(task, year)")
        cls.try_build = body(read("task_projects.nut"),
                             "function OpexAI::_tryBuildProjects(year)")

    def test_setting_is_opt_in_and_default_off_on_every_difficulty(self):
        match = re.search(r'AddSetting\(\{\s*name = "p6_air_firstline_window",(.*?)\}\);',
                          read("info.nut"), re.S)
        self.assertIsNotNone(match)
        setting = match.group(1)
        self.assertIn("min_value = 0, max_value = 1", setting)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting, rf"{level}_value\s*=\s*0")
        self.assertIn('P6_AIR_FIRSTLINE_WINDOW = AIController.GetSetting("p6_air_firstline_window");',
                      read("settings.nut"))
        self.assertIn('P6_AIR_FIRSTLINE_WINDOW <- 0;', read("globals_pre.nut"))
        self.assertIn("if (P6_AIR_FIRSTLINE_WINDOW != 0 && OpexP6FirstlineWindowHold(this))", self.try_build)
        self.assertLess(self.try_build.index("this._ensureSelection();"),
                        self.try_build.index("OpexP6FirstlineWindowHold(this)"))
        self.assertLess(self.try_build.index("OpexP6FirstlineWindowHold(this)"),
                        self.try_build.index("OpexC75BypassEnsureYear(year);"))
        self.assertNotIn("OpexP6FirstlineWindowHold(this)", self.dispatch)
        self.assertIn("this._tryBuildProjects(year)", self.dispatch)

    def test_reactive_build_also_honors_window_and_invalidation_closes_it(self):
        orchestrator = read("orchestrator.nut")
        self.assertIn("this._tryBuildProjects(AIDate.GetYear(AIDate.GetCurrentDate()));",
                      orchestrator)
        self.assertIn("this._ensureSelection();", self.try_build)
        self.assertIn("if (spPass != null) OpexSpanEnd(spPass);", self.try_build)
        self.assertIn('if (this._portfolioInvalidated) {', self.dispatch)
        self.assertIn("this._p6FirstlineWindow = null;", self.dispatch)
        self.assertIn('phase=release reason=invalidated', self.dispatch)
        self.assertTrue("owner._p6FirstlineWindowConsumed = true;" in self.check)

    def test_only_previously_built_eligible_projects_and_c78_progress(self):
        for token in ("owner._projects.best", 'project.mode != "air"',
                      "OpexProjectFinanceCapital(project) > capital",
                      "OpexAirBatchPlanStillLive(project.payload, owner._lines)",
                      "OpexProjectKeyFor(project)", "count != 2",
                      "scan.lastPublishedCount > state.startPublished",
                      "scan.airOps - state.startAirOps", "ticks >= 32",
                      "scanOps >= 160000", "owner._p6FirstlineWindowConsumed = true;"):
            self.assertIn(token, self.check)
        for forbidden in ("OpexAirPlans(", "OpexC121CatalogChoice(",
                          "OpexProjectFromAir(", "_rebuildProjects(",
                          "AIController.Sleep("):
            self.assertNotIn(forbidden, self.check)
        self.assertIn('if (DECISION_LOG) OpexDecide("P6_FIRSTLINE", "phase=wait', self.check)
        self.assertIn('if (DECISION_LOG) OpexDecide("P6_FIRSTLINE", "phase=release', self.check)

    def test_extra_publication_and_hard_limits_are_exits(self):
        baseline = (True, "primary", False, False, 31, 159999, 2)
        self.assertIsNone(release_reason(*baseline))
        cases = [
            ((True, "primary", False, True, 1, 12000, 3), "published"),
            ((True, "primary", False, False, 32, 12000, 2), "tick_limit"),
            ((True, "primary", False, False, 5, 160000, 2), "ops_limit"),
            ((False, "primary", False, False, 1, 12000, 2), "scan_done"),
            ((True, "apply", False, False, 1, 12000, 2), "scan_done"),
            ((True, "primary", True, False, 1, 12000, 2), "scan_done"),
            ((True, "primary", False, False, 1, 12000, 1), "viability_lost"),
            ((True, "primary", False, False, 1, 12000, 3), "third_pair"),
        ]
        for input_values, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(release_reason(*input_values), expected)

    def test_short_full_save_and_load_never_extend_window(self):
        persist = read("persist.nut")
        save = body(persist, "function OpexAI::Save()")
        load = body(persist, "function OpexAI::Load(version, data)")
        short_save = save[:save.index("return shortSave;")]
        full_save = save[save.index("local saveObj = {"):]
        for name, scope in (("shortSave", short_save), ("saveObj", full_save)):
            self.assertIn(f"{name}.p6FirstlineWindowConsumed <- true;", scope)
            self.assertIn("P6_AIR_FIRSTLINE_WINDOW != 0 && this._p6FirstlineWindowConsumed", scope)
        self.assertIn("this._p6FirstlineWindow = null;", load)
        self.assertIn('("p6FirstlineWindowConsumed" in data)', load)
        self.assertIn("data != null", load)
        self.assertNotIn("c78AirRebuild", save)
        self.assertNotIn("c78AirRebuild", load)


if __name__ == "__main__":
    unittest.main()
