#!/usr/bin/env python3
"""sweeps/test_rail_sibling_lot1.py — Contrats RAIL-SIBLING lot 1 (rail_sibling, defaut 0)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


class TestRailSiblingLot1(unittest.TestCase):
    def test_setting_default_off(self):
        info = read("info.nut")
        block = info[info.index('name = "rail_sibling"'):]
        block = block[:block.index("});")]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{level}_value = 0", block)
        self.assertIn("RAIL_SIBLING <- 0;", read("globals_pre.nut"))
        settings = read("settings.nut")
        self.assertEqual(settings.count('AIController.GetSetting("rail_sibling")'), 1)
        self.assertIn("RAIL_SIBLING = (railSibling != null && railSibling > 0) ? 1 : 0;", settings)

    def test_parent_inert_when_off(self):
        cand = read("candidates.nut")
        body = cand[cand.index("function OpexRailSiblingParent"):]
        self.assertTrue(body.split("\n", 3)[2].strip().startswith("if (RAIL_SIBLING == 0"))

    def test_both_generators_hooked(self):
        # Le generateur historique et la copie PO01c (defaut) doivent porter les memes accroches.
        for name in ("candidates.nut", "po01c_generators.nut"):
            src = read(name)
            self.assertIn("(RAIL_SIBLING != 0 && ss != null && longGood == null)", src, name)
            self.assertEqual(src.count("OpexRailSiblingEmit("), 2 + (1 if name == "candidates.nut" else 0), name)
            self.assertIn("if (sibling != null && sd == null) {", src, name)
            self.assertIn("if (sibling != null && st == null) {", src, name)
            # La branche soeur precede le rejet origin_served.
            self.assertLess(src.index("if (sibling != null && sd == null) {"),
                            src.index("if (!v179Keep && (ss != null || sd != null)) {"), name)

    def test_emit_contract(self):
        cand = read("candidates.nut")
        emit = cand[cand.index("function OpexRailSiblingEmit"):]
        emit = emit[:emit.index("\n}\n")]
        for needle in ("candidate.sibling_src <- 1;", 'candidate.joinEnd <- "A";',
                       "candidate.joinLineId <- mother.line.lineId;",
                       "candidate.joinStationId <- mother.stationId;",
                       "candidate.siblingRevPct <- mother.revPct;",
                       "OpexRailSiblingApplyRevenue(candidate);"):
            self.assertIn(needle, emit)

    def test_revenue_boost_survives_reprice(self):
        eco = read("economy.nut")
        body = eco[eco.index("function OpexApplyRailEconomics"):]
        body = body[:body.index("\n}\n")]
        self.assertTrue(body.rstrip().endswith("OpexRailSiblingApplyRevenue(candidate);"))

    def test_strict_join(self):
        builder = read("builder_rail.nut")
        m = re.search(r"local strictOriginReuseJoin = .*?;", builder, re.S)
        self.assertIsNotNone(m)
        self.assertIn('"sibling_src" in candidate', m.group(0))


if __name__ == "__main__":
    unittest.main()
