"""R5 source contracts; full Load -> Start still requires OpenTTD."""
from pathlib import Path
import re
import unittest

AI = Path(__file__).resolve().parents[1] / "ai/OpexAI"


class TestReloadSelftests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (AI / "main.nut").read_text(encoding="utf-8")
        cls.persist = (AI / "persist.nut").read_text(encoding="utf-8")
        # R16 : les autotests vivent dans selftests.nut, requis par main.nut.
        assert 'require("selftests.nut");' in cls.main
        cls.source = ((AI / "orchestrator.nut").read_text(encoding="utf-8") + "\n"
                      + (AI / "selftests.nut").read_text(encoding="utf-8"))

    def body(self, name):
        body = self.source.split(f"function OpexAI::{name}()", 1)[1].split("\nfunction ", 1)[0]
        return re.sub(r"/\*.*?\*/|//[^\n]*", "", body, flags=re.S)

    def assert_reload_guard_first(self, name, prefix):
        body = self.body(name)
        self.assertRegex(body, r'^\s*\{\s*if \(this\._loadedFromSave\)\s*\{\s*'
                         + rf'AILog.Info\("{prefix} selftest skipped: loaded game"\);\s*return true;\s*\}}')
        return body

    def test_c80_guard_precedes_enqueue_and_worker_replacement(self):
        body = self.assert_reload_guard_first("_c80RunSelfTest", "C80")
        self.assertLess(body.index("return true;"), body.index("this._enqueueReactive("))
        self.assertLess(body.index("return true;"), body.index("this._activeWorker ="))

    def test_c76_guard_precedes_revision_reset_and_queue_clear(self):
        body = self.assert_reload_guard_first("_c76RunSelfTest", "C76")
        self.assertLess(body.index("return true;"), body.index("this._c76SaveRevisions()"))
        self.assertLess(body.index("return true;"), body.index("this._clearReactiveQueue()"))

    def test_reload_flag_is_set_before_null_or_legacy_data_exit(self):
        load = self.persist.split("function OpexAI::Load(", 1)[1].split("\nfunction ", 1)[0]
        self.assertLess(load.index("this._loadedFromSave = true;"), load.index("if (data == null) return;"))
        self.assertIn("_loadedFromSave = false;", self.main)

    def test_start_keeps_settings_then_reconciliation_then_both_tests(self):
        start = self.main.split("function OpexAI::Start()", 1)[1]
        self.assertLess(start.index("OpexLoadSettings();"), start.index("this._reconcileAfterLoad();"))
        for name in ("_c80RunSelfTest", "_c76RunSelfTest"):
            self.assertLess(start.index("this._reconcileAfterLoad();"), start.index(f"this.{name}();"))
        self.assertNotIn("this._loadedFromSave = false", start)

    def test_queue_and_worker_restore_remain_independent_of_test_guards(self):
        self.assertIn("this._reactiveQueue = OpexLoadReactiveQueue(data.c80ReactiveQueue);", self.persist)
        self.assertIn("this._activeWorker = OpexLoadActiveWorker(data.c80ActiveWorker);", self.persist)
        self.assertIn('this._activeWorker.kind == "regen_candidates"', self.persist)
        self.assertIn("this._activeWorker.ai <- this;", self.persist)
        for name in ("_c80RunSelfTest", "_c76RunSelfTest"):
            guard = self.body(name).split("return true;", 1)[0]
            self.assertNotIn("_reactiveQueue", guard)
            self.assertNotIn("_activeWorker", guard)

    def test_new_game_tests_are_retained_and_skips_are_not_logged_as_passes(self):
        for name, prefix in (("_c80RunSelfTest", "C80"), ("_c76RunSelfTest", "C76")):
            body = self.body(name)
            self.assertIn(f'{prefix} selftest ok', body)
            self.assertIn(f'{prefix} selftest FAIL', body)
            self.assertNotIn("selftest ok", body.split("return true;", 1)[0])


if __name__ == "__main__":
    unittest.main()