"""Static execution contracts for E1; engine scenarios remain a separate check."""
import re
import unittest
from test_v233_contracts import AI


class PendingContracts(unittest.TestCase):
    def test_default_off_at_all_difficulties_and_loaded(self):
        info = (AI / "info.nut").read_text()
        block = info.split('name = "v233_pending_continue"', 1)[1].split('});', 1)[0]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{level}_value = 0", block)
        self.assertIn('V233_PENDING_CONTINUE <- false;', (AI / "globals_pre.nut").read_text())
        self.assertIn('GetSetting("v233_pending_continue")', (AI / "settings.nut").read_text())

    def test_both_pending_branches_continue_before_any_stop(self):
        text = (AI / "task_projects.nut").read_text()
        branches = text.split('if (attempt.outcome == "pending") {')[1:]
        self.assertEqual(len(branches), 2)
        for branch in branches:
            guarded = branch.split('if (DECISION_LOG) OpexDecide("V233_SEARCH", "state=pending', 1)[0]
            self.assertIn('if (V233_PENDING_CONTINUE)', guarded)
            self.assertIn('continue;', guarded)
            self.assertNotIn('builtCount++', guarded)
            self.assertNotIn('c75BypassConsumed = true', guarded)

    def test_bypass_commits_only_in_five_success_branches(self):
        text = (AI / "task_projects.nut").read_text()
        self.assertEqual(text.count('if (V233_PENDING_CONTINUE && v233Bypass != null)'), 5)
        self.assertEqual(len(re.findall(
            r'if \(attempt.outcome == "built"\) \{[\s\S]*?'
            r'if \(V233_PENDING_CONTINUE && v233Bypass != null\)', text)), 5)
        provisional = text.split('if (!c75BypassConsumed) {', 1)[1].split('if (!c75BypassThisProject)', 1)[0]
        self.assertIn('v233Bypass = {', provisional)
        self.assertIn('} else {\n              c75BypassConsumed = true;', provisional)

    def test_busy_slot_is_rejected_before_kpass(self):
        text = (AI / "task_projects.nut").read_text()
        slot = text.index('if (V233_PENDING_CONTINUE && project.mode == "rail"')
        kpass = text.index('local c121ChainAttempt = false;')
        self.assertLess(slot, kpass)
        reject = re.search(r'if \(!prepared && !graftReady\)\s*\{([^{}]*)\}', text)
        self.assertIsNotNone(reject)
        self.assertIn('continue;', reject.group(1))
        self.assertLess(slot, reject.start())
        self.assertLess(reject.end(), kpass)

    def test_dates_and_attempts(self):
        text = (AI / "task_projects.nut").read_text()
        self.assertIn('if (!V233_PENDING_CONTINUE) OpexC75RecordPassDate(now);', text)
        self.assertIn('if (builtCount > 0) {\n    if (V233_PENDING_CONTINUE) OpexC75RecordPassDate', text)
        self.assertIn('if (attemptKey in v233Attempts) continue;', text)
        self.assertLess(text.index('v233Attempts[attemptKey] <- true;'),
                        text.index('local attempt = this._tryBuildFleetProject'))


if __name__ == "__main__":
    unittest.main()
