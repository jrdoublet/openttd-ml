"""Contrats P3 : score AIR et éligibilité restent des objets séparés."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (ROOT / name).read_text(encoding="utf-8")


class P3ScoreContracts(unittest.TestCase):
    def test_off_all_difficulties_and_loaded(self):
        info, glob, settings = map(source, ("info.nut", "globals_pre.nut", "settings.nut"))
        for setting in ("score_air_buffer_separate", "score_air_buffer_shadow"):
            block = info.split(f'name = "{setting}"', 1)[1].split("});", 1)[0]
            for difficulty in ("easy", "medium", "hard", "custom"):
                self.assertRegex(block, rf"{difficulty}_value\s*=\s*0\b")
            self.assertIn(f'AIController.GetSetting("{setting}")', settings)
        self.assertIn("SCORE_AIR_BUFFER_SEPARATE <- false", glob)

    def test_no_finance_builder_or_persist_change(self):
        import subprocess
        # Ces modules ne sont pas modifiés par le patch du stage.
        changed = subprocess.check_output(["git", "diff", "--name-only"],
                                          cwd=ROOT.parents[1], text=True).splitlines()
        for forbidden in ("projects_finance.nut", "projects_builders.nut",
                          "builder_air.nut", "persist.nut", "air_catalog_c121.nut"):
            self.assertFalse(any(p.endswith("/" + forbidden) for p in changed), forbidden)

    def test_both_paths_keep_cash_guard_and_c77_tier(self):
        sel = source("projects_selection.nut")
        self.assertIn("if (financeCapital > capitalBudget)", sel)
        self.assertIn("if (financeCapital > capitalBudget) continue;", sel)
        self.assertEqual(sel.count("OpexProjectScoreCapital(project,\n"), 2)
        self.assertEqual(sel.count("OpexP3BufferShadowAdd(p3Shadow, project,"), 2)
        self.assertIn('OpexProjectInsertDefensive(state.base, copy, "p3Base", limit, AIR_EARLY_SLOT, true)', sel)
        self.assertIn('OpexProjectInsertDefensive(state.variant, copy, "p3Variant", limit, AIR_EARLY_SLOT, true)', sel)
        self.assertIn("OpexProjectDefensiveAirPriority(project)", sel)
        self.assertIn("local p3Shadow = (SCORE_AIR_BUFFER_SHADOW && realSelection)", sel)
        self.assertIn("if (SCORE_AIR_BUFFER_SEPARATE) {\n        local catalogDenom", sel)
        self.assertIn("catalogScore = OpexProjectScore(p3FundProfit, catalogDenom)", sel)
        self.assertIn(".lastScore = catalogScore", sel)

    def test_score_capital_preserves_decision_depth_and_immobilisation(self):
        model = source("projects_models.nut")
        pos = model.index("function OpexProjectScoreCapital(")
        body = model[pos:]
        self.assertIn("if (!separate", body)
        self.assertIn('project.mode != "air"', body)
        self.assertIn('"decisionConstructionCapital" in project', body)
        self.assertIn("OpexAirRequiredMargin(newAirports, plan)", body)
        self.assertIn("decisionFinanceCapital - margin", body)
        self.assertIn("scoreCapital < project.decisionConstructionCapital", body)

        def cap(finance, margin, construction, enabled):
            if not enabled or margin <= 0 or finance <= margin:
                return finance
            return max(finance - margin, construction)

        for margin in (2000, 12000, 30000):
            for immobilise in (0, 15000):
                finance = 100000 + margin + immobilise
                self.assertEqual(cap(finance, margin, 100000, True), 100000 + immobilise)
                self.assertEqual(cap(finance, margin, 100000, False), finance)
        # K_dec peut rendre le score identique dans les deux bras.
        self.assertEqual(max(150000, cap(130000, 30000, 100000, True)),
                         max(150000, cap(130000, 30000, 100000, False)))
        # L'abordabilité reste celle des 130k, et non des 100k de score.
        self.assertGreater(130000, 110000)


if __name__ == "__main__":
    unittest.main()
