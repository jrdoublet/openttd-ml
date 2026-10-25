#!/usr/bin/env python3
"""Contrats de retrait V192 — v192_rail_time_denom_pct (defaut 0, inerte).

Au defaut le denominateur du fundScore etait deja le capital (identite).
La fonction OpexV192RailDenom et le reglage sont retires.
"""
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


def _function_body(source: str, name: str) -> str:
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("unterminated " + name)


class SettingRemoved(unittest.TestCase):
    def test_not_declared(self):
        specs = parse_ai_setting_specs(AI / "info.nut")
        self.assertNotIn("v192_rail_time_denom_pct", specs)
        self.assertNotIn('name = "v192_rail_time_denom_pct"', _read("info.nut"))

    def test_not_loaded(self):
        self.assertNotIn("V192_RAIL_TIME_DENOM_PCT", _read("globals_pre.nut"))
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertNotIn("v192_rail_time_denom_pct", body)
        self.assertNotIn("V192_RAIL_TIME_DENOM_PCT", body)

    def test_helper_removed(self):
        models = _read("projects_models.nut")
        selection = _read("projects_selection.nut")
        self.assertNotIn("function OpexV192RailDenom", models)
        self.assertNotIn("OpexV192RailDenom", models)
        self.assertNotIn("OpexV192RailDenom", selection)

    def test_fund_score_uses_capital_denom(self):
        body = _function_body(_read("projects_selection.nut"), "OpexProjectSelectAffordable")
        self.assertIn("project.fundScore <- OpexProjectScore(OpexProjectFundProfit(project),", body)
        self.assertIn(
            "(kDec > scoreDecisionFinanceCapital && !fleetExemptDecision)",
            body,
        )
        self.assertNotIn("OpexV192RailDenom", body)


if __name__ == "__main__":
    unittest.main()
