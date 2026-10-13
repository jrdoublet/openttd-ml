"""P4 guardrails: the experimental annual cohort audit never changes C70 scoring.

These are source contracts only: Squirrel compilation and real economics need the
OpenTTD Docker smoke controlled by the prime agent.
"""

from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
BASELINE = "c2a5be3"


def function_body(source: str, name: str) -> str:
    match = re.search(r"function\s+" + re.escape(name) + r"\s*\([^\n]*\)\s*\{", source)
    if match is None:
        raise AssertionError(f"missing function: {name}")
    depth = 0
    for pos in range(match.end() - 1, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start() : pos + 1]
    raise AssertionError(f"unbalanced function: {name}")


class P4CohortProbeContracts(unittest.TestCase):
    def test_off_on_four_difficulties_and_settings(self):
        info = (AI / "info.nut").read_text(encoding="utf-8")
        settings = (AI / "settings.nut").read_text(encoding="utf-8")
        globals_pre = (AI / "globals_pre.nut").read_text(encoding="utf-8")
        cfg = re.search(r'name = "score_c70_cohort_probe",(.*?)\}\);', info, re.S)
        self.assertIsNotNone(cfg)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{difficulty}_value = 0", cfg.group(1))
        self.assertIn('SCORE_C70_COHORT_PROBE <- false', globals_pre)
        self.assertIn('SCORE_C70_COHORT_LOG = AIController.GetSetting("score_c70_cohort_probe") != 0;', settings)
        self.assertIn('SCORE_C70_COHORT_PROBE = SCORE_C70_COHORT_LOG || SCORE_C70_STABLE_COHORT;', settings)

    def test_c70_c82_original_core_byte_identical_save_sidecar_explicitly_gated(self):
        for source_name, names in (
            ("task_report.nut", ("OpexC70C82AccumulateLine", "OpexC70PublishModeFactors", "OpexC82PublishEngineFactors")),
            ("projects_models.nut", ("OpexC82RecomputeFactors",)),
            ("persist.nut", ("OpexSaveProjectLine",)),
        ):
            after = (AI / source_name).read_text(encoding="utf-8")
            before = subprocess.check_output(
                ["git", "show", f"{BASELINE}:ai/OpexAI/{source_name}"], cwd=ROOT
            ).decode("utf-8")
            for name in names:
                with self.subTest(name=name):
                    self.assertEqual(function_body(before, name), function_body(after, name))
        # A separate ON-only wrapper handles p4VYear, leaving OFF byte-identical.
        save = function_body((AI / 'persist.nut').read_text(encoding='utf-8'), 'OpexSaveProjectLine')
        self.assertNotIn('p4VYear', save)

    def test_probe_uses_previous_fleet_identity_and_young_age(self):
        task = (AI / "task_report.nut").read_text(encoding="utf-8")
        code = function_body(task, "OpexC70P4ObserveLine")
        self.assertIn('line.p4C70Year == year - 1', code)
        self.assertIn('ids[j] != line.p4C70Ids[j]', code)
        self.assertIn('AIVehicle.GetAge(v) < dayFloor', code)
        self.assertIn('AIDate.GetDate(year - 1, 1, 1)', code)
        self.assertIn('line.p4C70Ids <- ids', code)
        self.assertIn('line.p4C70Year <- year', code)
        self.assertIn('!mutated', code)
        self.assertIn('line.p4C70Real += real', code)
        self.assertIn('line.p4C70Pred += cPred.tofloat()', code)
        self.assertIn('line.p4C70Real.tofloat() / line.p4C70Pred.tofloat()', code)
        self.assertIn('"P4_C70_LINE exercise="', code)
        report = function_body(task, "OpexAI::_reportLines")
        self.assertLess(report.index('OpexC70C82AccumulateLine('), report.index('OpexC70P4ObserveLine('))
        self.assertIn('if (p4C70Sums != null)', report)
        self.assertIn('"P4_C70_SUM exercise="', report)
        self.assertIn('" candidate_year="', report)
        self.assertIn('" candidate_cumulative_lines="', report)

    def test_known_replacements_and_crashes_are_marked(self):
        events = (AI / "event_handlers.nut").read_text(encoding="utf-8")
        self.assertIn('OpexC70P4MarkMutation(line)', function_body(events, "OpexAI::_onVehicleCrashed"))
        self.assertIn('OpexC70P4MarkMutation(line)', function_body(events, "OpexAI::_onVehicleAutoreplaced"))
        marker = function_body((AI / "task_report.nut").read_text(encoding="utf-8"), "OpexC70P4MarkMutation")
        self.assertIn('p4C70MutationPreviousYear', marker)
        self.assertIn('p4C70MutationYear', marker)
        for name in ("air_fleet.nut", "task_rail.nut", "builder_road.nut", "builder_water.nut"):
            with self.subTest(name=name):
                self.assertIn('OpexC70P4MarkMutation(line)', (AI / name).read_text(encoding="utf-8"))
        self.assertIn('OpexC70P4MarkMutation(ownerLine)', (AI / "task_report.nut").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
