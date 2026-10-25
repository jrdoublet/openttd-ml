"""Contrats du second bypass opt-in N75, sans lancement OpenTTD/Docker."""

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse_n75_early_c75 import parse_lines, summarize  # noqa: E402


def load(path):
    return (ROOT / "ai" / "OpexAI" / path).read_text(encoding="utf-8")


def body(text, name):
    start = text.index(name)
    brace = text.index("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"Unclosed Squirrel body {name}")


class TestN75EarlyC75(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = load("info.nut")
        cls.settings = load("settings.nut")
        cls.globals = load("globals_pre.nut")
        cls.projects = load("task_projects.nut")
        cls.rail = load("task_rail.nut")
        cls.persist = load("persist.nut")
        cls.build = body(cls.projects, "function OpexAI::_tryBuildProjects(")
        cls.reason = body(cls.projects, "function OpexN75EarlyC75Reason(")
        cls.log = body(cls.projects, "function OpexN75EarlyC75Log(")

    def test_four_difficulties_default_off_and_single_load(self):
        definition = self.info.split('name = "n75_second_newline_bypass"', 1)[1].split("});", 1)[0]
        self.assertIn("min_value = 0, max_value = 2", definition)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{level}_value = 0", definition)
        self.assertIn("N75_SECOND_NEWLINE_BYPASS <- 0;", self.globals)
        self.assertEqual(self.settings.count('GetSetting("n75_second_newline_bypass")'), 1)
        self.assertIn("? n75EarlyC75 : 0", self.settings)

    def test_original_c75_bypass_remains_one_and_first(self):
        self.assertEqual(self.build.count("c75BypassConsumed = true;"), 1)
        self.assertEqual(self.build.count("n75SecondConsumed = true;"), 1)
        self.assertLess(self.build.index("c75BypassConsumed = true;"),
                        self.build.index("n75SecondConsumed = true;"))
        self.assertIn("c75BypassConsumed && !n75SecondConsumed", self.build)
        self.assertIn("if (!c75BypassThisProject)", self.build)
        self.assertIn('c75StopReason = (availCap >= 0 && projCap > availCap) ? "cash" : "k_pass";', self.build)

    def test_disabled_and_shadow_cannot_consume_extra(self):
        self.assertIn("if (!c75BypassThisProject && N75_SECOND_NEWLINE_BYPASS > 0", self.build)
        self.assertIn("if (N75_SECOND_NEWLINE_BYPASS == 2)", self.build)
        self.assertIn('N75_SECOND_NEWLINE_BYPASS == 1 ? "shadow_only"', self.build)
        self.assertLess(self.build.index("if (N75_SECOND_NEWLINE_BYPASS == 2)"),
                        self.build.index("n75SecondReady = true;"))
        self.assertLess(self.build.index("if (!c75BypassThisProject)"),
                        self.build.index("if (n75SecondReady)"))

    def test_years_relative_to_start_and_no_fleet(self):
        for snippet in ("year >= OPEX_START_YEAR + 1", "year <= OPEX_START_YEAR + 2"):
            self.assertIn(snippet, self.build)
        self.assertIn("OpexC75KPassBypassIsNewLine(project)", self.reason)
        self.assertIn('return "not_newline"', self.reason)
        self.assertNotIn('project.mode == "fleet"', self.reason)

    def test_guards_precede_second_consumption(self):
        for check in ("OpexProjectFinanceCapital(project) > available",
                      "OpexC80ProjectBelowMarginalFloor(ai._lines, project)",
                      "OpexAirBatchPlanStillLive(plan, ai._lines)",
                      "OpexAirBatchSiteStillBuildable(plan.siteA",
                      "OpexAirBatchSiteStillBuildable(plan.siteB",
                      "OpexProjectDefensiveAirPriority(other)",
                      'return "c77"'):
            self.assertIn(check, self.reason)
        self.assertLess(self.build.index('if (OpexC80ProjectBelowMarginalFloor(this._lines, project))'),
                        self.build.index("n75SecondConsumed = true;"))
        self.assertIn("if (availCap < 0) availCap = OpexAvailableCapital();", self.build)

    def test_rail_cannot_start_astar_or_force_pending(self):
        for token in ('"c121PrepStock" in rail', '"railPlan" in rail',
                      'return "rail_no_ready_plan"'):
            self.assertIn(token, self.reason)
        rail_build = body(self.rail, "function OpexAI::_tryBuildRailProject(")
        self.assertIn("n75NoNewSearch = false", rail_build)
        self.assertIn("if (n75NoNewSearch) return { outcome = \"rejected\"", rail_build)
        self.assertLess(rail_build.index("if (n75NoNewSearch)"),
                        rail_build.index("this._startRailSearch("))
        self.assertIn("anchor, yy, n75SecondRank == i", self.build)

    def test_result_follows_actual_executor_for_each_new_line(self):
        for function in ("_tryBuildAirProject(", "_tryBuildRoadProject(",
                         "_tryBuildRailProject(", "_tryBuildWaterProject("):
            before = self.build.index(function)
            self.assertIn("OpexN75EarlyC75Log(", self.build[before:before + 750])
        self.assertIn('attempt.outcome == "built" ? this._nextLineId - 1 : -1', self.build)
        self.assertIn('"built_after_second_bypass"', self.build)

    def test_pass_local_transient_not_saved(self):
        for item in ("local n75SecondConsumed = false;", "local n75SecondRank = -1;",
                     "local n75SecondPassTick ="):
            self.assertIn(item, self.build)
        self.assertNotIn("n75SecondConsumed", self.persist)
        self.assertNotIn("n75SecondRank", self.persist)
        self.assertNotIn("n75SecondPassTick", self.persist)
        self.assertIn("C75_PASS_DATES", self.persist)
        self.assertIn("OPEX_START_YEAR", load("globals_pre.nut"))

    def test_logs_and_durable_sign_without_decision_log(self):
        for token in ("N75_EARLY_C75 phase=", " date=", " year=", " pass_tick=",
                      " rank=", " key=", " profit=", " finance=", " cash=",
                      " available=", " k_pass=", " reason=", " line="):
            self.assertIn(token, self.log)
        self.assertIn('"N5|" + passTick', self.log)
        self.assertIn("OpexSign(AIMap.GetTileIndex(1, 1)", self.log)
        self.assertNotIn("DECISION_LOG", self.log)
        self.assertIn("if (N75_SECOND_NEWLINE_BYPASS <= 0) return;", self.log)

    def test_parser_deduplicates_pass_and_unique_project(self):
        fixture = [
            "N75_EARLY_C75 phase=eligible mode=air year=1972 pass_tick=123 rank=2 key=air|42 profit=30000 finance=10000 reason=shadow_only",
            "N75_EARLY_C75 phase=eligible mode=air year=1972 pass_tick=123 rank=2 key=air|42 profit=30000 finance=10000 reason=shadow_only",
            "N75_EARLY_C75 phase=eligible mode=air year=1972 pass_tick=130 rank=1 key=air|42 profit=30000 finance=10000 reason=second_candidate",
            "N75_EARLY_C75 phase=attempt mode=air year=1972 pass_tick=130 rank=1 key=air|42 profit=30000 finance=10000 reason=passed_c80",
            "N75_EARLY_C75 phase=built mode=air year=1972 pass_tick=130 rank=1 key=air|42 profit=30000 finance=10000 reason=built_after_second_bypass line=8",
            "N5|130|1|A|B|8",
        ]
        events, signs = parse_lines(fixture, "seed42.log")
        result = summarize(events, signs)
        self.assertEqual(result["per_year"]["1972"]["unique_candidate_keys"], 1)
        self.assertEqual(result["per_year"]["1972"]["unique_built_keys"], 1)
        self.assertEqual(result["per_year"]["1972"]["eligible"], 2)
        self.assertEqual(result["per_year"]["1972"]["attempt"], 1)
        self.assertEqual(result["per_year"]["1972"]["built"], 1)
        self.assertEqual(result["per_year"]["1972"]["shadow_only"], 1)
        self.assertEqual(result["signed_events"]["B"], 1)


if __name__ == "__main__":
    unittest.main()
