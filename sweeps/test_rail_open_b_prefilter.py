"""RAIL-OPEN (c): prefilter only cargo-covered B endpoints that cannot join twice.

Static contracts (no engine): intentionally conservative to protect new freight sinks.
"""

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def body(name, function_name):
    code = source(name)
    first = code.index("function " + function_name + "(")
    opening = code.index("{", first)
    depth = 0
    for index in range(opening, len(code)):
        if code[index] == "{":
            depth += 1
        elif code[index] == "}":
            depth -= 1
            if depth == 0:
                return code[first:index + 1]
    raise AssertionError(function_name)


class TestRailOpenBPrefilter(unittest.TestCase):
    def test_matches_too_close_contract_without_bypass(self):
        too_close = body("lines.nut", "OpexAI::_tooClose")
        gate = body("candidates.nut", "OpexRailOpenBAlreadyCovered")
        self.assertIn('("joinLineId" in candidate) ? candidate.joinLineId : -1', too_close)
        self.assertIn('line.lineId == joinLineId) continue;', too_close)
        self.assertIn('AIMap.DistanceManhattan(entry[1], stationTile)', too_close)
        self.assertIn('OpexRememberClosest(d, MIN_SEPARATION, blocking)', too_close)
        self.assertIn('if (RAIL_OPEN == 0 || mother == null || !("railOpen" in mother)) return false;', gate)
        self.assertIn('other == mother.line', gate)
        self.assertIn('stationId == mother.stationId', gate)
        self.assertIn('other.mode != "rail"', gate)
        self.assertIn('AIStation.IsValidStation(stationId)', gate)
        self.assertIn('AIStation.HasStationType(stationId, AIStation.STATION_TRAIN)', gate)

    def test_rejects_only_destinations_already_covered_for_this_cargo(self):
        gate = body("candidates.nut", "OpexRailOpenBAlreadyCovered")
        self.assertIn('AIMap.DistanceManhattan(dstTile, stationTile)', gate)
        self.assertIn('if (distance >= MIN_SEPARATION || distance > catalog.railCoverage) continue;', gate)
        self.assertIn('AICargoList_StationAccepting(stationId)', gate)
        self.assertIn('if (accepting.HasItem(cargo)) return true;', gate)
        self.assertTrue(gate.rstrip().endswith('return false;\n}'))

        # Boundary matrix for the documented guards: a merely nearby station
        # 5-9 tiles from B is NOT proof that the cargo destination is covered.
        def covered(distance, radius, same_mother, accepts, rail_open):
            return rail_open and not same_mother and distance < 10 and distance <= radius and accepts

        for distance, radius, mother, accepts, enabled, expected in (
            (3, 4, False, True, True, True),
            (4, 4, False, True, True, True),
            (5, 4, False, True, True, False),
            (9, 4, False, True, True, False),
            (10, 12, False, True, True, False),
            (1, 4, False, False, True, False),
            (1, 4, True, True, True, False),
            (1, 4, False, True, False, False),
        ):
            with self.subTest(distance=distance, accepts=accepts, rail_open=enabled):
                self.assertEqual(covered(distance, radius, mother, accepts, enabled), expected)

    def test_generators_filter_both_sinks_before_expensive_economics(self):
        for filename, name in (
            ("candidates.nut", "OpexFreightCandidates"),
            ("po01c_generators.nut", "OpexPO01CFreightCandidates"),
        ):
            with self.subTest(filename=filename):
                freight = body(filename, name)
                self.assertEqual(freight.count("OpexRailOpenBAlreadyCovered("), 2)
                self.assertIn("OpexRailOpenBAlreadyCovered(catalog, lines, cargo, industries[di].tile, sibling)", freight)
                self.assertIn("OpexRailOpenBAlreadyCovered(catalog, lines, cargo, town.tile, sibling)", freight)
                self.assertEqual(freight.count('reason=too_close_no_join_b'), 2)
                self.assertEqual(freight.count('stats.pairsOriginServed++;\n'), 5)
                self.assertLess(freight.index("OpexRailOpenBAlreadyCovered(catalog, lines, cargo, industries[di].tile"),
                                freight.index("OpexRailSiblingEmit(catalog, stats, profile, cruiseCache, cargo, source,"))
                self.assertLess(freight.index("OpexRailOpenBAlreadyCovered(catalog, lines, cargo, town.tile"),
                                freight.rindex("OpexRailSiblingEmit(catalog, stats, profile, cruiseCache, cargo, source,"))

    def test_squirrel_identifiers_are_not_reserved(self):
        gate = body("candidates.nut", "OpexRailOpenBAlreadyCovered")
        identifiers = re.findall(r"\blocal\s+(\w+)|\bfunction\s+(\w+)\s*\(", gate)
        reserved = {"clone", "base", "parent", "static", "delegate", "vargc", "vargv",
                    "resume", "yield", "constructor", "instanceof"}
        for local, function_name in identifiers:
            self.assertNotIn(local or function_name, reserved)
        self.assertNotIn(".find(", gate)
        self.assertNotIn("function(", gate)


if __name__ == "__main__":
    unittest.main()
