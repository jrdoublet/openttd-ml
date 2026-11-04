"""Contrats statiques de la TRANCHE 1 RAIL-LONG v3.

Le smoke moteur et les fonctionnalités 2-3 locomotives, remplacement et
extension de quais restent des étapes DISTINCTES, non qualifiées par ce test.
"""

import re
import unittest
from pathlib import Path

from rail_long_v3_off import off_source as v3_off
from rail_long_v2_off import off_source as v2_off


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def func(name, symbol):
    src = source(name)
    pos = src.index("function " + symbol + "(")
    brace = src.index("{", pos)
    depth = 0
    for index in range(brace, len(src)):
        if src[index] == "{":
            depth += 1
        if src[index] == "}":
            depth -= 1
            if depth == 0:
                return src[pos:index + 1]
    raise AssertionError(f"Unterminated function {symbol}")


class RailLongV3InitialContracts(unittest.TestCase):
    def test_opt_in_three_and_exclusive_legacy_modes(self):
        info = source("info.nut")
        setting = next(x for x in re.findall(
            r'AddSetting\(\{[^}]+\}\);', info, re.DOTALL
        ) if 'name = "rail_long"' in x)
        self.assertIn("max_value = 3", setting)
        for tier in ("easy", "medium", "hard", "custom"):
            self.assertIn(tier + "_value = 0", setting)
        self.assertIn("RAIL_LONG_V3 <- false;", source("globals_pre.nut"))
        settings = source("settings.nut")
        self.assertIn("RAIL_LONG = railLongMode == 1;", settings)
        self.assertIn("RAIL_LONG_V2 = railLongMode == 2;", settings)
        self.assertIn("RAIL_LONG_V3 = railLongMode == 3;", settings)
        self.assertEqual(settings.count('AIController.GetSetting("rail_long")'), 1)
        self.assertIn('require("rail_long_v3.nut");', source("main.nut"))

    def test_7_then_6_then_legacy_and_dynamic_cash(self):
        site = func("rail_long_v3.nut", "OpexRailLongV3SiteLength")
        self.assertIn("return limit >= 7 ? 7 : 6;", site)
        self.assertIn("catalog.maxTrainLength > 0", site)
        self.assertIn('candidate.kind != "freight"', site)
        self.assertIn("OpexV190Active()", site)
        self.assertNotIn("750000", site)
        self.assertNotIn("350000", site)
        planning = func("builder_rail.nut", "OpexRailPlatformPlans")
        self.assertIn("OpexRailLongV3SiteLength(catalog, candidate)", planning)
        self.assertIn("for (local length = railLongLength; length >= 6; length--)", planning)
        self.assertIn("OpexRailTryPlatformLength(catalog, candidate, length", planning)
        self.assertIn("RAIL_LONG_V3 ? 50000", planning)
        self.assertIn("quote.capital * 1.10", planning)
        self.assertIn('event=quote src=', planning)
        self.assertIn("for (local length = wanted; length >= floor; length--)", planning)

    def test_minimum_eight_and_two_hundred_real_units(self):
        floor = func("rail_long_v3.nut", "OpexRailLongV3WagonFloor")
        self.assertIn("max(8, OpexCeilDiv(200, wagon.capacity))", floor)
        self.assertIn("OpexRailNominalMaxWagons(platformLength)", floor)
        for wagon_capacity, platform, expected in (
            (25, 7, 8), (30, 7, 8), (20, 7, 10),
            (15, 7, 0), (25, 6, 8), (20, 6, 10),
            (25, 5, 0)
        ):
            minimum = max(8, (200 + wagon_capacity - 1) // wagon_capacity)
            answer = minimum if (platform >= 6 and minimum <= 2 * platform - 1) else 0
            self.assertEqual(answer, expected)
        economics = func("economy.nut", "OpexLineEconomics")
        self.assertIn("OpexRailLongV3WagonFloor(wagon, fixedPlatformLength)", economics)
        self.assertIn("if (correctedWagons < minimum) correctedWagons = minimum;", economics)
        self.assertIn("OpexRailLongV3MultiChoose(catalog, cargo,", economics)

    def test_traction_uses_real_loaded_freight_mass(self):
        traction = func("rail_long_v3.nut", "OpexRailLongV3SingleTractionOK")
        self.assertIn("OpexRailTrainWeight(loco, wagon, wagons)", traction)
        self.assertIn("OpexRailAcceleration(loco, wagon, wagons, 25)", traction)
        self.assertIn("OpexRailCruiseSpeed(loco, wagon, wagons)", traction)
        catalog = source("catalog.nut")
        self.assertIn("AIEngine.GetPower(e)", catalog)
        self.assertIn("AIEngine.GetMaxTractiveEffort(e)", catalog)
        self.assertIn("AICargo.GetWeight(cargo, capacity)", catalog)
        self.assertIn("cargoWeight *= this.freightTrainMultiplier", catalog)

    def test_physical_certification_precedes_start_and_rollback(self):
        checker = func("rail_long_v3.nut", "OpexRailLongV3TrainsCertified")
        for guard in (
            "AIVehicle.GetLength(train) > candidate.platformLength * 16",
            "AIVehicle.GetNumWagons(train) != locoCount + candidate.wagons",
            "AIVehicle.GetCapacity(train, candidate.cargo) < 200",
        ):
            self.assertIn(guard, checker)
        builder = source("builder_rail.nut")
        self.assertEqual(builder.count("OpexRailLongV3TrainsCertified(candidate, trains, catalog)"), 2)
        build_start = builder.index("function OpexBuildTrains(")
        normal = builder[builder.index("function OpexExecuteRailPlan"):] if "function OpexExecuteRailPlan" in builder else builder[build_start:]
        self.assertIn("OpexRollback(tiles, planA, planB, depot, trains.rollbackVehicles)", normal)
        self.assertIn("trains.failure = \"LENGTH\"", builder)
        self.assertIn("AIVehicle.StartStopVehicle(train)", builder)
        metadata = func("task_rail.nut", "OpexAI::_recordRailAttempt")
        self.assertIn('event=build line=', metadata)
        self.assertIn('builtV3.rawset("railLongV3", true)', metadata)

    def test_v1_v2_off_projection_is_idempotent_without_rewriting_fixtures(self):
        for name in ("globals_pre.nut", "info.nut", "settings.nut", "main.nut",
                     "builder_rail.nut", "economy.nut", "task_rail.nut"):
            with self.subTest(name=name):
                current = source(name)
                v3 = v3_off(name, current)
                self.assertEqual(v3_off(name, v3), v3)
                self.assertNotIn("RAIL_LONG_V3", v3)
                self.assertNotIn("railLongV3", v3)
                self.assertEqual(v2_off(name, current), v2_off(name, v3))

    def test_legacy_v2_and_invest_stall_are_isolated(self):
        v3 = source("rail_long_v3.nut")
        self.assertNotIn("AIVehicle.MoveWagon(", v3)
        self.assertNotIn("AIVehicle.BuildVehicle(", v3)
        self.assertNotIn("AIVehicle.SellVehicle(", v3)
        self.assertIn("if (!RAIL_LONG_V2", func(
            "task_rail_long_v2.nut", "OpexRailLongV2Select"))
        self.assertIn("if (!INVEST_STALL", func(
            "invest_stall_fleet.nut", "OpexInvestStallFleetSelect"))


if __name__ == "__main__":
    unittest.main()
