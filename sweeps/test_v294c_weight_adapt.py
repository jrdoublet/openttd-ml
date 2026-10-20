"""Static V294c contracts (no engine smoke and no Squirrel compilation)."""

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def function(code, name):
    match = re.search(r"^function " + re.escape(name) + r"\([^\n]*\)\s*\{", code, re.M)
    if match is None:
        raise AssertionError(f"Missing function {name}")
    end = code.find("\nfunction ", match.end())
    return code[match.start():end if end >= 0 else len(code)]


class TestV294cWeightAdapt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = source("info.nut")
        cls.settings = source("settings.nut")
        cls.globals = source("globals_pre.nut")
        cls.builder = source("builder_rail.nut")
        cls.task = source("task_rail.nut")

    def test_public_setting_is_off_in_all_profiles_and_range_is_validated(self):
        match = re.search(r'AddSetting\(\{\s*name = "v294_rail_weight_adapt",(.*?)\}\);',
                          self.info, re.S)
        self.assertIsNotNone(match)
        block = match.group(1)
        self.assertIn("min_value = 0, max_value = 400", block)
        for profile in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{profile}_value\s*=\s*0\b")
        self.assertRegex(self.globals, r"\bV294C_RAIL_WEIGHT_ADAPT\s*<-\s*0;")
        self.assertEqual(self.settings.count('AIController.GetSetting("v294_rail_weight_adapt")'), 1)
        self.assertEqual(sum(p.read_text(encoding="utf-8").count(
            'GetSetting("v294_rail_weight_adapt")') for p in AI.glob("*.nut")), 1)
        self.assertIn("weightAdapt >= 100 && weightAdapt <= 400", self.settings)
        self.assertIn("? weightAdapt : 0", self.settings)

    def test_state_is_local_and_three_callers_share_one_implementation(self):
        create = function(self.builder, "OpexCreateSegmentedSearch")
        advance = function(self.builder, "OpexAdvanceSegmentedSearch")
        self.assertIn("state.v294cWeight <- V294C_RAIL_WEIGHT_ADAPT;", create)
        self.assertIn("state.v294cTier <- 0;", create)
        self.assertIn("state.v294cLastDist <- OpexV294cSourceDistance(state);", create)
        self.assertIn("state.v294cLastDist = OpexV294cSourceDistance(state);", advance)
        self.assertIn("pathfinder.cost.astar_weight_pct = state.v294cWeight;", advance)
        self.assertIn("pathfinder.cost.astar_weight_pct = state.weight;", advance)
        self.assertEqual(self.task.count("segmented = OpexCreateSegmentedSearch("), 3)
        for caller in ("_startRailSearch", "_startRailUpgradeSearch", "_startRailStockSearch"):
            self.assertIn(f"function OpexAI::{caller}(", self.task)

    def test_stall_uses_nearest_actual_goal_then_two_fallbacks(self):
        distance = function(self.builder, "OpexV294cGoalDistance")
        switch = function(self.builder, "OpexV294cSwitchWeight")
        advance = function(self.builder, "OpexAdvanceSegmentedSearch")
        self.assertIn("AIMap.DistanceManhattan(tile, goal[0])", distance)
        self.assertIn("local progress = state.v294cLastDist - remaining;", advance)
        self.assertIn("progress * 10 < state.v294cLastDist", advance)
        self.assertIn("if (state.v294cTier < 2) state.v294cTier++;", switch)
        self.assertIn("state.v294cTier = 0;", switch)
        self.assertIn("local nextWeight = V294C_RAIL_WEIGHT_ADAPT;", switch)
        self.assertIn("if (state.v294cTier == 1) nextWeight = state.weight;", switch)
        self.assertIn("else if (state.v294cTier == 2) nextWeight = 100;", switch)
        self.assertIn('OpexDecide("V294C", "event=weight from="', switch)
        self.assertIn('" seg=" + state.segments + " remaining=" + remaining', switch)

    def test_nopa_and_backtrack_are_bounded_and_do_not_reset_total_iterations(self):
        retry = function(self.builder, "OpexV294cRetryNoPath")
        backtrack = function(self.builder, "OpexTrySegmentedBacktrack")
        advance = function(self.builder, "OpexAdvanceSegmentedSearch")
        self.assertIn("state.v294cTier >= 2", retry)
        self.assertIn("state.iterations >= state.iterationBudget", retry)
        self.assertIn("state.iterations >= state.timeSafe", retry)
        self.assertIn("OpexV294cSwitchWeight(state, true", retry)
        self.assertIn("OpexV294cSwitchWeight(state, true", backtrack)
        # Deux reprises : retour sur le prefixe et frontiere inutilisable. Pas sur tas vide :
        # max_cost elague sur g, un poids plus bas ne rendrait rien atteignable de plus.
        self.assertEqual(advance.count("OpexV294cRetryNoPath(state, deadlineTick)"), 2)
        empty = advance[advance.index("if (path == null) {"):]
        empty = empty[:empty.index('return OpexSegmentedResult(state, null, "NOPA", true);')]
        self.assertNotIn("OpexV294cRetryNoPath", empty)
        self.assertNotRegex(retry + backtrack, r"state\.iterations\s*=\s*0\b")

    def test_retry_skips_same_weight_tier_and_logs_adaptive_weight(self):
        retry = function(self.builder, "OpexV294cRetryNoPath")
        switch = function(self.builder, "OpexV294cSwitchWeight")
        self.assertIn("while (state.v294cTier < 2 && state.v294cWeight == before)", retry)
        self.assertIn("if (state.v294cWeight == before) return false;", retry)
        self.assertIn("state.v294cSwitches++;", switch)
        rail = (AI / "task_rail.nut").read_text(encoding="utf-8")
        self.assertIn("if (V294C_RAIL_WEIGHT_ADAPT > 0 && DECISION_LOG && (\"segmented\" in state)", rail)
        self.assertIn('" adapt=" + (("v294cAdapt" in candidate) ? candidate.v294cAdapt : "-")', rail)
        self.assertIn('" len=" + (("routeLen" in candidate) ? candidate.routeLen : -1)', rail)
        builder = (AI / "builder_rail.nut").read_text(encoding="utf-8")
        self.assertIn("if (!(\"routeLen\" in candidate)) candidate.routeLen <- routeDistance;", builder)

    def test_new_calls_are_guarded_and_no_unregistered_global_or_closure(self):
        create = function(self.builder, "OpexCreateSegmentedSearch")
        advance = function(self.builder, "OpexAdvanceSegmentedSearch")
        backtrack = function(self.builder, "OpexTrySegmentedBacktrack")
        self.assertIn("if (V294C_RAIL_WEIGHT_ADAPT > 0)", create)
        self.assertIn("if (V294C_RAIL_WEIGHT_ADAPT > 0)", backtrack)
        self.assertGreaterEqual(advance.count("if (V294C_RAIL_WEIGHT_ADAPT > 0)"), 3)
        self.assertEqual(advance.count("if (V294C_RAIL_WEIGHT_ADAPT > 0 && OpexV294cRetryNoPath"), 2)
        self.assertEqual(set(re.findall(r"\bV294C_[A-Z_]+\b", self.builder + self.settings)),
                         {"V294C_RAIL_WEIGHT_ADAPT"})
        for name in ("OpexV294cGoalDistance", "OpexV294cSourceDistance",
                     "OpexV294cSwitchWeight", "OpexV294cRetryNoPath"):
            self.assertNotRegex(function(self.builder, name), r"\blocal\s+\w+\s*=\s*function\b")


if __name__ == "__main__":
    unittest.main()
