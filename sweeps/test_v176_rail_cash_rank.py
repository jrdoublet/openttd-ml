#!/usr/bin/env python3
"""Tests statiques pour V176 — classement rail par profit absolu sous tresorerie dormante.

Reglage : `v176_rail_cash_rank_k` (entier 0..2000, en kGBP, defaut 0 = inerte).
Quand N > 0 et que le capital disponible depasse N * 1000, les projets rail
financables sont classes par profit annuel calibre absolu.
"""
from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

# Resolution du dossier racine sans identifiant interdit
ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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


class SettingDeclaration(unittest.TestCase):
    def test_setting_spec(self):
        spec = parse_ai_setting_specs(AI / "info.nut")["v176_rail_cash_rank_k"]
        self.assertEqual(spec["default"], 0)
        self.assertFalse(spec["boolean"])
        self.assertEqual((spec["min_value"], spec["max_value"]), (0, 2000))
        block = _read("info.nut").split('name = "v176_rail_cash_rank_k"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 0\b")

    def test_loaded_once_in_settings(self):
        self.assertIn("V176_RAIL_CASH_RANK_K <- 0;", _read("globals_pre.nut"))
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertEqual(body.count('AIController.GetSetting("v176_rail_cash_rank_k")'), 1)
        self.assertIn("local cashRankK = AIController.GetSetting(\"v176_rail_cash_rank_k\");", body)
        self.assertIn("V176_RAIL_CASH_RANK_K = (cashRankK != null && cashRankK > 0) ? cashRankK : 0;", body)
        self.assertIn("if (V176_RAIL_CASH_RANK_K > 2000) V176_RAIL_CASH_RANK_K = 2000;", body)


class SelectionStructure(unittest.TestCase):
    def test_single_capital_read_guarded(self):
        body = _function_body(_read("projects_selection.nut"), "OpexProjectSelectAffordable")
        # OpexAvailableCapital est garde par V176_RAIL_CASH_RANK_K > 0 : aucun appel au defaut 0
        guard = (
            "local v176Active = false;\n"
            "  if (V176_RAIL_CASH_RANK_K > 0) {\n"
            "    v176Active = OpexAvailableCapital() > (V176_RAIL_CASH_RANK_K * 1000);\n"
            "  }"
        )
        self.assertIn(guard, body)
        # La lecture n'a lieu qu'une seule fois dans la fonction
        self.assertEqual(body.count("OpexAvailableCapital()"), 1)

    def test_rail_absolute_scoring_branch(self):
        body = _function_body(_read("projects_selection.nut"), "OpexProjectSelectAffordable")
        # Mode rail et v176Active utilisent OpexProjectFundProfit sans division par le capital
        branch = (
            "local isV176Rail = v176Active && project.mode == \"rail\";\n"
            "    if (isV176Rail) {\n"
            "      project.fundScore <- OpexProjectFundProfit(project);\n"
            "      project.v176 <- 1;\n"
            "    } else {\n"
            "      if (V176_RAIL_CASH_RANK_K > 0 && (\"v176\" in project)) project.v176 = 0;\n"
            "      project.fundScore <- OpexProjectScore(OpexProjectFundProfit(project),"
        )
        self.assertIn(branch, body)

    def test_fallback_loop_consistent(self):
        body = _function_body(_read("projects_selection.nut"), "OpexProjectSelectAffordable")
        fallback_pos = body.index("if (affordable.len() == 0 && floorProfit > 0)")
        fallback_sub = body[fallback_pos:]
        self.assertIn("local isV176Rail = v176Active && project.mode == \"rail\";", fallback_sub)
        self.assertIn("project.fundScore <- OpexProjectFundProfit(project);", fallback_sub)
        self.assertIn("project.v176 <- 1;", fallback_sub)

    def test_non_rail_modes_untouched(self):
        # Seul le mode rail est conditionne par isV176Rail
        body = _function_body(_read("projects_selection.nut"), "OpexProjectSelectAffordable")
        for match in re.finditer(r"isV176Rail\s*=\s*([^;]+);", body):
            expr = match.group(1).strip()
            self.assertEqual(expr, 'v176Active && project.mode == "rail"')


class LoggingContracts(unittest.TestCase):
    def test_portfolio_rank_logs_v176(self):
        source = _read("projects_rank_log.nut")
        body_std = _function_body(source, "OpexLogPortfolioRank")
        self.assertIn('local v176Tag = (("v176" in p) && p.v176) ? " v176=1" : "";', body_std)
        self.assertIn('+ roadFleet + v176Tag', body_std)

        body_tension = _function_body(source, "OpexLogPortfolioRankWithTension")
        self.assertIn('local v176Tag = (("v176" in p) && p.v176) ? " v176=1" : "";', body_tension)
        self.assertIn('+ roadFleet + v176Tag', body_tension)


if __name__ == "__main__":
    unittest.main()
