"""ROAD1Y : contrat de road1y_gap (fourgons MAIL, defaut 0).

A 0 le plafond reste 2 * quais et OpexRoad1yMailStep tente un seul parent.
Hors route seule le chargement force 0. N>2 leve le plafond a N et, des
que N>0, saute un parent sans site MAIL (au plus 4 essais, un succes).
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

GAP_BRANCH = (
    "  if (ROAD1Y_GAP > 0) {\n"
    "    OpexRoad1yMailStepGap(ai, cashReserve, activeParents, activePairs, ym);\n"
    "    return;\n"
    "  }\n"
    "  local bestParent = null;"
)


class TestRoad1yGap(unittest.TestCase):
    def test_setting_defaults_to_zero_and_bounds_are_zero_to_thirty(self):
        info = source("info.nut")
        self.assertEqual(info.count('name = "road1y_gap"'), 1)
        block = info.split('name = "road1y_gap",')[1].split("});")[0]
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 30", block)
        self.assertIn("flags = 0", block)
        self.assertNotIn("AICONFIG_BOOLEAN", block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{difficulty}_value = 0", block)
        self.assertIn("ROAD1Y_GAP <- 0;", source("globals_pre.nut"))

    def test_loaded_once_clamped_and_forced_off_outside_road_only(self):
        settings = source("settings.nut")
        self.assertEqual(settings.count('GetSetting("road1y_gap")'), 1)
        load = body("settings.nut", "OpexLoadSettings")
        self.assertIn(
            "local road1yRoadOnly = MODE_ROAD && !MODE_AIR && !MODE_RAIL && !MODE_WATER;",
            load,
        )
        self.assertIn('ROAD1Y_GAP = AIController.GetSetting("road1y_gap");', load)
        self.assertIn("if (ROAD1Y_GAP < 0 || ROAD1Y_GAP > 30) ROAD1Y_GAP = 0;", load)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_GAP = 0;", load)
        defined = load.index("local road1yRoadOnly =")
        read_at = load.index('GetSetting("road1y_gap")')
        clamp_at = load.index("if (ROAD1Y_GAP < 0 || ROAD1Y_GAP > 30) ROAD1Y_GAP = 0;")
        gate_at = load.index("if (!road1yRoadOnly) ROAD1Y_GAP = 0;")
        self.assertLess(defined, read_at)
        self.assertLess(read_at, clamp_at)
        self.assertLess(clamp_at, gate_at)
        bus = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertNotIn("road1y_gap", bus)
        self.assertNotIn("ROAD1Y_GAP", bus)
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn('GetSetting("road1y_gap")', path.read_text(encoding="utf-8"), path.name)
        self.assertNotIn("road1y_gap", source("persist.nut"))
        self.assertNotIn("ROAD1Y_GAP", source("persist.nut"))

    def test_zero_keeps_historical_cap_and_single_parent(self):
        refleet = body("bus_districts.nut", "OpexRoad1yRefleetMailLine")
        cap_at = refleet.index("local mailCap = 2 * stops;")
        raise_at = refleet.index("if (ROAD1Y_GAP > mailCap) mailCap = ROAD1Y_GAP;")
        want_at = refleet.index("if (want > 2) want = 2;")
        self.assertLess(cap_at, raise_at)
        self.assertLess(raise_at, want_at)
        self.assertIn(
            "local cashReserve = (ROAD1Y_FLEET_UNLOCK & 2) != 0 ? 10000 : (ROAD1Y_PAX_REFLEET ? 15000 : 25000);",
            refleet,
        )
        step = body("bus_districts.nut", "OpexRoad1yMailStep")
        self.assertEqual(step.count(GAP_BRANCH), 1)
        self.assertLess(step.index(GAP_BRANCH), step.index("local bestParent = null;"))
        self.assertIn("OpexRoad1yBuildMailChild(ai, bestParent, cashReserve);", step)
        self.assertIn(
            "local cashReserve = (ROAD1Y_FLEET_UNLOCK & 2) != 0 ? 10000 : (ROAD1Y_PAX_REFLEET ? 15000 : 25000);",
            step,
        )
        build = body("bus_districts.nut", "OpexRoad1yBuildMailChild")
        self.assertIn(
            "local wantVans = (mailVol >= 2 * refitCap\n"
            "      && AICompany.GetBankBalance(AICompany.COMPANY_SELF) >= cashReserve + 2 * engine.price\n"
            "      && OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, 2)) ? 2 : 1;",
            build,
        )

    def test_positive_raises_cap_skips_unsitable_parent_and_stops_at_four(self):
        gap = body("bus_districts.nut", "OpexRoad1yMailStepGap")
        self.assertIn("while (attempts < 4)", gap)
        self.assertIn(
            'if (("road1yMailNoSite" in line) && line.road1yMailNoSite != 0) continue;',
            gap,
        )
        self.assertIn("if (OpexRoad1yBuildMailChild(ai, bestLine, cashReserve)) return;", gap)
        self.assertIn("bestLine.road1yMailTryMonth <- ym;", gap)
        self.assertLess(
            gap.index("bestLine.road1yMailTryMonth <- ym;"),
            gap.index("if (OpexRoad1yBuildMailChild(ai, bestLine, cashReserve)) return;"),
        )
        joined = "\n".join(path.read_text(encoding="utf-8") for path in AI.glob("*.nut"))
        self.assertEqual(joined.count("function OpexRoad1yMailStepGap("), 1)
        self.assertEqual(joined.count("OpexRoad1yMailStepGap("), 2)
        self.assertEqual(joined.count("function OpexRoad1yBuildMailChild("), 1)
        self.assertEqual(joined.count("parentLine.road1yMailNoSite <- 1;"), 1)
        build = body("bus_districts.nut", "OpexRoad1yBuildMailChild")
        null_at = build.index("if (siteA == null || siteB == null)")
        flag_at = build.index("if (ROAD1Y_GAP > 0) parentLine.road1yMailNoSite <- 1;")
        log_at = build.index('reason=" + (siteA == null ? "NO_SITE_A" : "NO_SITE_B")')
        self.assertLess(null_at, flag_at)
        self.assertLess(flag_at, log_at)
        for word in ("clone", "base", "par", "parent", "static"):
            self.assertNotRegex(gap, r"\blocal\s+" + word + r"\b", word)
        self.assertNotIn("function(", gap)
        self.assertNotIn(".find(", gap)
        self.assertNotIn("yield", gap)
        for called in ("OpexLineVehicleIds", "OpexRoad1yBuildMailChild"):
            self.assertIn("function " + called + "(", joined)


if __name__ == "__main__":
    unittest.main()
