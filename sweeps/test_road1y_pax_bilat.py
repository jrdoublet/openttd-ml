"""Static contracts only: these tests do not compile or execute Squirrel."""
import json
import re
import unittest
from pathlib import Path
from test_v261_forum_behaviours import body, source

ROOT = Path(__file__).resolve().parents[1]


class PaxBilatContracts(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        self.assertIn('ROAD1Y_PAX_BILAT <- 0;', source("globals_pre.nut"))
        info = source("info.nut")
        self.assertIn('name = "road1y_pax_bilat"', info)
        block = info.split('name = "road1y_pax_bilat",')[1].split("});")[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 0", block)
        self.assertIn("min_value = 0, max_value = 1", block)
        self.assertIn("flags = 0", block)

    def test_settings_nut_loading_in_both_loaders(self):
        for loader in ("OpexLoadSettings", "OpexLoadBusDistrictSettings"):
            code = body("settings.nut", loader)
            self.assertIn('AIController.GetSetting("road1y_pax_bilat")', code)
            self.assertIn("if (ROAD1Y_PAX_BILAT < 0) ROAD1Y_PAX_BILAT = 0;", code)
            self.assertIn("if (ROAD1Y_PAX_BILAT > 1) ROAD1Y_PAX_BILAT = 1;", code)
            self.assertIn("if (!road1yRoadOnly) ROAD1Y_PAX_BILAT = 0;", code)

    def test_refleet_formula_and_scope(self):
        code = body("bus_districts_overrides.nut", "OpexRoad1yRefleetSaved")
        # Freight uses waitingA
        self.assertIn('(("kind" in line) && line.kind == "freight") ? waitingA : totalWaiting;', code)
        # Pax bilat uses weakest terminus stock doubled
        self.assertIn("if (isPax && ROAD1Y_PAX_BILAT > 0)", code)
        self.assertIn("road1yWait = (waitingB < waitingA ? waitingB : waitingA) * 2;", code)

    def test_fixtures_match_live_sources(self):
        for path in (ROOT / "sweeps/fixtures").glob("road100_*_hunks.json"):
            for filename, hunks in json.loads(path.read_text()).items():
                for hunk in hunks:
                    if "ROAD1Y_PAX_BILAT" in hunk["after"] or "road1y_pax_bilat" in hunk["after"]:
                        self.assertEqual(source(filename).count(hunk["after"]), 1,
                                         (path.name, filename))

    def test_squirrel_reserved_words_and_hazards(self):
        for filename in ("bus_districts_overrides.nut", "globals_pre.nut", "settings.nut", "info.nut"):
            code = source(filename)
            for word in ("clone", "base", "parent", "static", "delegate", "vargc", "vargv", "resume", "yield"):
                self.assertNotRegex(code, r"\blocal\s+" + word + r"\b", f"Found local {word} in {filename}")
            self.assertNotIn("function(", code, f"Found anonymous function in {filename}")
            self.assertNotIn(".find(", code, f"Found array .find in {filename}")


if __name__ == "__main__":
    unittest.main()
