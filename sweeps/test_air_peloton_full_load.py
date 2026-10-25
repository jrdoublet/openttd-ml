"""AIR-PELOTON-1 : contrats des ordres des avions sous option explicite.

Verification statique : une simulation OpenTTD est requise pour etablir
l'execution des commandes API et leur effet economique.
"""

from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(filename):
    return (AI / filename).read_text(encoding="utf-8")


class AirPelotonFullLoadContracts(unittest.TestCase):
    def test_setting_is_opt_in_and_loaded_once(self):
        match = re.search(
            r'AddSetting\(\{\s*name = "air_peloton_full_load",.*?\}\);',
            source("info.nut"),
            re.S,
        )
        self.assertIsNotNone(match)
        for token in (
            "min_value = 0, max_value = 1",
            "easy_value = 0, medium_value = 0, hard_value = 0",
            "custom_value = 0",
        ):
            self.assertIn(token, match.group())
        self.assertEqual(source("info.nut").count("AddSetting("), 59)
        self.assertIn("AIR_PELOTON_FULL_LOAD <- false;", source("globals_pre.nut"))
        settings = source("settings.nut")
        self.assertEqual(settings.count('GetSetting("air_peloton_full_load")'), 1)
        self.assertIn(
            'AIR_PELOTON_FULL_LOAD = AIController.GetSetting("air_peloton_full_load") != 0;',
            settings,
        )

    def test_both_fresh_order_creation_paths_use_same_optional_flags(self):
        construction = source("air_construction.nut")
        fleet = source("air_fleet.nut")
        for blob, names, stations in (
            (construction, ("airFlagsA", "airFlagsB"), ("airportA", "airportB")),
            (fleet, ("flagsA", "flagsB"), ("line.stationA", "line.stationB")),
        ):
            for flag in names:
                self.assertIn(
                    f"local {flag} = AIR_PELOTON_FULL_LOAD ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;",
                    blob,
                )
            for station, flag in zip(stations, names):
                self.assertRegex(
                    blob,
                    rf"AIOrder\.AppendOrder\(\s*\w+,\s*{re.escape(station)},\s*{flag}\)",
                )

    def test_new_aircraft_orders_normalized_before_start(self):
        fleet = source("air_fleet.nut")
        construction = source("air_construction.nut")
        renewal = source("task_v252.nut")
        self.assertIn("AIOrder.IsGotoStationOrder(vehicle, 0)", fleet)
        self.assertIn("AIOrder.IsGotoStationOrder(vehicle, 1)", fleet)
        self.assertIn("AIOrder.GetOrderCount(vehicle) != 2", fleet)
        self.assertIn("AIOrder.SetOrderFlags(vehicle, pos, AIOrder.OF_FULL_LOAD_ANY)", fleet)
        self.assertIn("if (!AIR_PELOTON_FULL_LOAD) return true;", fleet)
        for blob, new_vehicle in (
            (construction, "extra"),
            (fleet, "extra"),
            (renewal, "newPlane"),
        ):
            check = f"AIR_PELOTON_FULL_LOAD && !OpexAirPelotonEnsureFullLoadOrders({new_vehicle})"
            self.assertIn(check, blob)
            # La construction démarre tous les built[] via aircraft, tandis
            # que le renfort et V252 démarrent leur avion directement.
            start_call = (
                "AIVehicle.StartStopVehicle(aircraft)"
                if blob is construction
                else f"AIVehicle.StartStopVehicle({new_vehicle})"
            )
            self.assertLess(blob.index(check), blob.index(start_call))
        self.assertIn("AIOrder.ShareOrders(extra, plane)", construction)
        self.assertIn("AIVehicle.CloneVehicle(hangar, template, !AIR_PELOTON_FULL_LOAD)", fleet)
        self.assertIn("AIOrder.CopyOrders(extra, template)", fleet)
        self.assertIn("AIOrder.CopyOrders(newPlane, bestVeh)", renewal)

    def test_adversarial_partial_flag_or_start_failure_cannot_change_existing_shared_orders(self):
        construction = source("air_construction.nut")
        fleet = source("air_fleet.nut")
        renewal = source("task_v252.nut")
        # CloneVehicle(..., true) PARTAGE les ordres. Avec l'option ON,
        # la copie indépendante (false) est obligatoire avant SetOrderFlags.
        self.assertEqual(
            construction.count("AIVehicle.CloneVehicle(fromB ? hangarB : hangar, plane, !AIR_PELOTON_FULL_LOAD)"),
            1,
        )
        self.assertEqual(
            fleet.count("AIVehicle.CloneVehicle(hangar, template, !AIR_PELOTON_FULL_LOAD)"),
            2,
        )
        self.assertNotIn("CloneVehicle(hangar, template, true)", fleet)
        self.assertNotIn("CloneVehicle(fromB ? hangarB : hangar, plane, true)", construction)
        # Sur les trois chemins BuildVehicleWithRefit, CopyOrders s'impose
        # sous option : ShareOrders ne peut créer d'alias vers le template.
        self.assertRegex(
            construction,
            r"AIR_PELOTON_FULL_LOAD\s*\? AIOrder\.CopyOrders\(extra, plane\)"
            r"\s*: AIOrder\.ShareOrders\(extra, plane\)",
        )
        self.assertRegex(
            fleet,
            r"AIR_PELOTON_FULL_LOAD\s*\? AIOrder\.CopyOrders\(extra, template\)"
            r"\s*: AIOrder\.ShareOrders\(extra, template\)",
        )
        self.assertRegex(
            fleet,
            r"AIR_PELOTON_FULL_LOAD\s*\? AIOrder\.CopyOrders\(extra, template\)"
            r"\s*: \(AIOrder\.ShareOrders\(extra, template\) \|\| AIOrder\.CopyOrders\(extra, template\)\)",
        )
        self.assertRegex(
            renewal,
            r"AIR_PELOTON_FULL_LOAD\s*\? AIOrder\.CopyOrders\(newPlane, bestVeh\)"
            r"\s*: \(AIOrder\.ShareOrders\(newPlane, bestVeh\) \|\| AIOrder\.CopyOrders\(newPlane, bestVeh\)\)",
        )
        # En échec de SetOrderFlags (1er ou 2e) et StartStopVehicle,
        # la seule vente autorisée est celle du nouvel appareil indépendant.
        self.assertIn("if (!AIOrder.SetOrderFlags(vehicle, pos, AIOrder.OF_FULL_LOAD_ANY)) return false;", fleet)
        self.assertIn("if (AIVehicle.IsStoppedInDepot(extra)) AIVehicle.SellVehicle(extra);", fleet)
        self.assertIn("if (AIVehicle.IsStoppedInDepot(newPlane)) AIVehicle.SellVehicle(newPlane);", renewal)
        self.assertIn("OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, built,", construction)
        self.assertNotIn("OpexAirPelotonEnsureFullLoadOrders(template)", fleet)
        self.assertNotIn("OpexAirPelotonEnsureFullLoadOrders(bestVeh)", renewal)

    def test_no_persistent_experimental_state_needed(self):
        # L'option est un reglage charge au Start ; les ordres appartiennent
        # au moteur OpenTTD et sont conserves dans les sauvegardes du jeu.
        self.assertNotIn("air_peloton_full_load", source("persist.nut"))
        self.assertNotIn("AIR_PELOTON_FULL_LOAD", source("persist.nut"))


if __name__ == "__main__":
    unittest.main()
