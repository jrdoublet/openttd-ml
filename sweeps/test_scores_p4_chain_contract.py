"""P4 evidence of constructor outcomes. Structural, not a Squirrel runtime test."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = (ROOT / "ai/OpexAI/task_projects.nut").read_text(encoding="utf8")


class P4ChainContract(unittest.TestCase):
    def test_shadow_default_off(self):
        info = (ROOT / "ai/OpexAI/info.nut").read_text(encoding="utf8")
        block = info.split('name = "score_p4_flip_shadow"', 1)[1].split("});", 1)[0]
        for name in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{name}_value = 0", block)

    def test_outcome_has_durable_line_identity(self):
        self.assertIn("function OpexP4FlipTraceOutcome(", CODE)
        self.assertIn("P4_FLIP_OUTCOME id=", CODE)
        self.assertIn('" outcome=" + outcome', CODE)
        self.assertIn('" new_line=" + newLine', CODE)
        self.assertIn('SCORE_P4_FLIP_LAST.head != project', CODE)
        self.assertEqual(CODE.count('OpexP4FlipTraceOutcome(project, year, i, attempt.outcome,'), 5)

    def test_pending_is_separate_from_built(self):
        self.assertIn('attempt.outcome == "pending" && SCORE_P4_FLIP_LAST != null', CODE)
        self.assertIn('this._railSearch.p4FlipTraceId <- SCORE_P4_FLIP_LAST.id', CODE)
        self.assertIn('P4_FLIP_RESUME id=', CODE)
        self.assertIn('railBuilt ? "built" : "not_built"', CODE)

    def test_all_builder_calls_are_after_gate(self):
        self.assertIn('if (SCORE_P4_FLIP_SHADOW)', CODE)
        for method in ("_tryBuildFleetProject", "_tryBuildAirProject",
                       "_tryBuildRoadProject", "_tryBuildRailProject",
                       "_tryBuildWaterProject"):
            self.assertIn("this." + method + "(", CODE)


if __name__ == "__main__":
    unittest.main()
