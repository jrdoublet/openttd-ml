"""Source contracts for the experimental candidate ranking."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class HomogeneousPreselectContract(unittest.TestCase):
    def test_setting_default_and_dispatch(self):
        info = (ROOT / "info.nut").read_text()
        settings = (ROOT / "settings.nut").read_text()
        block = re.search(r'name = "homogeneous_preselect"[\s\S]*?flags = AICONFIG_BOOLEAN', info)
        self.assertIsNotNone(block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{level}_value = 0", block.group())
        self.assertIn('AIController.GetSetting("homogeneous_preselect") != 0', settings)
        self.assertIn('? OpexTopKFund : OpexTopKLegacy', settings)

    def test_paper_project_uses_selection_score(self):
        source = (ROOT / "candidates.nut").read_text()
        block = source.split('function OpexTopKFund(', 1)[1].split('\n}', 1)[0]
        for symbol in ('OpexProjectFromCandidate(candidate)',
                       'OpexProjectFinanceCapital(project)',
                       'OpexProjectScore(C70_PROFIT_CALIBRATED ? OpexCalibratedProfit(project) : project.profitAnnual'):
            self.assertIn(symbol, block)
        self.assertNotIn('turnoverBonus', block)
        self.assertNotIn('opcodeRatio', block)
        self.assertNotIn('candidate.ratio', block)

    def test_legacy_body_unchanged_by_dispatch(self):
        source = (ROOT / "candidates.nut").read_text()
        legacy = source.split('function OpexTopK(', 1)[1].split('\n}', 1)[0]
        self.assertIn('candidate.ratio <= floor', legacy)
        self.assertIn('best[pos - 1].ratio < candidate.ratio', legacy)
        self.assertIn('OpexTopKLegacy <- OpexTopK;', source)


if __name__ == "__main__":
    unittest.main()
