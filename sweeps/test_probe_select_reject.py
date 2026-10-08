from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
SELECTION = (ROOT / "ai" / "OpexAI" / "projects_selection.nut").read_text(encoding="utf-8")


class ProbeSelectRejectTests(unittest.TestCase):
    def test_setting_declared_in_info_nut_with_all_zero_values(self):
        self.assertEqual(INFO.count('name = "probe_select_reject"'), 1)
        start = INFO.index('name = "probe_select_reject"')
        block = INFO[start:INFO.index("});", start)]
        for token in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(token, block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)

    def test_global_declared_in_globals_pre(self):
        self.assertIn("PROBE_SELECT_REJECT <- false;", GLOBALS)

    def test_setting_loaded_once_in_settings_nut(self):
        self.assertEqual(SETTINGS.count('AIController.GetSetting("probe_select_reject")'), 1)
        self.assertIn('PROBE_SELECT_REJECT = AIController.GetSetting("probe_select_reject") != 0;', SETTINGS)

    def test_helpers_present_in_projects_selection(self):
        self.assertIn("function OpexSelectRejectScore(project, kDec)", SELECTION)
        self.assertIn("function OpexSelectRejectLog(project, reason, affordable, scoreKey, kDec)", SELECTION)
        self.assertIn("function OpexSelectRejectLogTopK(dropped, best, limit)", SELECTION)

    def test_rejection_points_instrumented(self):
        # 1. Cash rejection
        self.assertIn('OpexSelectRejectLog(project, "cash", affordable, scoreKey, kDec)', SELECTION)
        # 2. Floor rejection
        self.assertIn('OpexSelectRejectLog(project, "floor", affordable, scoreKey, kDec)', SELECTION)
        # 3. Dedupe rejection
        self.assertIn('OpexSelectRejectLog(prior, "dedupe", affordable, scoreKey, kDec)', SELECTION)
        self.assertIn('OpexSelectRejectLog(project, "dedupe", affordable, scoreKey, kDec)', SELECTION)
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
