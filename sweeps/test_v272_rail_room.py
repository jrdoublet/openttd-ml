#!/usr/bin/env python3
"""V272 : place de croissance des lignes rail fret (quai plus long, V270 plusieurs fois par an ; defaut 0)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_setting_specs  # noqa: E402


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


class TestV272RailRoom(unittest.TestCase):
    def test_setting_inert_by_default(self):
        spec = parse_ai_setting_specs(AI / "info.nut")["v272_rail_room"]
        self.assertEqual(spec["default"], 0)
        self.assertEqual((spec["min_value"], spec["max_value"]), (0, 12))
        self.assertIn("V272_RAIL_ROOM <- 0;", _read("globals_pre.nut"))
        self.assertEqual(_read("settings.nut").count('GetSetting("v272_rail_room")'), 1)

    def test_platform_margin_freight_only_and_capped(self):
        eco = _read("economy.nut")
        self.assertIn('} else if (V272_RAIL_ROOM > 0 && kind == "freight") {', eco)
        self.assertIn("catalog.maxTrainLength < roomMaximum", eco)
        self.assertIn("OpexRailWantedPlatformLength(wagons + wagons2, roomMaximum, V272_RAIL_ROOM)", eco)
        # Chemin par defaut inchange.
        self.assertIn("platformLength = OpexRailWantedPlatformLength(wagons + wagons2, catalog.platformLength);", eco)
        self.assertIn("function OpexRailWantedPlatformLength(targetWagons, gameMaximum, margin = RAIL_PLATFORM_GROWTH_WAGONS)",
                      _read("catalog.nut"))

    def test_v270_quota(self):
        rail = _read("task_rail.nut")
        self.assertIn("(V272_RAIL_ROOM <= 0 || !(\"v272Count\" in line) || line.v272Count >= line.v272Quota)) continue;", rail)
        self.assertIn("if (quota > V272_MAX_WAGONS_PER_YEAR) quota = V272_MAX_WAGONS_PER_YEAR;", rail)
        self.assertIn("const V272_MAX_WAGONS_PER_YEAR = 4;", _read("globals_pre.nut"))


if __name__ == "__main__":
    unittest.main()
