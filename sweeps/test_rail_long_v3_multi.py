"""Contrats statiques RAIL-LONG v3 multihead, hors OpenTTD.

La physique de reference Python verifie des cas de force/rampe/caisse,
mais NE remplace pas une execution moteur de MoveWagon et du rollback.
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
sys.path.insert(0, str(ROOT / "sweeps"))
from rail_long_v3_off import off_source as v3_off
from rail_long_v2_off import off_source as v2_off


def src(name):
    return (AI / name).read_text(encoding="utf-8")


def body(name, symbol):
    text = src(name)
    start = text.index("function " + symbol + "(")
    brace = text.index("{", start)
    nesting = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            nesting += 1
        elif text[pos] == "}":
            nesting -= 1
            if nesting == 0:
                return text[start:pos + 1]
    raise AssertionError("unclosed Squirrel function " + symbol)


def grade_speed(power_hp, te_kn, loco_weight, wagon_full, n_loco, n_wagon,
                grade, max_speed=150, wagon_speed=120):
    """Independent integer approximation of the engine's conservative limit."""
    mass = n_loco * loco_weight + n_wagon * wagon_full
    cap = min(max_speed, wagon_speed)
    def works(speed):
        air_drag = min(192, max(1, 2048 // max_speed))
        rolling = 15 * (512 + speed) / 512
        air = 14 * air_drag * (1 + 3 * (n_loco + n_wagon) / 20) * speed ** 2 / 1000
        resistance = mass * (10 + rolling) + air + mass * grade * 100
        force = min(n_loco * te_kn * 1000,
                    n_loco * power_hp * 746 * 18 / (speed * 5))
        return force > resistance
    return max((speed for speed in range(1, cap + 1) if works(speed)), default=0)


class MultiPhysicalContracts(unittest.TestCase):
    def test_1_2_3_loco_count_and_realistic_grade(self):
        self.assertEqual([14 - n for n in (1, 2, 3)], [13, 12, 11])
        self.assertGreater(grade_speed(1800, 80, 80, 25, 2, 8, 3), 35)
        self.assertLess(grade_speed(1800, 80, 80, 25, 1, 8, 3), 35)
        self.assertLess(grade_speed(1800, 80, 80, 25, 2, 8, 5), 35)
        self.assertGreater(grade_speed(1800, 80, 80, 25, 3, 8, 5), 35)
        assert 2 * 30000 + 8 * 3000 + 50000 <= 140000
        self.assertGreater(3 * 30000 + 8 * 3000 + 50000, 140000)

    def test_catalogue_uses_loaded_freight_mass_and_engine_specs(self):
        choose = body("rail_long_v3_multi.nut", "OpexRailLongV3MultiChoose")
        depot = body("rail_long_v3_multi.nut", "OpexRailLongV3MultiDepotReady")
        grade = body("rail_long_v3_multi.nut", "OpexRailLongV3MultiGradeSpeed")
        self.assertIn("local weight = loco.weight * locoCount + wagon.fullWeight * wagons;", grade)
        self.assertIn("weight * gradePct * 100", grade)
        self.assertIn("locoCount + wagons", grade)
        self.assertIn("OpexRailForce(profile, speed)", grade)
        self.assertIn("OpexRailResistance(profile, weight", grade)
        self.assertIn("for (local count = 1; count <= 3; count++)", choose)
        self.assertIn("if (best != null) {", choose)
        self.assertIn("return best; // minimum physique en nombre de motrices", choose)
        self.assertIn("cost = profile.price + 5 * profile.runningCost", choose)
        # NoAI min(integer, integer) throws on the float from effective speed.
        self.assertIn("flatSpeed < gradeSpeed ? flatSpeed : gradeSpeed", choose)
        self.assertNotIn("min(flatSpeed, gradeSpeed)", choose)
        for item in ("AIEngine.GetPower(loco.id)", "AIEngine.GetMaxTractiveEffort(loco.id)",
                     "AIEngine.GetWeight(loco.id)", "AICargo.GetWeight(cargo,",
                     'AIGameSettings.GetValue("vehicle.freight_trains")',
                     "AIEngine.HasPowerOnRail", "AIEngine.IsArticulated",
                     "OpexRailLongV3MultiGradeSpeed(loco"):
            with self.subTest(item=item):
                self.assertIn(item, depot)
        self.assertIn("sawCashRejection", choose)
        self.assertIn("event=quote src=", body("builder_rail.nut", "OpexRailPlatformPlans"))

    def test_builder_transaction_order_length_rollback_and_orders(self):
        multi = body("rail_long_v3_multi.nut", "OpexRailLongV3MultiBuild")
        for part in ("AIVehicle.BuildVehicle(depot, loco.id)",
                     "AIVehicle.MoveWagon(second, 0, train, n - 1)",
                     "AIVehicle.MoveWagon(car, 0, train, locoCount + w - 1)",
                     "AIVehicle.GetLength(train)", "AIVehicle.GetNumWagons(train)",
                     "AIVehicle.GetWagonEngineType(train, j)",
                     "AIVehicle.IsStoppedInDepot(train)",
                     "AIOrder.AppendOrder(train, exitA, flagsA)",
                     "AIOrder.AppendOrder(train, exitB, flagsB)",
                     "rollbackVehicles.append(train)",
                     "rollbackVehicles.append(second)",
                     "rollbackVehicles.append(car)"):
            with self.subTest(part=part):
                self.assertIn(part, multi)
        self.assertLess(multi.index("AIVehicle.MoveWagon(second"),
                        multi.index("AIVehicle.BuildVehicle(depot, wagon.id)"))
        self.assertLess(multi.index("AIVehicle.GetLength(train)"),
                        multi.index("AIOrder.AppendOrder(train, exitA, flagsA)"))
        self.assertNotIn("AIVehicle.StartStopVehicle(", multi)
        self.assertNotIn("AIVehicle.SellVehicle(", multi)
        self.assertIn("return result; // start par constructeur", multi)
        main = src("builder_rail.nut")
        self.assertIn("return OpexRailLongV3MultiBuild(", main)
        self.assertEqual(main.count("OpexRailLongV3TrainsCertified(candidate, trains, catalog)"), 2)
        self.assertIn("OpexRollback(tiles, planA, planB, depot, trains.rollbackVehicles)", main)
        self.assertIn("if (RAIL_LONG_V3 && v3LocoCount > 1)", main)
        self.assertIn("wanted == 1 && kind == \"freight\" && wagons2 == 0 && !startVehicles", main)

    def test_quote_contains_all_locomotives_and_real_wagons(self):
        economics = body("economy.nut", "OpexLineEconomics")
        self.assertLess(economics.index("loco = railLongV3Multi.profile"),
                        economics.index("local vehicleCost = trains * (loco.price"))
        self.assertIn("result.railLongV3LocoCount <- railLongV3Multi.count", economics)
        self.assertIn("if (railLongV3Multi != null) maxTrains = 1", economics)
        self.assertIn("local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;", economics)
        apply = body("economy.nut", "OpexApplyRailEconomics")
        self.assertIn('candidate.rawset("railLongV3LocoCount"', apply)
        for occurrence in (
            "candidate.railLongV3LocoCount : 1);",
            "OpexRailLongV3TrainsCertified(candidate, trains, catalog)",
        ):
            self.assertIn(occurrence, src("builder_rail.nut"))
        certify = body("rail_long_v3.nut", "OpexRailLongV3TrainsCertified")
        self.assertIn("AIVehicle.GetNumWagons(train) != locoCount + candidate.wagons", certify)
        self.assertIn("AIVehicle.GetLength(train) > candidate.platformLength * 16", certify)
        self.assertIn("AIVehicle.GetCapacity(train, candidate.cargo) < 200", certify)

    def test_legacy_selectors_do_not_misread_2nd_loco_as_wagon(self):
        line_guard = body("rail_long_v3_multi.nut", "OpexRailLongV3MultiLine")
        self.assertIn('"railLongV3LocoCount" in line', line_guard)
        self.assertIn('"railLongV3Multihead" in line', line_guard)
        self.assertIn("if (OpexRailLongV3MultiLine(line)) return;",
                      body("task_v257.nut", "OpexAI::_v257Review"))
        self.assertIn("if (OpexRailLongV3MultiLine(line)) {",
                      body("task_v257.nut", "OpexAI::_v257ReplaceStep"))
        self.assertIn("if (OpexRailLongV3MultiLine(line)) continue;",
                      body("task_v284.nut", "OpexV284Select"))
        self.assertIn("pending.phase = \"rollback\";",
                      body("task_v284.nut", "OpexV284Tick"))
        self.assertIn("if (OpexRailLongV3MultiLine(line)) return 0.0;",
                      body("invest_stall.nut", "OpexInvestStallLineCapacity"))
        self.assertIn("multihead_unmodelled",
                      body("invest_stall.nut", "OpexInvestStallSourceGap"))
        self.assertIn("OpexRailLongV3MultiLine(line)",
                      body("invest_stall_fleet.nut", "OpexInvestStallFleetSelect"))
        self.assertIn("OpexRailLongV3MultiLine(mother)",
                      body("candidates.nut", "OpexInvestStallParentCanGrowWagon"))

    def test_off_projection_exact_and_idempotent_for_every_touched_file(self):
        names = ("main.nut", "builder_rail.nut", "economy.nut", "task_rail.nut",
                 "task_v257.nut", "task_v284.nut", "invest_stall.nut",
                 "invest_stall_fleet.nut", "candidates.nut",
                 "orchestrator.nut", "persist.nut")
        for name in names:
            with self.subTest(name=name):
                current = src(name)
                off = v3_off(name, current)
                self.assertEqual(off, v3_off(name, off))
                self.assertNotIn("RAIL_LONG_V3", off)
                # Retain a mode-independent Save/Load transaction guard:
                # a V3 upgrade may be pending even after the setting is off.
                # It is not a V3 multihead construction/selection path.
                pending_upgrade_guards = {
                    "task_v284.nut": 1,
                    "invest_stall_fleet.nut": 4,
                }
                if name in pending_upgrade_guards:
                    self.assertEqual(
                        off.count("_railLongV3UpgradePending"),
                        pending_upgrade_guards[name],
                    )
                    self.assertEqual(off.count("railLongV3"),
                                     pending_upgrade_guards[name])
                    self.assertNotIn("OpexRailLongV3MultiLine(", off)
                else:
                    self.assertNotIn("railLongV3", off)
                self.assertNotIn("v3LocoCount", off)
                self.assertEqual(v2_off(name, current), v2_off(name, off))

    def test_upgrade_owned_exclusively_by_worker_2(self):
        self.assertIn('require("rail_long_v3_upgrade.nut");', src("main.nut"))
        self.assertIn("if (RAIL_LONG_V3 && OpexRailLongV3UpgradeSelect(this, year)) return;",
                      body("task_rail.nut", "OpexAI::_expandRailLines"))


if __name__ == "__main__":
    unittest.main()
