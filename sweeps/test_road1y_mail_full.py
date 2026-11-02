"""Contract tests for ROAD1Y child MAIL full load orders (road1y_mail_full).

Verifies:
- setting declared default 0 at all four difficulties (0..3);
- ROAD1Y_MAIL_FULL global declared default 0 in globals_pre.nut;
- ROAD1Y_MAIL_FULL read in OpexLoadSettings and OpexLoadBusDistrictSettings,
  clamped to 0..3 and forced to 0 outside road-only mode;
- bit 1 sets OF_FULL_LOAD_ANY at station A, bit 2 at station B for child MAIL vans;
- new child lines (OpexRoad1yBuildMailChild) apply bits to orders;
- existing shared orders (OpexRoad1yRefleetMailLine) updated when ROAD1Y_MAIL_FULL > 0;
- refleet fleet build (OpexRoadRefleet) sets bits on empty fleet mail_pax lines;
- PAX and freight lines untouched;
- Squirrel hazards check: no try/yield, no anonymous functions, no reserved word identifiers.
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


class TestRoad1yMailFull(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertEqual(info_src.count('name = "road1y_mail_full"'), 1)
        setting_block = info_src.split('name = "road1y_mail_full",')[1].split("});")[0]
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 3", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)

    def test_global_pre_declaration(self):
        self.assertIn("ROAD1Y_MAIL_FULL <- 0;", source("globals_pre.nut"))

    def test_settings_nut_loading(self):
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_mail_full")'), 2)
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn('GetSetting("road1y_mail_full")', path.read_text(encoding="utf-8"), path.name)
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn('ROAD1Y_MAIL_FULL = AIController.GetSetting("road1y_mail_full");', load_fn)
        self.assertIn("if (ROAD1Y_MAIL_FULL < 0 || ROAD1Y_MAIL_FULL > 3) ROAD1Y_MAIL_FULL = 0;", load_fn)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_MAIL_FULL = 0;", load_fn)
        defined = load_fn.index("local road1yRoadOnly =")
        self.assertLess(defined, load_fn.index('GetSetting("road1y_mail_full")'))

        loader = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertIn('ROAD1Y_MAIL_FULL = AIController.GetSetting("road1y_mail_full");', loader)
        self.assertIn("if (ROAD1Y_MAIL_FULL < 0 || ROAD1Y_MAIL_FULL > 3) ROAD1Y_MAIL_FULL = 0;", loader)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_MAIL_FULL = 0;", loader)
        self.assertLess(loader.index("local road1yRoadOnly ="), loader.index('GetSetting("road1y_mail_full")'))
        self.assertLess(
            loader.index("if (!road1yRoadOnly) ROAD1Y_MAIL_FULL = 0;"),
            loader.index('require("bus_districts_overrides.nut")'),
        )
        self.assertNotIn("road1y_mail_full", source("persist.nut"))
        self.assertNotIn("ROAD1Y_MAIL_FULL", source("persist.nut"))

    def test_build_mail_child_orders(self):
        code = body("bus_districts.nut", "OpexRoad1yBuildMailChild")
        self.assertIn("(ROAD1Y_MAIL_FULL & 1) != 0 ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE", code)
        self.assertIn("(ROAD1Y_MAIL_FULL & 2) != 0 ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE", code)
        self.assertIn("AIOrder.AppendOrder(first, siteA.tile, flagsA)", code)
        self.assertIn("AIOrder.AppendOrder(first, siteB.tile, flagsB)", code)

    def test_refleet_existing_orders_sync(self):
        code = body("bus_districts.nut", "OpexRoad1yRefleetMailLine")
        self.assertIn("if (ROAD1Y_MAIL_FULL > 0 && vehicles.len() > 0)", code)
        self.assertIn("AIOrder.SetOrderFlags(v, o, newFlags)", code)
        self.assertIn("if (AIVehicle.HasSharedOrders(v)) break;", code)
        # Verify sync happens before capacity/waiting check returns early
        sync_pos = code.index("ROAD1Y_MAIL_FULL > 0")
        cap_check = code.index("totalWaiting < capacity")
        self.assertLess(sync_pos, cap_check)

    def test_builder_road_refleet_empty_fleet(self):
        code = body("builder_road.nut", "OpexRoadRefleet")
        self.assertIn('line.kind == "mail_pax"', code)
        self.assertIn("(ROAD1Y_MAIL_FULL & 1) != 0 ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE", code)
        self.assertIn("(ROAD1Y_MAIL_FULL & 2) != 0 ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE", code)

    def test_pax_and_freight_untouched(self):
        build_route = body("builder_road.nut", "OpexBuildRoadRoute")
        self.assertNotIn("ROAD1Y_MAIL_FULL", build_route)
        self.assertNotIn("ROAD1Y_MAIL_FULL", source("candidates.nut"))
        self.assertNotIn("ROAD1Y_MAIL_FULL", source("projects_selection.nut"))
        self.assertNotIn("ROAD1Y_MAIL_FULL", source("projects_models.nut"))

    def test_squirrel_hazards_and_reserved_words(self):
        code = body("bus_districts.nut", "OpexRoad1yRefleetMailLine")
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
