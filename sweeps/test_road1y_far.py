"""Contract tests for ROAD1Y long-distance bus pairs (road1y_far).

At 0 the knob is inactive and the execution path is strictly identical to master.
N>0 allows town-to-town PAX bus-district pairs up to 128 + N tiles, expands the
A* trace max length to 128 + N + 64, and scales the A* node search budget
proportionally to distance ((nodeBudget * dist) / 128).
Freight and MAIL lines are strictly untouched.
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


class TestRoad1yFar(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertEqual(info_src.count('name = "road1y_far"'), 1)
        setting_block = info_src.split('name = "road1y_far",')[1].split("});")[0]
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 96", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)
        self.assertNotIn("AICONFIG_BOOLEAN", setting_block)

    def test_global_pre_declaration(self):
        self.assertIn("ROAD1Y_FAR <- 0;", source("globals_pre.nut"))

    def test_settings_nut_loading_and_clamping(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_far")'), 2)
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn(
                'GetSetting("road1y_far")',
                path.read_text(encoding="utf-8"),
                path.name,
            )
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_FAR = AIController.GetSetting("road1y_far");', load_fn)
        self.assertIn("if (ROAD1Y_FAR < 0 || ROAD1Y_FAR > 96) ROAD1Y_FAR = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_FAR = 0;", load_fn)
        defined = load_fn.index("local road1yRoadOnly =")
        read_at = load_fn.index('GetSetting("road1y_far")')
        clamp_at = load_fn.index("if (ROAD1Y_FAR < 0 || ROAD1Y_FAR > 96) ROAD1Y_FAR = 0;")
        gate_at = load_fn.index("if (!road1yRoadOnly) ROAD1Y_FAR = 0;")
        self.assertLess(defined, read_at)
        self.assertLess(read_at, clamp_at)
        self.assertLess(clamp_at, gate_at)

        loader = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertIn('ROAD1Y_FAR = AIController.GetSetting("road1y_far");', loader)
        self.assertIn("if (ROAD1Y_FAR < 0 || ROAD1Y_FAR > 96) ROAD1Y_FAR = 0;", loader)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_FAR = 0;", loader)
        self.assertLess(loader.index("local road1yRoadOnly ="), loader.index('GetSetting("road1y_far")'))
        self.assertLess(
            loader.index("if (!road1yRoadOnly) ROAD1Y_FAR = 0;"),
            loader.index('require("bus_districts.nut")'),
        )
        self.assertNotIn("road1y_far", source("persist.nut"))
        self.assertNotIn("ROAD1Y_FAR", source("persist.nut"))

    def test_pax_bus_district_candidate_generation_filter(self):
        code = body("bus_districts_overrides.nut", "OpexRoad100SoloPaxCandidates")
        self.assertIn("local farAllowed = ROAD1Y_FAR > 0 && distance > 128 && distance <= (128 + ROAD1Y_FAR);", code)
        self.assertIn("if (!farAllowed && !OpexRoadDistanceAllowed(catalog, distance, stats)) continue;", code)
        self.assertIn("if (ROAD1Y_FAR > 0 && distance > (128 + ROAD1Y_FAR)) continue;", code)
        self.assertIn('if (DECISION_LOG && ROAD1Y_FAR > 0 && distance > 128)', code)
        self.assertIn('OpexDecide("ROAD1Y_FAR", "added=1 distance=" + distance', code)

    def test_astar_trace_length_and_proportional_budget(self):
        voirie = body("bus_districts_overrides.nut", "OpexRoadPlanPaxVoirie")
        self.assertIn("local astarMaxLen = ROAD_MAX_TRACE_TILES + 64;", voirie)
        self.assertIn("if (ROAD1Y_FAR > 0 && (128 + ROAD1Y_FAR + 64) > astarMaxLen)", voirie)
        self.assertIn("astarMaxLen = 128 + ROAD1Y_FAR + 64;", voirie)
        self.assertIn("trace = OpexRoad1yAStarTrace(siteA, siteB, astarMaxLen);", voirie)

        astar = body("road1y_astar.nut", "OpexRoad1yAStarTrace")
        self.assertIn("local dist = AIMap.DistanceManhattan(siteA.tile, siteB.tile);", astar)
        self.assertIn("if (ROAD1Y_FAR > 0 && dist > 128)", astar)
        self.assertIn("nodeBudget = (nodeBudget * dist) / 128;", astar)

    def test_freight_and_mail_untouched(self):
        cands = source("candidates.nut")
        self.assertNotIn("ROAD1Y_FAR", cands)
        # Verify mail generator has no reference to ROAD1Y_FAR
        mail_fn = body("candidates.nut", "OpexRoad100MailIntertownGenerator")
        self.assertNotIn("ROAD1Y_FAR", mail_fn)

    def test_squirrel_keywords_and_hazards(self):
        # Verify no reserved words used as identifiers in modified nut files
        files_to_check = [
            "globals_pre.nut",
            "settings.nut",
            "bus_districts_overrides.nut",
            "road1y_astar.nut",
        ]
        reserved = ["clone", "base", "parent", "static", "delegate", "vargc", "vargv", "resume", "constructor", "instanceof"]
        for fname in files_to_check:
            text = source(fname)
            # Remove comments and strings
            clean = re.sub(r'/\*[\s\S]*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"', ' ', text)
            for word in reserved:
                matches = re.findall(r'\b' + word + r'\b', clean)
                self.assertEqual(len(matches), 0, f"Found reserved keyword {word} in {fname}")


if __name__ == "__main__":
    unittest.main()
