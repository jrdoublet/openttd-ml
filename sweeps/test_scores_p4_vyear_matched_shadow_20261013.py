"""Source-contract and economic fixtures for P4-adjust matched measurement shadow.

Host only: asserts the exact source gates, original OFF paths and Save sidecar
semantics; Squirrel VM/opcode equivalence requires a prime-controlled Docker run.
"""

import re
import subprocess
import unittest
from pathlib import Path

from test_scores_p4_vyear_20261013 import (
    factor, load_projection, model_report, saved_projection_and_sidecar, panel_entry
)


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def function_body(s, name):
    match = re.search(r"^function\s+" + re.escape(name) + r"\([^\n]*\)\s*\{", s, re.M)
    if match is None:
        raise AssertionError(f"missing function {name}")
    depth = 0
    # The functions used below do not contain braces in string literals.
    for i in range(match.end() - 1, len(s)):
        if s[i] == "{":
            depth += 1
        if s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[match.start():i + 1]
    raise AssertionError("unbalanced function")


def policy_matrix(cohort, shadow, *, stable=False, full_save=True):
    behavior = bool(cohort and not stable and full_save)
    diagnostic = bool(shadow and not stable and full_save)
    return behavior, behavior or diagnostic


class MatchedShadowContracts(unittest.TestCase):
    def test_c82_default_off_and_override_scope(self):
        info = source('info.nut')
        block = info.split('name = "c82_engine_calibration"', 1)[1].split('});', 1)[0]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(level + "_value = 0", block)
        models = function_body(source('projects_models.nut'), 'OpexC82Profit')
        self.assertIn('if (e >= 0) return project.profitAnnual * OpexC82EngineFactor(e);', models)
        self.assertIn('return OpexC70Profit(project);', models)

    def test_two_flags_off_all_difficulties(self):
        info = source("info.nut")
        for key in ("score_c70_vyear_measure_shadow", "score_c70_vyear_cohort"):
            block = info.split('name = "' + key + '"', 1)[1].split("});", 1)[0]
            for level in ("easy", "medium", "hard", "custom"):
                self.assertIn(level + "_value = 0", block)
        globals_pre = source("globals_pre.nut")
        self.assertIn("SCORE_C70_VYEAR_MEASURE_SHADOW <- false;", globals_pre)
        self.assertIn("SCORE_C70_VYEAR_MEASURE <- false;", globals_pre)

    def test_flag_independence_and_restrictions(self):
        settings = source("settings.nut")
        self.assertIn('SCORE_C70_VYEAR_COHORT = AIController.GetSetting("score_c70_vyear_cohort") != 0', settings)
        self.assertIn('SCORE_C70_VYEAR_MEASURE_SHADOW = AIController.GetSetting("score_c70_vyear_measure_shadow") != 0', settings)
        self.assertIn('SCORE_C70_VYEAR_MEASURE = SCORE_C70_VYEAR_COHORT || SCORE_C70_VYEAR_MEASURE_SHADOW;', settings)
        self.assertEqual(policy_matrix(False, False), (False, False))
        self.assertEqual(policy_matrix(False, True), (False, True))
        self.assertEqual(policy_matrix(True, False), (True, True))
        self.assertEqual(policy_matrix(True, True), (True, True))
        self.assertEqual(policy_matrix(True, True, stable=True), (False, False))
        self.assertEqual(policy_matrix(True, True, full_save=False), (False, False))

    def test_all_capture_sites_follow_measure_flag_not_policy_flag(self):
        # The economic flag may be referenced only by the settings gate and
        # the single guarded publication assignment in OpexC70VYearRecomputeFactors.
        permitted = {"settings.nut", "globals_pre.nut", "projects_models.nut"}
        for file in AI.glob("*.nut"):
            data = file.read_text(encoding="utf-8")
            if "SCORE_C70_VYEAR_COHORT" in data:
                self.assertIn(file.name, permitted, file.name)
        sites = {
            "task_report.nut": (
                "if (!SCORE_C70_VYEAR_MEASURE || line == null",
                "if (SCORE_C70_VYEAR_MEASURE)\n      OpexC70VYearObserveLine",
                "if (SCORE_C70_VYEAR_MEASURE && C70_MODE_CALIBRATION)",
                "if (SCORE_C70_VYEAR_MEASURE && ownerLine != null)",
            ),
            "event_handlers.nut": (
                "if (line != null && SCORE_C70_VYEAR_MEASURE)",
                "SCORE_C70_COHORT_PROBE || SCORE_C70_VYEAR_MEASURE",
                "if (p4Found && SCORE_C70_VYEAR_MEASURE)",
            ),
            "air_fleet.nut": ("SCORE_C70_VYEAR_MEASURE && kept.len() != old.len()",),
            "task_rail.nut": ("if (SCORE_C70_VYEAR_MEASURE) OpexC70VYearMarkStructuralMutation",),
            "persist.nut": (
                "SCORE_C70_VYEAR_MEASURE ? OpexSaveProjectLineVYear",
                "local p4Adjust = SCORE_C70_VYEAR_MEASURE ? {} : null;",
                "if (SCORE_C70_VYEAR_MEASURE && this._reloadP4Adjust != null",
                "if (C70_MODE_CALIBRATION && SCORE_C70_VYEAR_MEASURE)",
            ),
        }
        for name, fragments in sites.items():
            with self.subTest(file=name):
                data = source(name)
                for fragment in fragments:
                    self.assertIn(fragment, data)

    def test_factor_computed_in_both_but_published_only_under_cohort(self):
        calc = function_body(source("projects_models.nut"), "OpexC70VYearRecomputeFactors")
        self.assertIn("local measuredK = (acc[0] + 2.0) / (acc[1] + 2).tofloat();", calc)
        self.assertIn("local legacyK = C70_MODE_FACTOR[mode];", calc)
        self.assertEqual(calc.count("C70_MODE_FACTOR[mode] = (SCORE_C70_VYEAR_COHORT ? effectiveK : legacyK);"), 1)
        self.assertIn("local effectiveK = acc[2] > 0 ? measuredK : legacyK;", calc)
        self.assertIn('" factor=" + effectiveK', calc)
        self.assertIn('" legacy_k=" + legacyK', calc)
        self.assertIn('" applied=" + (SCORE_C70_VYEAR_COHORT ? 1 : 0)', calc)
        for measured in (.4676, 1.0, 2.0):
            old = .91
            # Shadow returns the historical C70 factor and only reports the
            # candidate. Policy ON applies it, at the SAME report/Load point.
            self.assertEqual(old if not policy_matrix(False, True)[0] else measured, old)
            self.assertEqual(measured if policy_matrix(True, True)[0] else old, measured)

    def test_save_and_load_work_for_both_measure_arms_not_off(self):
        persistence = source("persist.nut")
        self.assertIn('cache[line] <- (SCORE_C70_VYEAR_MEASURE ?', persistence)
        self.assertIn('if (SCORE_C70_VYEAR_MEASURE)\n        projectedLines.append(OpexSaveProjectLineVYear(line));', persistence)
        self.assertIn('else\n        projectedLines.append(OpexSaveProjectLine(line));', persistence)
        self.assertIn('local p4Adjust = SCORE_C70_VYEAR_MEASURE ? {} : null;', persistence)
        self.assertIn('if (p4Adjust != null) saveObj.p4Adjust <- p4Adjust;', persistence)
        self.assertIn('if (SCORE_C70_VYEAR_MEASURE) {\n    foreach (line in this._lines)', persistence)
        self.assertIn('OpexC70VYearRecomputeFactors(this._lines, this._lastReportYear)', persistence)
        self.assertEqual(policy_matrix(False, False)[1], False)
        self.assertEqual(policy_matrix(False, True)[1], policy_matrix(True, True)[1])
        lines = []
        stale = {}
        for id_ in range(90):
            old = {"reportYear": 1971, "snapshot": [panel_entry(id_, 10, 22)],
                   "sumPm": 0, "count": 0, "valid": 0}
            now = model_report(old, year=1972,
                               current={id_: (10, 22, 2, 800, 100)}, n0=1, predicted=100)
            line = {"lineId": id_, "year": 1970, "predicted": 100,
                    "trains0": 1, "p4VYear": now}
            lines.append(line)
            stale[id_] = {**line, "p4VYear": old}
        for policy, collect in ((False, True), (True, True)):
            with self.subTest(policy=policy):
                self.assertEqual(policy_matrix(policy, collect)[1], True)
                projected, sidecar = saved_projection_and_sidecar(lines, stale)
                loaded = load_projection(projected, sidecar)
                self.assertEqual(loaded, lines)
                self.assertEqual(factor(loaded, 1972), factor(lines, 1972))

    def test_historical_save_project_line_byte_identical_and_calibration_core(self):
        for name, functions in (
            ("persist.nut", ("OpexSaveProjectLine",)),
            ("task_report.nut", ("OpexC70C82AccumulateLine", "OpexC70PublishModeFactors", "OpexC82PublishEngineFactors")),
            ("projects_models.nut", ("OpexC82RecomputeFactors",)),
        ):
            original = subprocess.check_output(
                ["git", "show", "c2a5be3:ai/OpexAI/" + name], cwd=ROOT).decode("utf-8")
            current = source(name)
            for func in functions:
                with self.subTest(file=name, function=func):
                    self.assertEqual(function_body(original, func), function_body(current, func))


if __name__ == "__main__":
    unittest.main()
