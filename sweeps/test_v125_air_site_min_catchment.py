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
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('air_site_min_catchment',))

    def test_helper_checks_acceptance_and_production(self):
        helper = body(self.sites, "function OpexAirSiteHasCatchment(")
        self.assertIn("AITile.GetCargoAcceptance(anchor, paxCargo", helper)
        self.assertIn("< 8) return false;", helper)
        self.assertIn("OpexAirAirportCatchmentProduction(anchor, airport.type, paxCargo) > 0", helper)

    def test_catchment_loop_skips_dead_site_before_counting_valid(self):
        loop = body(self.sites, "function OpexAirFindSiteCatchmentListed(")
        guard = loop.index("!OpexAirSiteHasCatchment(anchor")
        self.assertLess(guard, loop.index("valid++;"))
        self.assertLess(guard, loop.index("best = { town = town, anchor = anchor };"))

    def test_cached_anchor_is_rechecked(self):
        find = body(self.sites, "function OpexAirFindSite(")
        self.assertIn("OpexAirSiteHasCatchment(cachedAnchor, airport, OpexAirDemandPaxCargo())", find)


if __name__ == "__main__":
    unittest.main()
