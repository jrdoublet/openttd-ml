"""Contracts for the opt-in cached rail project proximity check."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"

def source(name):
    return (ROOT / name).read_text(encoding="utf-8")


class RailCachedProximityGate(unittest.TestCase):
    def test_all_defaults_are_zero_and_three_modes(self):
        info = source("info.nut")
        block = info.split('name = "rail_cached_proximity_gate",', 1)[1].split("});", 1)[0]
        self.assertIn("min_value = 0, max_value = 2", block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"\b{level}_value\s*=\s*0\b")
        self.assertIn("RAIL_CACHED_PROXIMITY_GATE <- 0;", source("globals_pre.nut"))
        self.assertIn('RAIL_CACHED_PROXIMITY_GATE = AIController.GetSetting("rail_cached_proximity_gate");',
                      source("settings.nut"))

    def test_matches_actual_build_precheck_and_join_exception(self):
        helper = source("projects_generation.nut").split(
            "function OpexRailCachedProximity(project, lines)", 1)[1].split(
            "function OpexRailCachedProximityKeep(", 1)[0]
        build = source("lines.nut").split("function OpexAI::_tooClose(candidate)", 1)[1].split(
            "function OpexAI::_findLineById(", 1)[0]
        for invariant in (
            '("joinLineId" in candidate) ? candidate.joinLineId : -1',
            'line.lineId == joinLineId',
            'AIMap.DistanceManhattan(entry[1], originTile)',
            'OpexRememberClosest(d, ORIGIN_SEPARATION, originA)',
            'OpexRememberClosest(d, ORIGIN_SEPARATION, originB)',
            'originA >= 0 && originB >= 0',
            'OpexLineStationId(line, lineEnd)',
            'AIMap.DistanceManhattan(entry[1], stationTile)',
            'OpexRememberClosest(d, MIN_SEPARATION, blocking)',
            'return { hard = -1, blocking = blocking };',
        ):
            self.assertIn(invariant, helper)
            self.assertIn(invariant, build)

    def test_only_cached_validation_and_reselection_are_affected(self):
        generation = source("projects_generation.nut")
        selection = source("projects_selection.nut")
        self.assertIn('OpexRailCachedProximityKeep(p, lines, "incremental")', generation)
        self.assertIn('OpexRailCachedProximityKeep(project, lines, "reselect")', selection)
        self.assertIn("if (RAIL_CACHED_PROXIMITY_GATE == 0", generation)
        self.assertIn("return RAIL_CACHED_PROXIMITY_GATE != 2;", generation)
        self.assertIn('if (RAIL_CACHED_PROXIMITY_GATE != 0 && lines != null)', selection)
        self.assertEqual(generation.count("OpexRailCachedProximityKeep(p, lines, "), 1)
        self.assertEqual(selection.count('OpexRailCachedProximityKeep(project, lines, "reselect")'), 1)
        self.assertNotIn("OpexRailCachedProximityKeep(", source("candidates.nut"))
        self.assertNotIn("OpexRailCachedProximityKeep(", source("task_rail.nut"))
        self.assertIn('("isChain" in candidate) && candidate.isChain', generation)


if __name__ == "__main__":
    unittest.main()
