#!/usr/bin/env python3
"""Contrats statiques C96 — meilleur placement AIR sans nouveau modèle de demande."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_settings, parse_ai_setting_specs
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air


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


class TestC96AirSiteCatchment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = read("ai/OpexAI/info.nut")
        cls.settings = read("ai/OpexAI/settings.nut")
        cls.globals = read("ai/OpexAI/globals_pre.nut")
        cls.air = read_builder_air()

    def test_setting_is_declared_loaded_and_default_on(self):
        # V237: the adopted path is permanent; the public rollback is gone.
        from v237_contracts import assert_retired
        assert_retired(self, ('c96_air_site_catchment',))

    def test_score_is_physical_and_not_a_demand_model(self):
        score = body(self.air, "function OpexAirC96SiteCatchmentScore(")
        self.assertIn("OpexAirAirportCatchmentProduction", score)
        self.assertNotIn("AITown.GetLastMonthProduction", score)
        self.assertNotIn("TOWN_CATCHMENT_SHARE_PCT", score)
        self.assertNotIn("OpexAirEconomics", score)

    def test_search_reuses_v94_ring_and_is_bounded(self):
        search = body(self.air, "function OpexAirFindSiteCatchmentListed(")
        self.assertIn("OpexAirFindSiteRing(", search)
        self.assertIn("OpexAirFootprintCheapOk(anchor, airport)", search)
        self.assertIn("AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW)", search)
        self.assertIn("valid >= C96_AIR_SITE_MAX_VALID", search)
        self.assertIn("firstValidRing + C96_AIR_SITE_EXTRA_RINGS", search)
        self.assertIn("score > bestScore", search)
        self.assertNotIn("score >= bestScore", search)

    def test_choice_telemetry_compares_first_and_selected_site(self):
        log = body(self.air, "function OpexAirC96LogChoice(")
        for field in (
            '"C96_SITE town="',
            '" first="',
            '" first_score="',
            '" best="',
            '" best_score="',
            '" gain="',
            '" first_dist="',
            '" best_dist="',
            '" valid="',
            '" first_ring="',
            '" best_ring="',
            '" probes="',
        ):
            self.assertIn(field, log)
        search = body(self.air, "function OpexAirFindSiteCatchmentListed(")
        self.assertIn("firstAnchor = anchor", search)
        self.assertIn("firstScore = score", search)
        self.assertIn("OpexAirC96LogChoice", search)

if __name__ == "__main__":
    unittest.main()
