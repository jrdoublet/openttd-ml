#!/usr/bin/env python3
"""Contrats de securite de la variante GOOD A-join (sans moteur OpenTTD)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def src(filename):
    return (AI / filename).read_text(encoding="utf-8")


def body(filename, name):
    text = src(filename)
    start = text.index("function " + name + "(")
    opening = text.index("{", start)
    level = 0
    for i in range(opening, len(text)):
        if text[i] == "{":
            level += 1
        elif text[i] == "}":
            level -= 1
            if level == 0:
                return text[start:i + 1]
    raise AssertionError(f"unterminated {name}")


class GoodSourceContracts(unittest.TestCase):
    def test_flag_single_read_default_off_at_all_difficulties(self):
        info = src("info.nut")
        setting = re.search(r'AddSetting\(\{ name = "good_source_rail_join".*?\}\);', info, re.S)
        self.assertIsNotNone(setting)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(level + "_value = 0", setting.group())
        self.assertEqual(src("settings.nut").count('GetSetting("good_source_rail_join")'), 1)
        self.assertIn("GOOD_SOURCE_RAIL_JOIN <- false;", src("globals_pre.nut"))

    def test_supply_requires_own_real_rail_non_good_at_factory_b(self):
        supply = body("candidates.nut", "OpexGoodSourceService")
        for invariant in (
            "!GOOD_SOURCE_RAIL_JOIN", 'AICargo.GetCargoLabel(cargo) != "GOOD"',
            'service.lineEnd != "B"', 'line.dstIndustry != source.id',
            'line.cargo == cargo', 'AIIndustry.IsCargoAccepted(source.id, line.cargo)',
            'AICompany.IsMine(AITile.GetOwner(line.stationB))',
            'AIStation.GetStationID(line.stationB) != stationId',
            'AIStation.HasStationType(stationId, AIStation.STATION_TRAIN)',
            'AIVehicle.IsValidVehicle(v)', 'service.blocked',
        ):
            self.assertIn(invariant, supply)
        live = body("candidates.nut", "OpexGoodSourceSupplyLive")
        self.assertIn("line.lineId != candidate.goodSourceLineId", live)
        self.assertIn("line.dstIndustry != sourceIndustry", live)
        self.assertIn("line.cargo == candidate.cargo", live)

    def test_only_industry_to_unserved_town(self):
        freight = body("candidates.nut", "OpexFreightCandidates")
        industry, town = freight.split("/* Livraison des marchandises complexes aux villes", 1)
        self.assertNotIn("OpexGoodSourceEmit(", industry)
        self.assertIn("goodSource = OpexGoodSourceService(ss, source, cargo)", industry)
        self.assertIn("if (goodSource != null && st == null)", town)
        self.assertIn("OpexGoodSourceEmit(", town)
        self.assertLess(town.index("if (goodSource != null && st == null)"),
                        town.index("if (ss != null || st != null)"))
        emit = body("candidates.nut", "OpexGoodSourceEmit")
        self.assertIn('candidate.joinEnd <- "A"', emit)
        self.assertIn("candidate.goodSourceLineId <- attached.lineId", emit)
        self.assertIn("candidate.originServed", src("candidates.nut"))

    def test_station_a_is_mandatory_and_captures_goods(self):
        build = body("builder_rail.nut", "OpexRailPlatformPlans")
        self.assertIn("strictOriginReuseJoin", build)
        self.assertIn("|| sourceGood", build)
        self.assertIn("if (strictOriginReuseJoin)", build)
        self.assertIn("OpexJoinPlatformPlans(candidate.joinPlatform, candidate.joinStationId, statsA)", build)
        self.assertIn("OpexRailPlatformCargoValue(p.anchor, p.step, p.length,", build)
        self.assertIn("candidate.cargo, catalog.railCoverage, true) > 0", build)
        self.assertLess(build.index("if (strictOriginReuseJoin)"),
                        build.index("for (local length = wanted;"))
        safe = body("builder_rail.nut", "OpexGoodSourcePlanSafe")
        self.assertIn("planA.stationId == candidate.joinStationId", safe)
        self.assertIn("OpexRailPlatformCargoValue", safe)
        self.assertIn("OpexGoodSourceStationLive(candidate)", safe)
        built = body("builder_rail.nut", "OpexGoodSourceBuiltStation")
        self.assertIn("AIStation.GetStationID(planA.anchor) == candidate.joinStationId", built)
        self.assertIn("AICompany.IsMine(AITile.GetOwner(planA.anchor))", built)
        for name in ("OpexExecuteRailPlan", "OpexV190ExecuteRailPlan"):
            self.assertEqual(body("builder_rail.nut", name).count("OpexGoodSourcePlanSafe("), 2)
            self.assertIn("OpexGoodSourceBuiltStation(candidate, planA)", body("builder_rail.nut", name))

    def test_rails_and_c80_do_not_bypass_guard(self):
        close = body("lines.nut", "OpexAI::_tooClose")
        self.assertIn('if (sameGoodStation && entry[0] == "A") continue;', close)
        self.assertIn('if (shareGoodA && entry[0] == "A" && stationId == joinStationId) continue;', close)
        self.assertIn("stationId == joinStationId", close)
        self.assertNotIn("candidate.goodSourceLineId == joinLineId", close)
        rail = src("task_rail.nut")
        self.assertIn("OpexGoodSourceSupplyLive(this._lines, candidate)", rail)
        self.assertIn('return { ok = false, reason = "good_source_invalid" };', rail)
        stock = body("task_rail.nut", "OpexAI::_revalidateRailStockPlan")
        self.assertIn("AITown.IsValidTown(candidate.dstTown)", stock)
        self.assertIn("} else if (candidate.kind != \"pax\")", stock)
        dispatch = body("builder_rail.nut", "OpexBuildLine")
        self.assertIn('&& !("goodSourceJoin" in candidate)', dispatch)


class GoodSourceCatchmentFixtures(unittest.TestCase):
    """Petite geometrie executee en Python : bassin de GOOD sur quai joint.

    La fonction native est testee par le code OpenTTD au smoke du prime. Ici les
    cas couvrent la necessite de sonder toutes les tuiles du quai dedie.
    """

    @staticmethod
    def captured(anchor, step, length, producing):
        return max((producing.get(anchor + step * i, 0) for i in range(length)), default=0)

    def test_parallel_platform_join_can_be_empty_even_if_station_serves_factory(self):
        incoming_platform = [100, 101, 102]
        new_platform = [110, 111, 112]
        goods = {100: 16, 101: 8, 102: 0, 110: 0, 111: 0, 112: 0}
        self.assertGreater(self.captured(100, 1, 3, goods), 0)
        self.assertEqual(self.captured(110, 1, 3, goods), 0)
        goods[112] = 4
        self.assertGreater(self.captured(110, 1, 3, goods), 0)

    def test_any_positive_tile_qualifies_but_zero_is_rejected(self):
        for values, expected in (((0, 0, 0), False), ((0, 8, 0), True),
                                 ((1, 0, 0), True), ((0, 0, 16), True)):
            observed = {20 + i: v for i, v in enumerate(values)}
            self.assertEqual(self.captured(20, 1, 3, observed) > 0, expected)


if __name__ == "__main__":
    unittest.main()
