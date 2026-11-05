"""INVEST-STALL b+c: source-level safety contracts (no OpenTTD engine).

These tests validate the opt-in gates, both generator entry points, the
single-end separation exception and the physical NEW-station checks. They do
not certify train movement, station ratings or the economics of the option.
"""

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def block(code, name):
    start = code.index("function " + name + "(")
    brace = code.index("{", start)
    depth = 0
    for i in range(brace, len(code)):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if depth == 0:
                return code[start:i + 1]
    raise AssertionError("unterminated " + name)


def distance_bonus(active, mode, year, start_year, cash, sliced):
    if not active or mode != "freight" or sliced or year < start_year + 4 or cash < 750000:
        return 0
    age = year - start_year
    return 20 if age == 4 else (40 if age == 5 else 60)


class InvestStallOriginContracts(unittest.TestCase):
    def test_flag_remains_optin_default_zero(self):
        info = source("info.nut")
        setting = info.split('name = "invest_stall"', 1)[1].split('flags = AICONFIG_BOOLEAN', 1)[0]
        self.assertTrue(all(f"{d}_value = 0" in setting for d in ("easy", "medium", "hard", "custom")))
        self.assertIn("INVEST_STALL <- false;", source("globals_pre.nut"))

    def test_ready_delegates_to_cash_and_year_gate(self):
        gate = block(source("invest_stall.nut"), "OpexInvestStallReady")
        self.assertIn("INVEST_STALL && MODE_RAIL", gate)
        self.assertIn("OpexAvailableCapital() >= 750000", gate)
        self.assertIn("OPEX_START_YEAR + 4", gate)

    def test_capacity_uses_real_primary_trains_not_nominal_project(self):
        source_gap = block(source("invest_stall.nut"), "OpexInvestStallSourceGap")
        self.assertIn("OpexInvestStallLineCapacity(existing)", source_gap)
        self.assertIn("production.tofloat() <= total", source_gap)
        self.assertIn("pct >= 75 && rating >= 75", source_gap)

    def test_parent_screen_requires_one_existing_unblocked_source_station(self):
        parent = block(source("candidates.nut"), "OpexInvestStallSecondSourceParent")
        for token in ('!INVEST_STALL', 'V276_CAND_SLICES > 0',
                      'V190_RAIL_DOUBLE_BUILD', '!OpexInvestStallReady()',
                      'service.blocked', 'service.lineEnd != "A"',
                      'mother.cargo != cargo', 'physicalHeadroom > 0',
                      'OpexInvestStallParentCanGrowWagon(', 'OpexInvestStallSourceGap(',
                      'gap.industry != source.id', 'spare <= 0'):
            self.assertIn(token, parent)

    def test_second_station_when_rating_cannot_fill_mother_even_with_wagon_room(self):
        parent = block(source("candidates.nut"), "OpexInvestStallSecondSourceParent")
        # La priorité flotte n'est PAS un simple test de place disponible :
        # une gare dont l'offre notée < capacité ne profite d'aucun wagon.
        self.assertIn('gap.production.tofloat() * gap.rating / 100.0', parent)
        self.assertIn('local canLoadMoreAtMother = ratedOffer > gap.capacity;', parent)
        self.assertIn('local actionableWagon = canLoadMoreAtMother && physicalHeadroom > 0', parent)
        self.assertIn('event=origin_fleet_blocked reason=rating_supply', parent)
        self.assertLess(parent.index('OpexInvestStallSourceGap('),
                        parent.index('local actionableWagon = canLoadMoreAtMother'))
        for production, rating, capacity, expected in (
            (200, 40, 90, False), (200, 40, 70, True),
            (200, 75, 120, True), (200, 20, 60, False),
        ):
            self.assertEqual(production * rating / 100.0 > capacity, expected)

    def test_unactionable_wagon_cannot_block_second_station(self):
        parent = block(source("candidates.nut"), "OpexInvestStallSecondSourceParent")
        grow = block(source("candidates.nut"), "OpexInvestStallParentCanGrowWagon")
        self.assertIn('if (actionableWagon)', parent)
        self.assertNotIn('mother.doubleTrack == 1', parent)
        self.assertIn('OpexInvestStallFleetMargin(', grow)
        self.assertIn('OpexV284Equipment(', grow)
        self.assertIn('AIVehicle.GetLength(train) + 8 > lengthLimit * 16', grow)

    def test_new_candidate_is_single_train_new_station_not_join(self):
        emit = block(source("candidates.nut"), "OpexInvestStallEmitSecondStation")
        for token in ('c.trains != 1', 'c.investStallNewSource <- 1;',
                      'c.investStallParentLineId <-',
                      'c.investStallParentStationId <-',
                      'c.investStallParentStationTile <-',
                      'c.joinPlatform <- null;', 'event=origin_candidate'):
            self.assertIn(token, emit)
        self.assertNotIn('c.joinEnd <- "A"', emit)
        self.assertNotIn('c.joinLineId <-', emit)

    def test_both_generators_apply_identical_explicit_second_station_branch(self):
        legacy = block(source("candidates.nut"), "OpexFreightCandidates")
        resumable = block(source("po01c_generators.nut"), "OpexPO01CFreightCandidates")
        for code in (legacy, resumable):
            self.assertIn("OpexInvestStallSecondSourceParent(lines, ss, cargo, source)", code)
            self.assertEqual(code.count("OpexInvestStallEmitSecondStation("), 2)
            self.assertEqual(code.count("stallSecond != null && sd == null"), 1)
            self.assertEqual(code.count("stallSecond != null && st == null"), 1)
            self.assertLess(code.index("stallSecond != null && sd == null"),
                            code.index("sibling != null && sd == null"))
            self.assertLess(code.index("stallSecond != null && st == null"),
                            code.index("sibling != null && st == null"))
            self.assertIn('RAIL_OPEN_REJECT", "reason=both_ends_served', code)
            self.assertIn("stats.pairsOriginServed++", code)

    def test_pair_abandon_guards_stay_before_second_station(self):
        for name, fn in (("candidates.nut", "OpexFreightCandidates"),
                         ("po01c_generators.nut", "OpexPO01CFreightCandidates")):
            code = block(source(name), fn)
            # Each industry and town destination pair still tests abandonment.
            self.assertIn('"freight|" + cargo + "|" + source.id', code)
            self.assertIn('"|t" + town.id', code)
            self.assertGreaterEqual(code.count("pairKey in abandonedPairs"), 2)

    def test_too_close_exception_only_matching_parent_a(self):
        code = block(source("lines.nut"), "OpexAI::_tooClose")
        self.assertEqual(code.count('lineEnd == "A" && entry[0] == "A"'), 2)
        self.assertEqual(code.count('line.lineId == stallParent'), 2)
        self.assertIn('stationId == stallStation', code)
        self.assertIn('OpexLineStationId(line, "A") == stallStation', code)
        self.assertIn('if (d >= ORIGIN_SEPARATION) continue;', code)
        self.assertIn('OpexRememberClosest(d, MIN_SEPARATION, blocking)', code)
        self.assertNotIn('if (stallParent >= 0 && line.lineId == stallParent) continue;', code)

    def test_plan_requires_new_station_and_no_neighbour_station(self):
        code = block(source("builder_rail.nut"), "OpexInvestStallNewSourceSiteSafe")
        for token in ('AIStation.STATION_NEW', 'AIStation.IsValidStation(',
                      'AIRail.IsRailStationTile(candidate.investStallParentStationTile)',
                      'AITile.IsStationTile(AIMap.GetTileIndex(nx, ny))',
                      'local test = AITestMode();', 'AIRail.BuildRailStation('):
            self.assertIn(token, code)
        self.assertIn('for (local dx = -1; dx <= 1; dx++)', code)
        self.assertIn('for (local dy = -1; dy <= 1; dy++)', code)
        self.assertIn('local approaches = [first - plan.step, last + plan.step];', code)
        self.assertIn('AIMap.DistanceManhattan(approach, end) != 1', code)
        self.assertIn('AIRail.IsRailTile(approach)', code)
        self.assertIn('AIRail.IsRailDepotTile(approach)', code)

    def test_station_search_bounded_and_proves_both_ends(self):
        code = block(source("builder_rail.nut"), "OpexInvestStallSecondStationPlans")
        for token in ('MAX_STATION_PLANS * 4', 'MAX_STATION_PLANS) break;',
                      'OpexInvestStallNewSourceSiteSafe(p, candidate)',
                      'OpexStationPlans(candidate.dst, candidate.src',
                      'event=site_ok', 'event=site_reject'):
            self.assertIn(token, code)

    def test_async_search_rechecks_site_before_spend(self):
        code = block(source("builder_rail.nut"), "OpexExecuteRailPlan")
        self.assertLess(code.index("OpexInvestStallNewSourceSiteSafe(planA, candidate)"),
                        code.index("OpexQuoteRailCapital("))
        self.assertLess(code.index("OpexInvestStallTraceIndependent(plan)"),
                        code.index("OpexQuoteRailCapital("))
        self.assertIn('("v307Prebuilt" in planB)', code)
        self.assertIn('candidate.investStallNewSource == 1', code)

    def test_new_line_cannot_reuse_an_existing_rail_tile(self):
        code = block(source("builder_rail.nut"), "OpexInvestStallTraceIndependent")
        self.assertIn('plan.tiles.len() < 3', code)
        self.assertIn('AIRail.IsRailTile(tile)', code)
        self.assertIn('AIBridge.IsBridgeTile(tile)', code)
        self.assertIn('AITunnel.IsTunnelTile(tile)', code)
        self.assertIn('AIRail.IsRailStationTile(tile)', code)
        self.assertIn('AIRail.IsRailDepotTile(tile)', code)
        self.assertIn('AITile.IsStationTile(tile)', code)

    def test_real_built_stations_have_different_ids(self):
        code = block(source("builder_rail.nut"), "OpexExecuteRailPlan")
        for token in ("newA == newB", "newA == candidate.investStallParentStationId",
                      "newB == candidate.investStallParentStationId", "OpexRollback(null, planA, planB",
                      'budget.end("build_stations")', 'event=station_built', 'event=build_ok'):
            self.assertIn(token, code)
        self.assertLess(code.index('event=station_built'), code.index('OpexBuildTrack('))

    def test_forces_safe_one_track_builder_not_double_templates(self):
        code = block(source("builder_rail.nut"), "OpexBuildLine")
        guard = code.index('if (INVEST_STALL && ("investStallNewSource" in candidate)')
        self.assertLess(guard, code.index('local v200Double'))
        self.assertIn('return OpexExecuteRailPlan(catalog, budget, candidate, plan);', code[guard:])

    def test_distance_is_freight_only_capped_and_no_global_bounds_mutation(self):
        candidates = source("candidates.nut")
        bonus = block(candidates, "OpexInvestStallFreightDistanceBonus")
        make = block(candidates, "OpexMakeCandidate")
        for token in ('kind != "freight"', 'V276_CAND_SLICES > 0',
                      '!OpexInvestStallReady()', 'years < 4', '20', '40', '60'):
            self.assertIn(token, bonus)
        for token in ('stallCap += stallBonus', 'OpexMapManhattanSpan()',
                      'stallCap > w.maxDistance', 'event=distance_keep'):
            self.assertIn(token, make)
        self.assertNotIn('bounds.railMax =', make)
        self.assertNotIn('catalog.bounds.railMax =', candidates)

    def test_distance_progression_model(self):
        for mode in ("pax", "air", "road"):
            self.assertEqual(distance_bonus(True, mode, 1977, 1970, 900000, False), 0)
        for year, expected in ((1973, 0), (1974, 20), (1975, 40),
                               (1976, 60), (1980, 60)):
            self.assertEqual(distance_bonus(True, "freight", year, 1970, 900000, False), expected)
        self.assertEqual(distance_bonus(False, "freight", 1977, 1970, 900000, False), 0)
        self.assertEqual(distance_bonus(True, "freight", 1977, 1970, 749999, False), 0)
        self.assertEqual(distance_bonus(True, "freight", 1977, 1970, 900000, True), 0)

    def test_physical_success_is_not_just_proposed_site(self):
        builder = block(source("builder_rail.nut"), "OpexExecuteRailPlan")
        self.assertLess(builder.index("event=site_reject reason=station_id"),
                        builder.index('result.ok = true;'))
        self.assertLess(builder.index('result.ok = true;'), builder.index('event=build_ok'))


if __name__ == "__main__":
    unittest.main()
