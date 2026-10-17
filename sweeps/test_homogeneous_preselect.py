"""Source contracts for the experimental candidate ranking."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class HomogeneousPreselectContract(unittest.TestCase):
    def test_setting_default_and_dispatch(self):
        info = (ROOT / "info.nut").read_text(encoding="utf-8")
        settings = (ROOT / "settings.nut").read_text(encoding="utf-8")
        self.assertNotIn('name = "homogeneous_preselect"', info)
        self.assertNotIn('homogeneous_preselect', settings)
        self.assertNotIn('OpexTopKFund', settings)
        self.assertNotIn('OpexTopKLegacy', settings)

    def test_retired_candidate_fund_symbols(self):
        source = (ROOT / "candidates.nut").read_text(encoding="utf-8")
        self.assertNotIn('function OpexTopKFund(', source)
        self.assertNotIn('OpexTopKLegacy <-', source)

    def test_legacy_body_unchanged(self):
        source = (ROOT / "candidates.nut").read_text(encoding="utf-8")
        legacy = source.split('function OpexTopK(', 1)[1].split('\n}', 1)[0]
        self.assertIn('candidate.ratio <= floor', legacy)
        self.assertIn('best[pos - 1].ratio < candidate.ratio', legacy)


if __name__ == "__main__":
    unittest.main()
