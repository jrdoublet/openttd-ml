#!/usr/bin/env python3
"""Contrats statiques V125 — refuser un site AIR sans passagers dans le catchment."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_settings


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for idx in range(brace, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start : idx + 1]
    raise AssertionError(f"unterminated function: {signature}")


class TestV125AirSiteMinCatchment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sites = read("ai/OpexAI/air_sites.nut")

    def test_default_on_at_all_difficulties(self):
        info = read("ai/OpexAI/info.nut")
        setting = info[info.index('name = "air_site_min_catchment"'):]
        setting = setting[:setting.index("});")]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{difficulty}_value = 1", setting)
        self.assertEqual(parse_ai_settings(ROOT / "ai" / "OpexAI" / "info.nut")["air_site_min_catchment"], 1)
        self.assertIn("AIR_SITE_MIN_CATCHMENT <- false;", read("ai/OpexAI/globals_pre.nut"))
        self.assertIn('AIR_SITE_MIN_CATCHMENT = AIController.GetSetting("air_site_min_catchment") != 0;',
                      read("ai/OpexAI/settings.nut"))

    def test_helper_checks_acceptance_and_production(self):
        helper = body(self.sites, "function OpexAirSiteHasCatchment(")
        self.assertIn("AITile.GetCargoAcceptance(anchor, paxCargo", helper)
        self.assertIn("< 8) return false;", helper)
        self.assertIn("OpexAirAirportCatchmentProduction(anchor, airport.type, paxCargo) > 0", helper)

    def test_catchment_loop_skips_dead_site_before_counting_valid(self):
        loop = body(self.sites, "function OpexAirFindSiteCatchmentListed(")
        guard = loop.index("AIR_SITE_MIN_CATCHMENT && !OpexAirSiteHasCatchment(anchor")
        self.assertLess(guard, loop.index("valid++;"))
        self.assertLess(guard, loop.index("best = { town = town, anchor = anchor };"))

    def test_cached_anchor_is_rechecked(self):
        find = body(self.sites, "function OpexAirFindSite(")
        self.assertIn("OpexAirSiteHasCatchment(cachedAnchor, airport, OpexAirDemandPaxCargo())", find)


if __name__ == "__main__":
    unittest.main()
