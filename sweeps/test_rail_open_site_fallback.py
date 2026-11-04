#!/usr/bin/env python3
"""Contrats statiques pour les replis de sites RAIL-OPEN (aucun Docker)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = (ROOT / "ai" / "OpexAI" / "builder_rail.nut").read_text(encoding="utf-8")
LINES = (ROOT / "ai" / "OpexAI" / "lines.nut").read_text(encoding="utf-8")


def function_body(name: str) -> str:
    match = re.search(r"function\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{", BUILDER)
    if match is None:
        raise AssertionError(f"missing function {name}")
    depth = 1
    for offset in range(match.end(), len(BUILDER)):
        if BUILDER[offset] == "{":
            depth += 1
        elif BUILDER[offset] == "}":
            depth -= 1
            if depth == 0:
                return BUILDER[match.start():offset + 1]
    raise AssertionError(f"unterminated function {name}")


class TestRailOpenSiteFallback(unittest.TestCase):
    def test_optin_and_original_strict_join_preserved(self):
        body = function_body("OpexRailPlatformPlans")
        self.assertIn("local railOpenSibling = RAIL_OPEN != 0 && !joinB", body)
        self.assertIn('("railOpen" in candidate) && candidate.railOpen', body)
        self.assertIn("local railOpenB = RAIL_OPEN != 0 && joinB", body)
        self.assertIn('("sibling_src" in candidate) && candidate.sibling_src', body)
        self.assertIn('("shared_dest" in candidate) && candidate.shared_dest', body)
        self.assertIn('("convergent_dest" in candidate) && candidate.convergent_dest', body)
        self.assertIn("local railOpenJoin = railOpenSibling || railOpenB;", body)
        self.assertIn("local railOpenFallback = railOpenJoin", body)
        self.assertIn("if (EB2_NEW_STATION_FALLBACK == 0 && !railOpenFallback)", body)
        self.assertIn("if (strictOriginReuseJoin)", body)
        self.assertIn("OpexRailOpenNewStationFunded(catalog, candidate, jointLength)", body)

    def test_order_a_parallel_then_spread_then_cash_fallback(self):
        body = function_body("OpexRailPlatformPlans")
        a = body.index("if (!joinB) {")
        b = body.index("} else {", a)
        scope = body[a:b]
        parallel = scope.index("OpexJoinPlatformPlans(")
        spread = scope.index("OpexRailOpenSiblingSpreadPlans(")
        self.assertLess(parallel, spread)
        self.assertIn("if (railOpenSibling && jointPlansA.len() == 0 && !railOpenCooldown)", scope)
        self.assertIn("p.stationId <- candidate.joinStationId;", scope)
        self.assertLess(spread, body.index("if (strictOriginReuseJoin)", b))
        helper = function_body("OpexRailOpenSiblingSpreadPlans")
        self.assertIn("OpexV264SpreadJoinPlans(candidate.joinPlatform, candidate.joinStationId, statsA)", helper)

    def test_order_b_parallel_then_spread_then_cash_fallback(self):
        body = function_body("OpexRailPlatformPlans")
        b = body.index("} else {", body.index("if (!joinB) {"))
        parallel = body.index("OpexJoinPlatformPlans(candidate.joinPlatform, candidate.joinStationId, statsB)", b)
        spread = body.index("OpexV264SpreadJoinPlans(candidate.joinPlatform, candidate.joinStationId, statsB)", parallel)
        fallback = body.index("if (strictOriginReuseJoin)", spread)
        self.assertLess(parallel, spread)
        self.assertLess(spread, fallback)
        self.assertIn("if (jointPlansB.len() == 0)", body[parallel:spread])
        self.assertIn("if (!railOpenCooldown)", body[parallel:spread])
        self.assertIn("OpexDecide(\"V264_JOIN\"", body[spread:fallback])
        self.assertIn("p.stationId <- candidate.joinStationId;", body[spread:fallback])
        self.assertIn("phase=joint_plan end=B", body[spread:fallback])

    def test_failed_join_cache_is_short_opaque_and_bounded(self):
        key = function_body("OpexRailOpenJoinKey")
        for field in ("joinStationId", "candidate.src", "candidate.dst", "candidate.cargo", "joinedLength"):
            self.assertIn(field, key)
        self.assertIn("const RAIL_OPEN_JOIN_RETRY_DAYS = 45;", BUILDER)
        self.assertIn("const RAIL_OPEN_JOIN_FAILURE_LIMIT = 128;", BUILDER)
        cooling = function_body("OpexRailOpenJoinCooling")
        remember = function_body("OpexRailOpenRememberJoinFailure")
        self.assertIn("age >= 0 && age < RAIL_OPEN_JOIN_RETRY_DAYS", cooling)
        self.assertIn("delete RAIL_OPEN_JOIN_FAILURES[key]", cooling)
        self.assertIn("RAIL_OPEN_JOIN_FAILURES.len() >= RAIL_OPEN_JOIN_FAILURE_LIMIT", remember)
        self.assertIn("RAIL_OPEN_JOIN_FAILURES[key] <- AIDate.GetCurrentDate()", remember)
        body = function_body("OpexRailPlatformPlans")
        self.assertIn("if (!joinedFound && !railOpenCooldown) OpexRailOpenRememberJoinFailure(railOpenKey);", body)
        self.assertIn("local railOpenCooldown = railOpenJoin && OpexRailOpenJoinCooling(railOpenKey);", body)

    def test_new_station_gate_uses_actual_cash_and_extra_station_cost(self):
        gate = function_body("OpexRailOpenNewStationFunded")
        self.assertIn("RAIL_OPEN == 0", gate)
        self.assertIn('candidate.kind != "freight"', gate)
        self.assertIn("candidate.profitAnnual <= 0", gate)
        self.assertIn("catalog.costStation * joinedLength", gate)
        self.assertIn("2 * catalog.costTrackPerTile", gate)
        self.assertIn("OpexRailOpenCashReady(candidate.capital + extra)", gate)
        plans = function_body("OpexRailPlatformPlans")
        self.assertIn("phase=skip_fallback reason=cash_or_profit", plans)
        self.assertIn("phase=new_station", plans)
        self.assertIn("phase=joint_plan end=A", plans)

    def test_not_a_too_close_bypass_and_not_a_construction_claim(self):
        # _tooClose court-circuite avant OpexRailPlatformPlans dans task_rail.nut.
        # Le builder ne doit donc pas lever artificiellement la garde en B.
        self.assertIn("function OpexAI::_tooClose(candidate)", LINES)
        self.assertNotIn("function OpexAI::_tooClose", BUILDER)
        body = function_body("OpexRailPlatformPlans")
        self.assertNotIn("MIN_SEPARATION =", body)
        self.assertNotIn("ORIGIN_SEPARATION =", body)
        self.assertNotIn("candidate.joinLineId <-", body)
        self.assertNotIn("RAIL_BUILD", body)
        self.assertIn('OpexDecide("RAIL_OPEN_SITE"', body)

    def test_new_squirrel_identifiers_not_reserved(self):
        source = BUILDER[BUILDER.index("/* RAIL-OPEN : cache"):BUILDER.index("/* Cherche les deux extremites", BUILDER.index("/* RAIL-OPEN : cache"))]
        forbidden = r"\b(?:parent|base|clone|static|delegate|vargc|vargv|resume|yield|constructor|instanceof)\b"
        for declaration in re.findall(r"\blocal\s+(\w+)|\bfunction\s+(\w+)\s*\(", source):
            name = declaration[0] or declaration[1]
            self.assertIsNone(re.fullmatch(forbidden, name), name)
        self.assertNotIn(".find(", source)
        self.assertNotIn("function(", source)


if __name__ == "__main__":
    unittest.main()
