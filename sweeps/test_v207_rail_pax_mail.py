#!/usr/bin/env python3
"""Tests statiques et de contrat pour V207 : rail passagers + courrier a la AAAHogEx.

Verifie :
1. Declaration des 3 reglages v207_rail_pax_share_pct (0..100, defaut 0),
   v207_rail_mail (bool, defaut 0), v207_rail_pax_joined_stops (0..4, defaut 0)
   dans info.nut, globals_pre.nut et settings.nut avec bornes.
2. OpexPaxCandidates :
   - calcul du volume passagers avec V207_RAIL_PAX_SHARE_PCT si > 0, sinon TOWN_CATCHMENT_SHARE_PCT (22%).
   - generation du secondary courrier si V207_RAIL_MAIL actif, avec precomputation optionnelle et memes parts.
   - transmission de secondary a OpexMakeCandidate.
3. Chaine V163 et recalculs :
   - OpexV163CandidateSecondary debloque pour le pax quand V207_RAIL_MAIL est actif.
   - Conservation du second cargo dans OpexMakeCandidate (chemin vivant ; pax_near retire).
4. Arrets joints rail V207 :
   - catalog.nut active AIRoad.SetCurrentRoadType(ROADTYPE_ROAD) si AIR_JOINED_STOPS ou V207_RAIL_PAX_JOINED_STOPS > 0.
   - OpexV207RailBuildJoinedStops defini dans builder_rail.nut avec les contraintes d'emprise, distance > rayon train, etc.
   - Appel dans task_rail.nut hors du bloc de journalisation, pour platformA et platformB, uniquement si V207_RAIL_PAX_JOINED_STOPS > 0 et kind == "pax".
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


class TestV207Settings(unittest.TestCase):
    def setUp(self):
        self.info = read_file("info.nut")
        self.globals_pre = read_file("globals_pre.nut")
        self.settings = read_file("settings.nut")

    def test_info_settings_declared(self):
        # 1. v207_rail_pax_share_pct
        match_share = re.search(r'name\s*=\s*"v207_rail_pax_share_pct"[^}]+', self.info)
        self.assertIsNotNone(match_share, "v207_rail_pax_share_pct must be declared")
        block_share = match_share.group(0)
        self.assertIn("min_value = 0", block_share)
        self.assertIn("max_value = 100", block_share)
        self.assertIn("easy_value = 0", block_share)
        self.assertIn("custom_value = 0", block_share)

        # 2. v207_rail_mail
        match_mail = re.search(r'name\s*=\s*"v207_rail_mail"[^}]+flags\s*=\s*AICONFIG_BOOLEAN', self.info, re.S)
        self.assertIsNotNone(match_mail, "v207_rail_mail must be AICONFIG_BOOLEAN")
        block_mail = match_mail.group(0)
        self.assertIn("easy_value = 0", block_mail)
        self.assertIn("custom_value = 0", block_mail)

        # 3. v207_rail_pax_joined_stops
        match_stops = re.search(r'name\s*=\s*"v207_rail_pax_joined_stops"[^}]+', self.info)
        self.assertIsNotNone(match_stops, "v207_rail_pax_joined_stops must be declared")
        block_stops = match_stops.group(0)
        self.assertIn("min_value = 0", block_stops)
        self.assertIn("max_value = 4", block_stops)
        self.assertIn("easy_value = 0", block_stops)
        self.assertIn("custom_value = 0", block_stops)

    def test_globals_pre_defaults(self):
        self.assertIn("V207_RAIL_PAX_SHARE_PCT <- 0;", self.globals_pre)
        self.assertIn("V207_RAIL_MAIL <- false;", self.globals_pre)
        self.assertIn("V207_RAIL_PAX_JOINED_STOPS <- 0;", self.globals_pre)

    def test_settings_loaded(self):
        self.assertIn('AIController.GetSetting("v207_rail_pax_share_pct")', self.settings)
        self.assertIn("V207_RAIL_PAX_SHARE_PCT =", self.settings)
        self.assertIn('V207_RAIL_MAIL = AIController.GetSetting("v207_rail_mail") != 0;', self.settings)
        self.assertIn('AIController.GetSetting("v207_rail_pax_joined_stops")', self.settings)
        self.assertIn("V207_RAIL_PAX_JOINED_STOPS =", self.settings)


class TestV207PaxAndMailCandidates(unittest.TestCase):
    def setUp(self):
        self.candidates_src = read_file("candidates.nut")
        self.economy_src = read_file("economy.nut")

    def test_pax_candidates_share_and_mail(self):
        body = function_body(self.candidates_src, "OpexPaxCandidates")
        # Check share logic
        self.assertIn("V207_RAIL_PAX_SHARE_PCT > 0 ? V207_RAIL_PAX_SHARE_PCT : TOWN_CATCHMENT_SHARE_PCT", body)
        # Check mail condition
        self.assertIn("V207_RAIL_MAIL && catalog.mailCargo >= 0 && (catalog.mailCargo in catalog.wagonByCargo)", body)
        # Check secondary passed to OpexMakeCandidate
        self.assertIn("OpexMakeCandidate(catalog, \"pax\", cargo, towns[a].tile, towns[b].tile,\n"
                      "                                          monthly, false, stats, false, candidateProfile, cruiseCache,\n"
                      "                                          secondary)", body)

    def test_secondary_unblocked_in_economy(self):
        body = function_body(self.economy_src, "OpexV163CandidateSecondary")
        # Must retain V163 compatibility and allow V207_RAIL_MAIL for pax
        self.assertNotIn("V163_MULTI_CARGO", body)
        self.assertIn("V207_RAIL_MAIL", body)
        self.assertIn('candidate.kind == "pax"', body)

    def test_make_candidate_preserves_secondary(self):
        body = function_body(self.candidates_src, "OpexMakeCandidate")
        self.assertIn('"wagons2" in economics', body)
        self.assertIn("candidate.cargo2 <- economics.cargo2;", body)
        self.assertNotIn("OpexMakePaxNearCandidate", self.candidates_src)


class TestV207JoinedStops(unittest.TestCase):
    def setUp(self):
        self.builder_src = read_file("builder_rail.nut")
        self.task_rail_src = read_file("task_rail.nut")
        self.catalog_src = read_file("catalog.nut")

    def test_catalog_road_type_fallback(self):
        body = function_body(self.catalog_src, "OpexCatalog::refresh")
        self.assertNotIn("AIR_JOINED_STOPS", body)
        self.assertIn("else if (AIRoad.IsRoadTypeAvailable(AIRoad.ROADTYPE_ROAD))", body)
        self.assertIn("AIRoad.SetCurrentRoadType(AIRoad.ROADTYPE_ROAD);", body)

    def test_builder_rail_joined_stops_function(self):
        body = function_body(self.builder_src, "OpexV207RailBuildJoinedStops")
        self.assertIn("if (maxStops <= 0 || platform == null) return 0;", body)
        self.assertIn("AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP)", body)
        self.assertIn("AIStation.GetCoverageRadius(AIStation.STATION_TRAIN)", body)
        self.assertIn("dx + dy <= railCoverage", body)
        self.assertIn("AIRoad.BuildDriveThroughRoadStation", body)
        self.assertIn("OpexBoostTownRating(townId, 800, 40)", body)
        self.assertIn('OpexDecide("V207_STOP"', body)
        self.assertIn('OpexDecide("V207_STOPS"', body)

    def test_task_rail_call_outside_decision_log(self):
        # The call must be within `if (result.ok) {` and outside `if (DECISION_LOG) {`
        block = function_body(self.task_rail_src, "OpexAI::_recordRailAttempt")

        # Check call is guarded by V207_RAIL_PAX_JOINED_STOPS > 0 and candidate.kind == "pax"
        self.assertIn('if (V207_RAIL_PAX_JOINED_STOPS > 0 && candidate.kind == "pax")', block)
        self.assertIn("OpexV207RailBuildJoinedStops(result.platformA", block)
        self.assertIn("OpexV207RailBuildJoinedStops(result.platformB", block)

        # Ensure call is not inside the DECISION_LOG block
        call_pos = block.index("OpexV207RailBuildJoinedStops")
        result_ok_pos = block.index("if (result.ok) {\n    local idx = this._nextLineId;")
        self.assertGreater(call_pos, result_ok_pos)


if __name__ == "__main__":
    unittest.main()
