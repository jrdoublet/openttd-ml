"""ROAD1Y-K : contrat de road1y_astar (A* routier, defaut 0).

Le budget est en milliers de noeuds, borne 0..16. Hors route seule le
chargement force 0. OpexRoad1yAStarTrace n'est appele que pour une paire
road1yBusSite, et seulement apres l'echec du BFS puis du L.
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

ASTAR_IF = (
    "if ((trace == null || depot == null) && ROAD1Y_ASTAR > 0\n"
    "        && (\"road1yBusSite\" in candidate) && nAStar == 0) {"
)


def _balanced_block(text, open_at):
    """Bloc { ... } dont l'accolade ouvrante est open_at."""
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_at:i + 1]
    raise AssertionError("accolade non fermee")


class TestRoad1yAstar(unittest.TestCase):
    def test_setting_defaults_to_zero_and_bounds_are_zero_to_sixteen(self):
        info = source("info.nut")
        self.assertEqual(info.count('name = "road1y_astar"'), 1)
        block = info.split('name = "road1y_astar",')[1].split("});")[0]
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 16", block)
        self.assertIn("flags = 0", block)
        self.assertNotIn("AICONFIG_BOOLEAN", block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{difficulty}_value = 0", block)
            self.assertNotIn(f"{difficulty}_value = 1", block)
        self.assertIn("ROAD1Y_ASTAR <- 0;", source("globals_pre.nut"))

    def test_loaded_once_clamped_and_forced_off_outside_road_only(self):
        settings = source("settings.nut")
        self.assertEqual(settings.count('GetSetting("road1y_astar")'), 1)
        load = body("settings.nut", "OpexLoadSettings")
        self.assertIn(
            "local road1yRoadOnly = MODE_ROAD && !MODE_AIR && !MODE_RAIL && !MODE_WATER;",
            load,
        )
        self.assertIn('ROAD1Y_ASTAR = AIController.GetSetting("road1y_astar");', load)
        self.assertIn("if (ROAD1Y_ASTAR < 0 || ROAD1Y_ASTAR > 16) ROAD1Y_ASTAR = 0;", load)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_ASTAR = 0;", load)
        defined = load.index("local road1yRoadOnly =")
        read_at = load.index('GetSetting("road1y_astar")')
        clamp_at = load.index("if (ROAD1Y_ASTAR < 0 || ROAD1Y_ASTAR > 16) ROAD1Y_ASTAR = 0;")
        gate_at = load.index("if (!road1yRoadOnly) ROAD1Y_ASTAR = 0;")
        self.assertLess(defined, read_at)
        self.assertLess(read_at, clamp_at)
        self.assertLess(clamp_at, gate_at)
        bus = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertNotIn("road1y_astar", bus)
        self.assertNotIn("ROAD1Y_ASTAR", bus)
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn('GetSetting("road1y_astar")', path.read_text(encoding="utf-8"), path.name)
        self.assertNotIn("road1y_astar", source("persist.nut"))
        self.assertNotIn("ROAD1Y_ASTAR", source("persist.nut"))

    def test_astar_runs_only_for_bus_site_after_bfs_and_l_fail(self):
        plan = body("bus_districts_overrides.nut", "OpexRoadPlanPaxVoirie")
        self.assertEqual(plan.count("OpexRoad1yAStarTrace("), 1)
        self.assertEqual(plan.count(ASTAR_IF), 1)
        self.assertIn("local nAStar = 0;", plan)
        bfs_at = plan.index("OpexRoadBfsPath(")
        l_at = plan.index("OpexRoadTrace(")
        if_at = plan.index(ASTAR_IF)
        call_at = plan.index("OpexRoad1yAStarTrace(")
        give_up = plan.index("if (trace == null || depot == null) continue;")
        self.assertLess(bfs_at, l_at)
        self.assertLess(l_at, if_at)
        self.assertLess(if_at, call_at)
        self.assertLess(call_at, give_up)
        block = _balanced_block(plan, plan.index("{", if_at))
        self.assertIn("OpexRoad1yAStarTrace(", block)
        self.assertIn("nAStar++;", block)
        self.assertIn('if (depot != null) via = "ASTAR";', block)
        joined = "\n".join(path.read_text(encoding="utf-8") for path in AI.glob("*.nut"))
        self.assertEqual(joined.count("OpexRoad1yAStarTrace("), 2)
        self.assertIn("function OpexRoad1yAStarTrace(", source("road1y_astar.nut"))
        self.assertNotIn("OpexRoad1yAStarTrace(", source("builder_road.nut"))
        main = source("main.nut")
        self.assertEqual(main.count('require("road1y_astar.nut");'), 1)
        self.assertLess(main.index('require("builder_road.nut");'), main.index('require("road1y_astar.nut");'))
        self.assertLess(main.index('require("road1y_astar.nut");'), main.index('require("opcode_exact.nut");'))

    def test_new_module_avoids_squirrel_hazards(self):
        code = source("road1y_astar.nut")
        for word in ("clone", "base", "parent", "static", "delegate",
                     "vargc", "vargv", "resume", "yield", "constructor", "instanceof"):
            self.assertNotRegex(code, r"\blocal\s+" + word + r"\b", word)
        self.assertNotIn("function(", code)
        self.assertNotIn(".find(", code)
        for block in re.findall(r"try\s*\{[^}]*\}", code, re.DOTALL):
            self.assertNotIn("yield", block)


if __name__ == "__main__":
    unittest.main()
