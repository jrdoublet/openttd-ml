"""Contract tests for ROAD1Y PAX distance floor (road1y_next).

Verifies:
- setting declared default 0 at all four difficulties (0..192);
- ROAD1Y_NEXT global declared default 0 in globals_pre.nut;
- ROAD1Y_NEXT read in OpexLoadSettings and OpexLoadBusDistrictSettings,
  clamped to 0..192 and forced to 0 outside road-only mode;
- the floor drops a new PAX pair in OpexRoad100SoloPaxCandidates only when
  ROAD1Y_NEXT > 0, before the quote and before fleet sizing;
- freight band generation is untouched;
- Squirrel hazards: no try/yield, no anonymous functions, no reserved locals.
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


class TestRoad1yNext(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertEqual(info_src.count('name = "road1y_next"'), 1)
        setting_block = info_src.split('name = "road1y_next",')[1].split("});")[0]
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 192", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)

    def test_global_pre_declaration(self):
        self.assertIn("ROAD1Y_NEXT <- 0;", source("globals_pre.nut"))

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_next")'), 2)
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn('GetSetting("road1y_next")', path.read_text(encoding="utf-8"), path.name)
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_NEXT = AIController.GetSetting("road1y_next");', load_fn)
        self.assertIn("if (ROAD1Y_NEXT < 0 || ROAD1Y_NEXT > 192) ROAD1Y_NEXT = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_NEXT = 0;", load_fn)
        defined = load_fn.index("local road1yRoadOnly =")
        self.assertLess(defined, load_fn.index('GetSetting("road1y_next")'))

        loader = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertIn('ROAD1Y_NEXT = AIController.GetSetting("road1y_next");', loader)
        self.assertIn("if (ROAD1Y_NEXT < 0 || ROAD1Y_NEXT > 192) ROAD1Y_NEXT = 0;", loader)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_NEXT = 0;", loader)
        self.assertLess(loader.index("local road1yRoadOnly ="), loader.index('GetSetting("road1y_next")'))
        self.assertLess(
            loader.index("if (!road1yRoadOnly) ROAD1Y_NEXT = 0;"),
            loader.index('require("bus_districts_overrides.nut")'),
        )
        self.assertNotIn("road1y_next", source("persist.nut"))
        self.assertNotIn("ROAD1Y_NEXT", source("persist.nut"))

    def test_pax_generator_floor(self):
        code = body("bus_districts_overrides.nut", "OpexRoad100SoloPaxCandidates")
        floor = "if (ROAD1Y_NEXT > 0 && distance < ROAD1Y_NEXT) continue;"
        self.assertEqual(code.count(floor), 1)
        self.assertLess(code.index("AIMap.DistanceManhattan(tileA, tileB)"), code.index(floor))
        self.assertLess(code.index(floor), code.index("OpexRoadDistanceAllowed("))
        self.assertLess(code.index(floor), code.index("OpexMakeRoadCandidate("))
        self.assertNotIn("ROAD1Y_NEXT", source("candidates.nut"))
        self.assertNotIn("ROAD1Y_NEXT", source("po01c_regen.nut"))
        self.assertNotIn("ROAD1Y_NEXT", source("projects_selection.nut"))
        self.assertNotIn("ROAD1Y_NEXT", source("projects_models.nut"))

    def test_squirrel_hazards_and_reserved_words(self):
        code = body("bus_districts_overrides.nut", "OpexRoad100SoloPaxCandidates")
        self.assertNotIn("yield", code)
        self.assertNotIn("function(", code)
        self.assertNotIn(".find(", code)
        reserved = ("clone", "base", "par", "parent", "static", "delegate", "resume", "vargc", "vargv")
        for word in reserved:
            self.assertIsNone(
                re.search(r"\blocal\s+" + word + r"\b", code),
                f"Reserved word '{word}' used as local variable",
            )


if __name__ == "__main__":
    unittest.main()
