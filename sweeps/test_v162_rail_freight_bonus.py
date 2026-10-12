#!/usr/bin/env python3
"""Tests pour V162 — bonus temporaire de classement du fret rail (test utilisateur du 12/10).

Contrats : réglage déclaré et chargé (défaut 0), bonus appliqué au seul profit de classement
(fundScore et scores grossiers du stock C80), jamais à profitAnnual, et chaque appel gardé
par V162_RAIL_FREIGHT_BONUS_PCT > 0 pour laisser le chemin par défaut inchangé.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def bonus(mode, kind, profit, pct):
    """Modèle Python de OpexV162RailFreightProfit (appelé seulement si pct > 0)."""
    if mode != "rail" or kind == "pax":
        return profit
    return profit * (100 + pct) // 100


class V162Contracts(unittest.TestCase):
    def test_setting_default_off(self):
        info = _read("info.nut")
        block = info[info.index('name = "v162_rail_freight_bonus_pct"'):]
        block = block[:block.index("});")]
        self.assertIn("min_value = 0, max_value = 300", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 0\b")
        self.assertIn("V162_RAIL_FREIGHT_BONUS_PCT <- 0;", _read("globals_pre.nut"))
        self.assertRegex(_read("settings.nut"),
                         r'local v162 = AIController\.GetSetting\("v162_rail_freight_bonus_pct"\);\s*'
                         r'if \(v162 >= 0\) V162_RAIL_FREIGHT_BONUS_PCT = v162;')

    def test_every_call_is_gated_and_ranking_only(self):
        sel = _read("projects_selection.nut")
        fund = sel[sel.index("function OpexProjectFundProfit("):]
        fund = fund[:fund.index("\n}\n")]
        self.assertIn("if (V162_RAIL_FREIGHT_BONUS_PCT > 0) return OpexV162RailFreightProfit(project, calibrated);", fund)
        rail = _read("task_rail.nut")
        calls = re.findall(r"if \(V162_RAIL_FREIGHT_BONUS_PCT > 0\) (\w+) = OpexV162RailFreightProfit\((\w+), \1\);", rail)
        self.assertEqual(sorted(c[0] for c in calls), ["paperProfit", "paperProfit", "readyProfit"])
        total = sum(_read(p.name).count("OpexV162RailFreightProfit(") for p in AI.glob("*.nut"))
        self.assertEqual(total, 5)  # definition + fundScore + 3 scores grossiers C80
        for p in AI.glob("*.nut"):
            self.assertNotRegex(p.read_text(encoding="utf-8"), r"profitAnnual\s*=\s*OpexV162", p.name)

    def test_helper_targets_rail_freight_only(self):
        sel = _read("projects_selection.nut")
        body = sel[sel.index("function OpexV162RailFreightProfit("):]
        body = body[:body.index("\n}\n")]
        self.assertIn('project.mode != "rail"', body)
        self.assertIn('project.kind == "pax") return profit;', body)
        self.assertIn("return profit * (100 + V162_RAIL_FREIGHT_BONUS_PCT) / 100;", body)
        self.assertEqual(bonus("rail", "freight", 28000, 50), 42000)
        self.assertEqual(bonus("rail", "pax", 5000, 50), 5000)
        self.assertEqual(bonus("air", "pax", 9000, 50), 9000)
        self.assertEqual(bonus("fleet", "fleet", 9000, 50), 9000)


if __name__ == "__main__":
    unittest.main()
