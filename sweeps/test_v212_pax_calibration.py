#!/usr/bin/env python3
"""Contrats statiques de V212 : recalage du revenu et du capital predits des lignes rail passagers.

Verifie :
1. Reglages v212_rail_pax_revenue_pct (50..300) et v212_rail_pax_capital_pct (50..200), defaut 100
   (inerte), declares dans info.nut, globals_pre.nut et settings.nut.
2. OpexLineEconomics : recalage applique apres la boucle du nombre de trains, uniquement pour
   kind == "pax", et seulement si l'un des deux reglages differe de 100.
3. Le profit est recalcule depuis le revenu recale (meme formule que OpexApplyRailActualCapital),
   et le ROI depuis le capital recale + immobilise.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI_DIR = ROOT / "ai" / "OpexAI"


def read_file(rel_path: str) -> str:
    return (AI_DIR / rel_path).read_text(encoding="utf-8")


def function_body(source: str, name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\(", source)
    if not match:
        raise AssertionError(f"Function {name} not found")
    start = source.index("{", match.end())
    depth = 0
    for pos in range(start, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1:pos]
    raise AssertionError(f"Unclosed function {name}")


class TestV212Settings(unittest.TestCase):
    def test_declared_with_bounds_and_default_100(self):
        info = read_file("info.nut")
        for name, bounds in (("v212_rail_pax_revenue_pct", "min_value = 50, max_value = 300"),
                             ("v212_rail_pax_capital_pct", "min_value = 50, max_value = 200")):
            block = re.search(rf'name\s*=\s*"{name}"[^}}]+', info)
            self.assertIsNotNone(block, name)
            text = block.group(0)
            self.assertIn(bounds, text)
            for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
                self.assertRegex(text, rf"{key}\s*=\s*100")

    def test_globals_and_reading(self):
        globals_pre = read_file("globals_pre.nut")
        self.assertIn("V212_RAIL_PAX_REVENUE_PCT <- 100;", globals_pre)
        self.assertIn("V212_RAIL_PAX_CAPITAL_PCT <- 100;", globals_pre)
        settings = read_file("settings.nut")
        self.assertIn('AIController.GetSetting("v212_rail_pax_revenue_pct")', settings)
        self.assertIn('AIController.GetSetting("v212_rail_pax_capital_pct")', settings)
        self.assertRegex(settings, r"V212_RAIL_PAX_REVENUE_PCT = \(v212Revenue != null && v212Revenue >= 50 && v212Revenue <= 300\) \? v212Revenue : 100;")
        self.assertRegex(settings, r"V212_RAIL_PAX_CAPITAL_PCT = \(v212Capital != null && v212Capital >= 50 && v212Capital <= 200\) \? v212Capital : 100;")


class TestV212Economics(unittest.TestCase):
    def setUp(self):
        self.body = function_body(read_file("economy.nut"), "OpexLineEconomics")

    def test_guarded_by_pax_and_non_default(self):
        self.assertIn('if (kind == "pax" && (V212_RAIL_PAX_REVENUE_PCT != 100 || V212_RAIL_PAX_CAPITAL_PCT != 100)) {',
                      self.body)

    def test_applied_after_train_choice(self):
        loop = self.body.index("for (local trains = startTrains; trains <= MAX_RAIL_TRAINS; trains++)")
        result = self.body.index("local result = {")
        calib = self.body.index("V212_RAIL_PAX_REVENUE_PCT != 100")
        ret = self.body.rindex("return result;")
        self.assertLess(loop, result)
        self.assertLess(result, calib)
        self.assertLess(calib, ret)

    def test_profit_and_roi_recomputed(self):
        self.assertIn("result.revenueAnnual = (result.revenueAnnual * V212_RAIL_PAX_REVENUE_PCT) / 100;", self.body)
        self.assertIn("result.profitAnnual = result.revenueAnnual - result.runningAnnual - result.amortAnnual;", self.body)
        self.assertIn("result.capital = (result.capital * V212_RAIL_PAX_CAPITAL_PCT) / 100;", self.body)
        self.assertIn("local totalCapital = result.capital + result.immobilise;", self.body)
        self.assertIn("? (result.profitAnnual * 1000) / totalCapital : 0;", self.body)


if __name__ == "__main__":
    unittest.main()
