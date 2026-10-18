"""Contrats de composition V257, sans moteur OpenTTD.

Ces contrôles protègent les frontières économie/construction/persistance.
Ils ne compilent pas Squirrel : smoke et exposition restent nécessaires.
"""
import re
import unittest
from pathlib import Path

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class ConsistContracts(unittest.TestCase):
    def test_one_setting_three_modes_default_off(self):
        info = read("info.nut")
        self.assertEqual(info.count('name = "v257_consist"'), 1)
        block = info.split('name = "v257_consist"', 1)[1].split("});", 1)[0]
        self.assertIn("min_value = 0, max_value = 2", block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(difficulty + "_value = 0", block)
        self.assertIn("V257_CONSIST <- 0;", read("globals_pre.nut"))
        self.assertEqual(read("settings.nut").count('GetSetting("v257_consist")'), 1)

    def test_helper_loaded_after_economy_before_candidates(self):
        main = read("main.nut")
        self.assertLess(main.index('require("rail_consist_v257.nut")'),
                        main.index('require("candidates.nut")'))

    def test_no_percentage_in_production_sizing(self):
        body = read("rail_consist_v257.nut").split("function OpexV257ObservePair", 1)[0]
        self.assertNotIn("STATION_RATING_PCT", body)
        self.assertNotIn("TOWN_CATCHMENT_SHARE_PCT", body)
        self.assertIn("n1 * wagon.capacity * trips >= monthly", body)
        self.assertIn("n2 * wagon2.capacity * trips >= secondary.monthly", body)
        source = read("candidates.nut")
        self.assertIn("if (V257_CONSIST > 0) monthly = prodA + prodB;", source)
        self.assertIn("if (V257_CONSIST > 0) mailMonthly = mailA + mailB;", source)

    def test_platform_and_game_limits_no_magic_wagon_cap(self):
        body = read("rail_consist_v257.nut")
        self.assertIn("platform > 0 ? platform : catalog.platformLength", body)
        self.assertIn("catalog.maxTrainLength < limit", body)
        self.assertIn("OpexRailNominalMaxWagons(limit)", body)
        builder = read("builder_rail.nut")
        # Le constructeur reste l'autorite pour la longueur reelle (notamment NewGRF).
        self.assertIn("AIVehicle.GetLength(car)", builder)
        self.assertIn("trainLengthLimit", builder)

    def test_mixed_mass_speed_and_dwell(self):
        body = read("rail_consist_v257.nut")
        self.assertIn("n1 * wagon.fullWeight + n2 * wagon2.fullWeight", body)
        self.assertIn("wagon2.speed < physical.speed", body)
        self.assertIn("if (dwell2 > dwell) dwell = dwell2", body)
        # Ne pas reutiliser une entree de cache dont la cle ignore le second wagon.
        self.assertIn("OpexRailEffectiveSpeed(loco, physical, total, distance);", body)

    def test_secondary_checked_on_selected_sites_before_final_economy(self):
        builder = read("builder_rail.nut").split("function OpexCompleteRailRouteAfterSearch", 1)[1]
        self.assertLess(builder.index("OpexV257ObservePair(candidate, planA, planB)"),
                        builder.index("local economics = OpexLineEconomics"))
        body = read("rail_consist_v257.nut")
        self.assertIn("AITile.GetCargoAcceptance", body)
        self.assertIn("coverage) < 8", body)
        self.assertIn("candidate.monthly2 = 0", body)
        # Une sonde de producteurs ne doit jamais etre prise pour un volume mensuel.
        self.assertNotRegex(body, r"candidate\.monthly2\s*=\s*OpexV207PlatformUnionValue")

    def test_profit_sees_constructed_counts_and_wagon_maintenance(self):
        economy = read("economy.nut")
        for field in ("wagons", "wagons2", "loco"):
            self.assertIn(field + " = consist." + field, economy)
        self.assertIn("wagons * wagon.runningCost", economy)
        self.assertIn("wagons2 * wagon2.runningCost", economy)
        self.assertIn("V257_CONSIST > 0 ? startTrains : MAX_RAIL_TRAINS", economy)

    def test_mode_one_ignores_secondary_flags(self):
        self.assertIn("if (V257_CONSIST == 1) secondary = null;", read("economy.nut"))

    def test_short_initial_plan_keeps_secondary_opportunity(self):
        self.assertIn("economics.wagons2 > 0 || V257_CONSIST == 2", read("candidates.nut"))

    def test_additions_keep_counts_and_engine_models(self):
        builder = read("builder_rail.nut")
        second = builder.split("function OpexBuildSecondTrain", 1)[1]
        self.assertIn("line.loco, line.wagons, line.platformLength", second)
        self.assertIn("line.v257Wagon", second)
        self.assertIn("line.v257Wagon2", second)
        task = read("task_rail.nut")
        self.assertIn("AIVehicle.CloneVehicle(targetDepot, modelTrain, true)", task)
        self.assertIn("built.v257Wagon <- clone", task)
        self.assertIn("built.v257Wagon2 <- clone", task)
        # Les tables API sont conservees par la projection generique Save/Load.
        persist = read("persist.nut")
        self.assertIn("local serializableLine = clone line;", persist)
        skip = persist.split("OPEX_SAVE_LINE_SKIP <-", 1)[-1].split("};", 1)[0]
        self.assertNotIn('"v257Wagon"', skip)

    def test_v190_secondary_fix_is_inert_at_zero(self):
        from test_v163_multi_cargo import _function_body
        builder = read("builder_rail.nut")
        normal = _function_body(builder, "OpexExecuteRailPlan")
        self.assertEqual(normal.count("OpexV163Cargo2(candidate), OpexV163Wagons2(candidate)"), 2)
        double = _function_body(builder, "OpexV190ExecuteRailPlan")
        self.assertEqual(double.count("V257_CONSIST > 0 ? OpexV163Wagons2(candidate) : 0"), 2)
        self.assertIn("V257_CONSIST > 0 ? OpexV163WagonsPrice(this._catalog, line) : 0",
                      read("task_rail.nut"))

    def test_existing_orders_and_rollback_preserved(self):
        builder = read("builder_rail.nut")
        self.assertIn("AIOrder.OF_FULL_LOAD_ANY", builder)
        self.assertIn("rollbackVehicles.append(car)", builder)
        self.assertIn("OpexRollback", builder)

    def test_exposure_log_requires_decision_log(self):
        task = read("task_rail.nut")
        self.assertRegex(task, r'if \(DECISION_LOG && V257_CONSIST > 0\)\s*\{\s*OpexDecide\("V257_CONSIST"')
        self.assertIn('" predicted_trains=" + candidate.trains', task)
        self.assertIn('" built_trains=" + result.trains', task)


if __name__ == "__main__":
    unittest.main()
