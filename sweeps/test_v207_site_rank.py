#!/usr/bin/env python3
"""Contrats statiques de V207 site : sites de gare passagers classes par production captee.

Verifie :
1. Reglage v207_rail_pax_site_rank_pct (0..100, defaut 0) declare dans info.nut,
   globals_pre.nut et settings.nut.
2. OpexStationPlans : limite d'echantillonnage = maxPlans quand rankPct vaut 0 (comportement
   historique), classement seulement si rankPct > 0.
3. OpexV207RankStationPlans : tri decroissant sur la production de l'emprise, seuil relatif au
   meilleur site, au plus maxPlans.
4. OpexRailTryPlatformLength : rankPct passe aux deux extremites, uniquement pour les candidats pax.
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
    pattern = rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{"
    match = re.search(pattern, source)
    if not match:
        raise AssertionError(f"Function {name} not found")
    start = match.end() - 1
    depth = 0
    for pos in range(start, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1:pos]
    raise AssertionError(f"Unclosed function {name}")


class TestV207SiteRankSetting(unittest.TestCase):
    def test_declared_with_bounds_and_default_zero(self):
        info = read_file("info.nut")
        block = re.search(r'name\s*=\s*"v207_rail_pax_site_rank_pct"[^}]+', info)
        self.assertIsNotNone(block)
        text = block.group(0)
        self.assertIn("min_value = 0, max_value = 100", text)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(text, rf"{key}\s*=\s*0")

    def test_global_and_reading(self):
        self.assertIn("V207_RAIL_PAX_SITE_RANK_PCT <- 0;", read_file("globals_pre.nut"))
        settings = read_file("settings.nut")
        self.assertIn('AIController.GetSetting("v207_rail_pax_site_rank_pct")', settings)
        self.assertRegex(settings, r"V207_RAIL_PAX_SITE_RANK_PCT\s*=\s*\(v207Rank != null && v207Rank >= 0 && v207Rank <= 100\)")


class TestV207StationPlans(unittest.TestCase):
    def setUp(self):
        self.src = read_file("builder_rail.nut")

    def test_default_limit_is_max_plans(self):
        body = function_body(self.src, "OpexStationPlans")
        self.assertIn("local limit = (rankPct > 0) ? maxPlans * V207_SITE_SAMPLE_FACTOR : maxPlans;", body)
        self.assertNotIn("plans.len() < maxPlans", body)
        self.assertNotIn("plans.len() >= maxPlans", body)
        self.assertIn("if (rankPct > 0) return OpexV207RankStationPlans(", body)
        self.assertRegex(self.src, r"function OpexStationPlans\([^)]*rankPct = 0\)")

    def test_rank_sorts_by_union_value_with_relative_floor(self):
        body = function_body(self.src, "OpexV207RankStationPlans")
        self.assertIn("OpexV207PlatformUnionValue(plan, cargo, coverage)", body)
        self.assertIn("if (a.unionValue > b.unionValue) return -1;", body)
        self.assertIn("local floorValue = best * rankPct / 100;", body)
        self.assertIn("if (kept.len() >= maxPlans) break;", body)
        self.assertIn('OpexDecide("V207_SITE"', body)

    def test_union_value_uses_platform_rectangle(self):
        body = function_body(self.src, "OpexV207PlatformUnionValue")
        self.assertIn("AITile.GetCargoProduction(plan.anchor, cargo, w, h, coverage)", body)

    def test_rank_only_for_pax_candidates(self):
        body = function_body(self.src, "OpexRailTryPlatformLength")
        self.assertIn('local rankPct = (candidate.kind == "pax") ? V207_RAIL_PAX_SITE_RANK_PCT : 0;', body)
        self.assertEqual(body.count("statsA, isDoubleFreight, rankPct);"), 1)
        self.assertEqual(body.count("statsB, isDoubleFreight, rankPct);"), 1)


if __name__ == "__main__":
    unittest.main()
