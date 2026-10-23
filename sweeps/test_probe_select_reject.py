from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
SELECTION = (ROOT / "ai" / "OpexAI" / "projects_selection.nut").read_text(encoding="utf-8")


class ProbeSelectRejectTests(unittest.TestCase):
    def test_setting_retired_in_favor_of_mask(self):
        self.assertEqual(INFO.count('name = "probe_select_reject"'), 0)
        self.assertEqual(INFO.count('name = "probes"'), 1)
        self.assertIn('max_value = 2147483647', INFO)

    def test_global_declared_in_globals_pre(self):
        self.assertIn("PROBE_SELECT_REJECT <- false;", GLOBALS)

    def test_probe_loaded_from_isolated_mask_bit(self):
        self.assertNotIn('GetSetting("probe_select_reject")', SETTINGS)
        self.assertIn('PROBE_SELECT_REJECT = OpexProbeEnabled(8192, 16);', SETTINGS)

    def test_helpers_present_in_projects_selection(self):
        self.assertIn("function OpexSelectRejectScore(project, kDec)", SELECTION)
        self.assertIn("function OpexSelectRejectLog(project, reason, affordable, scoreKey, kDec)", SELECTION)
        self.assertIn("function OpexSelectRejectLogTopK(dropped, best, limit)", SELECTION)

    def test_rejection_points_instrumented(self):
        # 1. Cash rejection
        self.assertIn('OpexSelectRejectLog(project, "cash", affordable, scoreKey, kDec)', SELECTION)
        # 2. Floor rejection
        self.assertIn('OpexSelectRejectLog(project, "floor", affordable, scoreKey, kDec)', SELECTION)
        # 3. Dedupe rejection removed with air_efficiency_dedupe
        self.assertNotIn("AIR_EFFICIENCY_DEDUPE", SELECTION)
        self.assertNotIn('OpexSelectRejectLog(prior, "dedupe", affordable, scoreKey, kDec)', SELECTION)
        self.assertNotIn('OpexSelectRejectLog(project, "dedupe", affordable, scoreKey, kDec)', SELECTION)
        # 4. Top-K truncation
        self.assertIn('OpexSelectRejectLogTopK(dropped, best, limit)', SELECTION)

    def test_probe_select_reject_format(self):
        self.assertIn('OpexDecide("SELECT_REJECT"', SELECTION)
        self.assertIn('"pair=" + pairStr + " type=" + typeStr + " reason=" + reason + " rank=" + rank + " score=" + score + " top=" + topScore', SELECTION)
        self.assertIn('"pair=" + pairStr + " type=" + typeStr + " reason=topk rank=" + limit + " score=" + score + " top=" + topScore', SELECTION)

    def test_probe_inactive_by_default(self):
        start = SELECTION.index("function OpexSelectRejectLog(")
        body = SELECTION[start:SELECTION.index("function OpexSelectRejectLogTopK(", start)]
        self.assertIn("if (!PROBE_SELECT_REJECT || project == null) return;", body)


if __name__ == "__main__":
    unittest.main()
