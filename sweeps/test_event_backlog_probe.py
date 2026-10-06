"""Contrat statique de la sonde probe_event_backlog (F-EVENT-BACKLOG-01)."""
import re
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
AI = ROOT / "ai" / "OpexAI"
INFO = AI / "info.nut"
SETTINGS = AI / "settings.nut"
GLOBALS = AI / "globals_pre.nut"
EVENTS = AI / "events.nut"
PERSIST = AI / "persist.nut"

from campaign_freeze import parse_ai_settings, parse_ai_setting_specs


class TestEventBacklogProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info_src = INFO.read_text(encoding="utf-8")
        cls.settings_src = SETTINGS.read_text(encoding="utf-8")
        cls.globals_src = GLOBALS.read_text(encoding="utf-8")
        cls.events_src = EVENTS.read_text(encoding="utf-8")
        cls.persist_src = PERSIST.read_text(encoding="utf-8")

    def test_setting_declaration_and_defaults(self):
        defaults = parse_ai_settings(INFO)
        specs = parse_ai_setting_specs(INFO)
        self.assertIn("probe_event_backlog", defaults)
        self.assertEqual(defaults["probe_event_backlog"], 0)
        self.assertTrue(specs["probe_event_backlog"]["boolean"])

        start = self.info_src.index('name = "probe_event_backlog"')
        block = self.info_src[start:self.info_src.index("});", start)]
        self.assertIn("0 = off (default)", block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 0", block)
        self.assertEqual(self.info_src.count('name = "probe_event_backlog"'), 1)

    def test_globals_declaration(self):
        self.assertIn("PROBE_EVENT_BACKLOG <- false;", self.globals_src)
        self.assertIn("EVENT_BACKLOG_CALLS <- 0;", self.globals_src)
        self.assertIn("EVENT_BACKLOG_EVENTS <- 0;", self.globals_src)
        self.assertIn("EVENT_BACKLOG_MAX_BURST <- 0;", self.globals_src)
        self.assertIn("EVENT_BACKLOG_OPS_TOTAL <- 0;", self.globals_src)
        self.assertIn("EVENT_BACKLOG_OPS_MAX <- 0;", self.globals_src)
        self.assertIn("EVENT_BACKLOG_MONTH <- -1;", self.globals_src)
        self.assertEqual(self.globals_src.count("PROBE_EVENT_BACKLOG <-"), 1)

    def test_settings_loading(self):
        needle = 'PROBE_EVENT_BACKLOG = AIController.GetSetting("probe_event_backlog") != 0;'
        self.assertIn(needle, self.settings_src)
        self.assertEqual(self.settings_src.count(needle), 1)
        self.assertNotIn("PROBE_EVENT_BACKLOG <-", self.settings_src)
        self.assertIn("if (PROBE_EVENT_BACKLOG) {", self.settings_src)

    def test_not_in_persistence(self):
        for token in (
            "probe_event_backlog",
            "PROBE_EVENT_BACKLOG",
            "EVENT_BACKLOG_CALLS",
            "EVENT_BACKLOG_EVENTS",
            "EVENT_BACKLOG_MAX_BURST",
            "EVENT_BACKLOG_OPS_TOTAL",
            "EVENT_BACKLOG_OPS_MAX",
            "EVENT_BACKLOG_MONTH",
        ):
            self.assertNotIn(token, self.persist_src)

    def test_single_dispatch_loop(self):
        """One dispatch loop: each handler call appears once in events.nut."""
        handlers = (
            "this._onVehicleCrashed(event);",
            "this._onVehicleAutoreplaced(event);",
            "this._onVehicleUnprofitable(event);",
            "this._onIndustryClose(event);",
            "this._onSubsidyOffer(event);",
            "this._onSubsidyOfferExpired(event);",
            "this._onSubsidyAwarded(event);",
            "this._onSubsidyExpired(event);",
            "this._onVehicleLost(event);",
            "this._onIndustryOpen(event);",
            "this._onTownFounded(event);",
            "this._onEngineAvailable(event);",
            "this._onStationFirstVehicle(event);",
        )
        for call in handlers:
            self.assertEqual(self.events_src.count(call), 1, call)
        self.assertEqual(
            self.events_src.count("while (AIEventController.IsEventWaiting())"), 1)
        self.assertEqual(self.events_src.count("AIEventController.GetNextEvent()"), 1)
        self.assertNotIn("if (!PROBE_EVENT_BACKLOG)", self.events_src)

        func_start = self.events_src.index("function OpexAI::_processEvents()")
        func_body = self.events_src[func_start:]
        self.assertIn("local backlog = PROBE_EVENT_BACKLOG;", func_body)
        self.assertEqual(func_body.count("while (AIEventController.IsEventWaiting())"), 1)
        self.assertIn("if (backlog) eventCount++;", func_body)

        begin = func_body.index("mark = OpexOpsMeasureBegin();")
        loop = func_body.index("while (AIEventController.IsEventWaiting())")
        end = func_body.index("local ops = OpexOpsMeasureEnd(mark);")
        self.assertLess(begin, loop)
        self.assertLess(loop, end)
        open_guard = func_body.rfind("if (backlog) {", 0, begin)
        self.assertGreaterEqual(open_guard, 0)
        self.assertLess(begin, func_body.find("\n  }", begin))
        self.assertLess(func_body.find("\n  }", begin), loop)
        close_guard = func_body.rfind("if (backlog) {", loop, end)
        self.assertGreaterEqual(close_guard, 0)
        # Measure, flush and the log stay inside the flag guards.
        self.assertNotIn("OpexOpsMeasureBegin", func_body[loop:close_guard])
        self.assertNotIn("OpexEventBacklogFlush", func_body[loop:close_guard])
        self.assertNotIn("AILog.Info", func_body[loop:close_guard])

    def test_probe_measurement_and_helpers(self):
        self.assertIn("function OpexEventBacklogDateText(date)", self.events_src)
        self.assertIn("function OpexEventBacklogFlush(curDate)", self.events_src)

        func_start = self.events_src.index("function OpexAI::_processEvents()")
        func_body = self.events_src[func_start:]
        self.assertIn("mark = OpexOpsMeasureBegin();", func_body)
        self.assertIn("local ops = OpexOpsMeasureEnd(mark);", func_body)
        self.assertIn("EVENT_BACKLOG_CALLS++;", func_body)
        self.assertIn("EVENT_BACKLOG_EVENTS += eventCount;", func_body)
        self.assertIn("EVENT_BACKLOG_MAX_BURST", func_body)
        self.assertIn("EVENT_BACKLOG_OPS_TOTAL += ops;", func_body)
        self.assertIn("EVENT_BACKLOG_OPS_MAX", func_body)

    def test_monthly_rollover_and_log_format(self):
        flush_start = self.events_src.index("function OpexEventBacklogFlush(curDate)")
        flush_block = self.events_src[flush_start:self.events_src.index("}", flush_start)]

        self.assertIn('AILog.Info("EVENT_BACKLOG date=" + dateText', flush_block)
        self.assertIn('calls=" + EVENT_BACKLOG_CALLS', flush_block)
        self.assertIn('events=" + EVENT_BACKLOG_EVENTS', flush_block)
        self.assertIn('max_burst=" + EVENT_BACKLOG_MAX_BURST', flush_block)
        self.assertIn('ops_total=" + EVENT_BACKLOG_OPS_TOTAL', flush_block)
        self.assertIn('ops_max=" + EVENT_BACKLOG_OPS_MAX', flush_block)

        # Regex contract of the log pattern
        sample_log = (
            "EVENT_BACKLOG date=1950-02-01 calls=74 events=12 max_burst=3 "
            "ops_total=14520 ops_max=3200"
        )
        pattern = re.compile(
            r"^EVENT_BACKLOG date=\d{4}-\d{2}-\d{2} calls=\d+ events=\d+ "
            r"max_burst=\d+ ops_total=\d+ ops_max=\d+$"
        )
        self.assertTrue(pattern.match(sample_log))

        # Check date formatter pads month and day to 2 digits
        date_func = self.events_src[
            self.events_src.index("function OpexEventBacklogDateText(date)"):
            self.events_src.index("function OpexEventBacklogFlush(curDate)")
        ]
        self.assertIn('month < 10 ? "0" + month : "" + month', date_func)
        self.assertIn('day < 10 ? "0" + day : "" + day', date_func)


if __name__ == "__main__":
    unittest.main()
