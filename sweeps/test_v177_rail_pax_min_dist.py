#!/usr/bin/env python3
"""V177 : distance minimale des candidats passagers rail (filtre de generation, defaut 0)."""
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


class V177(unittest.TestCase):
    def test_setting(self):
        spec = parse_ai_setting_specs(AI / "info.nut")["v177_rail_pax_min_dist"]
        self.assertEqual(spec["default"], 0)
        self.assertEqual((spec["min_value"], spec["max_value"]), (0, 512))

    def test_loaded_once(self):
        self.assertIn("V177_RAIL_PAX_MIN_DIST <- 0;", _read("globals_pre.nut"))
        self.assertEqual(_read("settings.nut").count('GetSetting("v177_rail_pax_min_dist")'), 1)

    def test_filter_pax_only(self):
        src = _read("candidates.nut")
        body = src[src.index("function OpexMakeCandidate("):]
        pax = body.index('if (kind == "pax") {')
        guard = body.index("if (V177_RAIL_PAX_MIN_DIST > 0 && distance < V177_RAIL_PAX_MIN_DIST) {")
        # 19/10 : la branche fret porte aussi la borne tardive V269.
        other = body.index("} else if (distance > ((V269_RAIL_LATE_RELAX > 0 && V269_RELAXED && V269_RAIL_MAX_DIST > bounds.railMax)")
        self.assertLess(pax, guard)
        self.assertLess(guard, other)


if __name__ == "__main__":
    unittest.main()
