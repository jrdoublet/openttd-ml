#!/usr/bin/env python3
"""V273 : repli en T de V264 pour les candidats V178 (defaut 0)."""
from __future__ import annotations

import unittest
from pathlib import Path

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


class V273SharedDestSpread(unittest.TestCase):
    def test_setting_default_off(self) -> None:
        info = _read("info.nut")
        start = info.index('name = "v273_shared_dest_spread"')
        block = info[start:info.index("});", start)]
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(level + " = 0", block)
        self.assertIn("V273_SHARED_DEST_SPREAD <- false;", _read("globals_pre.nut"))
        self.assertIn('GetSetting("v273_shared_dest_spread")', _read("settings.nut"))

    def test_spread_guard_accepts_either_flag(self) -> None:
        rail = _read("builder_rail.nut")
        self.assertIn("if (!V264_CONVERGENT_FREIGHT && !V273_SHARED_DEST_SPREAD) return [];", rail)

    def test_shared_dest_reaches_spread_after_parallel(self) -> None:
        rail = _read("builder_rail.nut")
        v273 = rail.index('local v273Spread = V273_SHARED_DEST_SPREAD && ("shared_dest" in candidate)')
        branch = rail.index("if (v264Spread || v273Spread) {", v273)
        spread = rail.index("OpexV264SpreadJoinPlans(", branch)
        self.assertIn("if (jointPlansB.len() == 0)", rail[branch:spread])
        self.assertIn('" via=" + (v264Spread ? "v264" : "v178")', rail)


if __name__ == "__main__":
    unittest.main()
