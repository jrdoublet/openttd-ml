"""Contract tests for ROAD1Y same-slot portfolio retry (road1y_retry).

At 0 the new compares are false: the k_pass break, the road walk and the
plan-failure return stay on the historical path. N>0, road-only, retries
other portfolio projects after a PAX road plan failure TRACEX/BUDGET/SITE_LOST.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from test_v261_forum_behaviours import body, source

AI = ROOT / "ai" / "OpexAI"

REASON_ARM = (
    '&& (ROAD1Y_RETRY_REASON == "TRACEX" || ROAD1Y_RETRY_REASON == "BUDGET"\n'
    '                || ROAD1Y_RETRY_REASON == "SITE_LOST"))'
)
CALLED = (
    "OpexAvailableCapital",
    "OpexReselectProjects",
    "OpexC69AttemptKey",
    "OpexCandidateIsAbandoned",
    "_tryBuildRoadProject",
    "_recordPortfolioProjectBuilt",
    "OpexSpanEvent",
)


class TestRoad1yRetry(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertEqual(info_src.count('name = "road1y_retry"'), 1)
        setting_block = info_src.split('name = "road1y_retry",')[1].split("});")[0]
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 8", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)
        self.assertNotIn("AICONFIG_BOOLEAN", setting_block)

    def test_global_pre_declaration(self):
        globals_src = source("globals_pre.nut")
        self.assertIn("ROAD1Y_RETRY <- 0;", globals_src)
        self.assertIn("ROAD1Y_RETRY_LEFT <- 0;", globals_src)
        self.assertIn("ROAD1Y_RETRY_ARMED <- false;", globals_src)
        self.assertIn('ROAD1Y_RETRY_REASON <- "";', globals_src)

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_retry")'), 2)
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn(
                'GetSetting("road1y_retry")',
                path.read_text(encoding="utf-8"),
                path.name,
            )
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_RETRY = AIController.GetSetting("road1y_retry");', load_fn)
        self.assertIn("if (ROAD1Y_RETRY < 0 || ROAD1Y_RETRY > 8) ROAD1Y_RETRY = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_RETRY = 0;", load_fn)
        defined = load_fn.index("local road1yRoadOnly =")
        read_at = load_fn.index('GetSetting("road1y_retry")')
        clamp_at = load_fn.index("if (ROAD1Y_RETRY < 0 || ROAD1Y_RETRY > 8) ROAD1Y_RETRY = 0;")
        gate_at = load_fn.index("if (!road1yRoadOnly) ROAD1Y_RETRY = 0;")
        self.assertLess(defined, read_at)
        self.assertLess(read_at, clamp_at)
        self.assertLess(clamp_at, gate_at)
        self.assertLess(load_fn.index("if (!road1yRoadOnly) ROAD1Y_MAIL2 = 0;"), read_at)

        loader = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertIn('ROAD1Y_RETRY = AIController.GetSetting("road1y_retry");', loader)
        self.assertIn("if (ROAD1Y_RETRY < 0 || ROAD1Y_RETRY > 8) ROAD1Y_RETRY = 0;", loader)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_RETRY = 0;", loader)
        self.assertLess(loader.index("local road1yRoadOnly ="), loader.index('GetSetting("road1y_retry")'))
        self.assertLess(
            loader.index("if (!road1yRoadOnly) ROAD1Y_MAIL2 = 0;"),
            loader.index('GetSetting("road1y_retry")'),
        )
        self.assertLess(
            loader.index("if (!road1yRoadOnly) ROAD1Y_RETRY = 0;"),
            loader.index('require("bus_districts.nut")'),
        )
        self.assertNotIn("road1y_retry", source("persist.nut"))
        self.assertNotIn("ROAD1Y_RETRY", source("persist.nut"))

    def test_zero_compare_does_not_replace_the_historical_break(self):
        projects = source("task_projects.nut")
        self.assertIn("function OpexAI::_road1yRetrySameSlot(", projects)
        self.assertEqual(projects.count("function OpexAI::_road1yRetrySameSlot("), 1)
        loop = body("task_projects.nut", "OpexAI::_tryBuildProjects")
        self.assertIn("if (ROAD1Y_RETRY > 0) {\n    ROAD1Y_RETRY_LEFT = 0;", loop)
        self.assertIn(
            "if (ROAD1Y_RETRY > 0 && ROAD1Y_RETRY_LEFT > 0\n"
            '                && project.mode == "road" && ("kind" in project) && project.kind == "pax")',
            loop,
        )
        self.assertLess(
            loop.index("if (ROAD1Y_RETRY > 0 && ROAD1Y_RETRY_LEFT > 0"),
            loop.index('c75StopReason = (availCap >= 0 && projCap > availCap) ? "cash" : "k_pass";'),
        )
        self.assertIn(REASON_ARM, loop)
        self.assertIn("this._road1yRetrySameSlot(", loop)
        self.assertLess(
            loop.index("ROAD1Y_RETRY_TRIED <= ROAD1Y_RETRY"),
            loop.index("this._road1yRetrySameSlot("),
        )
        helper = body("task_projects.nut", "OpexAI::_road1yRetrySameSlot")
        for name in CALLED:
            self.assertIn(name, helper, name)
            self.assertTrue(
                re.search(r"function\s+" + re.escape(name) + r"\b", source_all())
                or re.search(r"function\s+OpexAI::" + re.escape(name) + r"\b", source_all()),
                name,
            )
        for code in (helper, loop):
            self.assertNotIn("function(", code)
            self.assertNotIn(".find(", code)
            self.assertNotIn("yield", code)
            for word in ("clone", "base", "parent", "static", "delegate", "resume", "vargc", "vargv"):
                self.assertIsNone(re.search(r"\blocal\s+" + word + r"\b", code), word)

    def test_plan_failure_records_reason_only_when_retry_is_on(self):
        needle = (
            "if (ROAD1Y_RETRY > 0 && candidate.kind == \"pax\")\n"
            "          ROAD1Y_RETRY_REASON = planning.reason;"
        )
        # Chemin vivant : l'override remplace _tryBuildRoadProject quand
        # ROAD1Y_PAX_SITES est arme. task_road.nut reste le corps epingle.
        self.assertNotIn(needle, source("task_road.nut"))
        src = source("bus_districts_overrides.nut")
        self.assertEqual(src.count(needle), 1)
        fn = body("bus_districts_overrides.nut", "OpexAI::_tryBuildRoadProject")
        self.assertLess(fn.index("if (plan == null)"), fn.index(needle))
        self.assertLess(fn.index(needle), fn.index('OpexSign(anchor, "RA|"'))


def source_all():
    return "\n".join(path.read_text(encoding="utf-8") for path in AI.glob("*.nut"))


if __name__ == "__main__":
    unittest.main()
