"""test_physical_counters.py - Tests unitaires et qualification empirique du décodeur physique.

Vérifie l'exactitude du décodage physique sur les fixtures réelles OpenTTD 15.3 :
- `sweeps/fixtures/c66_control_fixture_15_3.json` (avec inventaire API NoAI indépendant)
- `sweeps/fixtures/c53_real_chunks_15_3.json`

Confrontations et qualifications formelles :
1. Égalité exacte des IDs de véhicules pilotables décodés vs AIVehicleList + IsPrimaryVehicle.
2. Égalité exacte des IDs de gares décodées vs AIStationList.
3. Égalité exacte de la répartition par mode vs AIVehicle.GetVehicleType.
4. Égalité exacte des installations de gare vs AIStation.HasStationType.
5. Fail-closed absolu sur chunk manquant ou malformé (chunk_valid=False, zéro anomalie silencieuse).
6. Robustesse et détection explicite de corruption de consist (pointeur mort, boucle, composant sans common).
7. Validation stricte des masques de bits OpenTTD 15.3 (vehstatus) et des observables physiques.
"""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from physical_counters import (
    FACILITY_BITS,
    QUALIFIED_MODES,
    SCHEMA_VERSION,
    decode_stations,
    decode_vehicles,
)


class TestPhysicalCounters(unittest.TestCase):

    def setUp(self):
        self.fixtures_dir = ROOT / "sweeps" / "fixtures"
        self.c66_fixture_path = self.fixtures_dir / "c66_control_fixture_15_3.json"
        self.c53_fixture_path = self.fixtures_dir / "c53_real_chunks_15_3.json"

        self.assertTrue(self.c66_fixture_path.exists(), f"Fixture introuvable: {self.c66_fixture_path}")
        self.assertTrue(self.c53_fixture_path.exists(), f"Fixture introuvable: {self.c53_fixture_path}")

        with open(self.c66_fixture_path) as f:
            self.c66_data = json.load(f)

        with open(self.c53_fixture_path) as f:
            self.c53_data = json.load(f)

    def test_independent_api_confrontation(self):
        """Preuve empirique indépendante C66.1 : confrontation exacte chunks vs NoAI API.

        Vérifie l'égalité exacte des ensembles d'identifiants entre le décodage des chunks
        du savegame OpenTTD 15.3 et l'inventaire API NoAI pris au même instant exact.
        """
        api_inv = self.c66_data.get("api_inventory")
        self.assertIsNotNone(api_inv, "La fixture C66 doit contenir un inventaire API indépendant !")

        # 1. Confrontation des véhicules
        vehs = self.c66_data["chunks"]["VEHS"]
        dec_v = decode_vehicles(vehs, target_owner=0)

        api_prim_ids = set(api_inv["primary_vehicle_ids"])
        dec_prim_ids = {v["index"] for v in dec_v["primary_vehicles_detail"]}

        # Égalité exacte des ensembles d'IDs
        self.assertEqual(
            dec_prim_ids,
            api_prim_ids,
            f"Désaccord IDs véhicules : API={api_prim_ids - dec_prim_ids}, Chunks={dec_prim_ids - api_prim_ids}",
        )
        self.assertEqual(dec_v["primary_vehicles_count"], api_inv["primary_vehicles_count"])
        self.assertEqual(dec_v["primary_vehicles_count"], len(api_prim_ids))

        # Égalité de la répartition par mode
        self.assertEqual(dec_v["primary_vehicles_by_mode"], api_inv["primary_by_type"])

        # 2. Confrontation des gares
        stnn = self.c66_data["chunks"]["STNN"]
        dec_s = decode_stations(stnn, target_owner=0)

        api_stn_ids = set(api_inv["station_ids"])
        dec_stn_ids = set(dec_s["station_ids"])

        # Égalité exacte des ensembles d'IDs de gares
        self.assertEqual(
            dec_stn_ids,
            api_stn_ids,
            f"Désaccord IDs gares : API={api_stn_ids - dec_stn_ids}, Chunks={dec_stn_ids - api_stn_ids}",
        )
        self.assertEqual(dec_s["total_stations"], api_inv["total_stations_count"])
        self.assertEqual(dec_s["total_stations"], len(api_stn_ids))

        # 3. Confrontation des installations par station (facilities)
        api_stns = api_inv["stations_detail"]
        api_facils = {name: 0 for _, name in FACILITY_BITS}
        for s in api_stns.values():
            if s["train"]:
                api_facils["rail"] += 1
            if s["truck"]:
                api_facils["truck"] += 1
            if s["bus"]:
                api_facils["bus"] += 1
            if s["airport"]:
                api_facils["airport"] += 1
            if s["dock"]:
                api_facils["dock"] += 1

        self.assertEqual(dec_s["stations_by_facility"], api_facils)

    def test_c66_fixture_vehicles_breakdown(self):
        """Vérifie le décodage physique complet sur la fixture de contrôle C66 (OpenTTD 15.3)."""
        vehs = self.c66_data["chunks"]["VEHS"]
        dec = decode_vehicles(vehs, target_owner=0)

        self.assertEqual(dec["schema_version"], SCHEMA_VERSION)
        self.assertTrue(dec["chunk_valid"])
        self.assertIsNone(dec["chunk_error"])
        self.assertEqual(dec["total_pool_entries"], 33)
        # 33 total = 7 effets + 26 possédés
        self.assertEqual(dec["vehicle_pool_entries"], 26)
        self.assertEqual(dec["non_company_entries"]["effects"], 7)
        self.assertEqual(dec["non_company_entries"]["disasters"], 0)
        self.assertEqual(dec["non_company_entries"]["other_owners"], 0)

        # 26 possédés = 21 pilotables + 5 composants (2 wagons + 3 ombres d'avion)
        self.assertEqual(dec["primary_vehicles_count"], 21)
        self.assertEqual(dec["primary_vehicles_by_mode"]["rail"], 1)
        self.assertEqual(dec["primary_vehicles_by_mode"]["road"], 17)
        self.assertEqual(dec["primary_vehicles_by_mode"]["air"], 3)
        self.assertEqual(dec["primary_vehicles_by_mode"]["water"], 0)

        # Qualification des modes
        self.assertTrue(dec["qualified_modes"]["rail"])
        self.assertTrue(dec["qualified_modes"]["road"])
        self.assertTrue(dec["qualified_modes"]["air"])
        self.assertFalse(dec["qualified_modes"]["water"])

        # Composants exclus
        self.assertEqual(dec["components_breakdown"]["rail_wagons"], 2)
        self.assertEqual(dec["components_breakdown"]["aircraft_shadows_rotors"], 3)
        self.assertEqual(dec["components_breakdown"]["road_articulated_parts"], 0)
        self.assertEqual(dec["components_breakdown"]["water_components"], 0)

        # Zéro entrée inexpliquée ou résiduelle
        self.assertEqual(len(dec["unclassified_entries"]), 0, f"Entrées non classées: {dec['unclassified_entries']}")

        # Vérification du convoi ferroviaire (Train 12 a 2 wagons de charbon = 60t)
        rail_details = [v for v in dec["primary_vehicles_detail"] if v["mode"] == "rail"]
        self.assertEqual(len(rail_details), 1)
        train = rail_details[0]
        self.assertEqual(train["unitnumber"], 1)
        self.assertEqual(train["index"], 12)
        self.assertEqual(train["consist_indices"], [12, 14, 13])
        self.assertEqual(train["consist_capacities"], {1: 60})
        self.assertTrue(train["consist_valid"])

        # Statut observable de la flotte
        self.assertEqual(dec["fleet_status"]["stopped"], 1)
        self.assertEqual(dec["fleet_status"]["not_stopped"], 20)
        self.assertEqual(dec["fleet_status"]["running"], 20)
        self.assertEqual(dec["fleet_status"]["hidden"], 1)
        self.assertEqual(dec["fleet_status"]["broken"], 0)
        self.assertEqual(dec["fleet_status"]["crashed"], 0)
        self.assertEqual(dec["fleet_status"]["stopped"] + dec["fleet_status"]["not_stopped"], 21)

    def test_c66_fixture_stations(self):
        """Vérifie le décodage des gares et la non-duplication des gares multimodales."""
        stnn = self.c66_data["chunks"]["STNN"]
        dec = decode_stations(stnn, target_owner=0)

        self.assertEqual(dec["schema_version"], SCHEMA_VERSION)
        self.assertTrue(dec["chunk_valid"])
        self.assertIsNone(dec["chunk_error"])
        self.assertEqual(dec["total_stations"], 24)

        # 4 gares multimodales (bus + airport)
        self.assertEqual(dec["n_multimodal_stations"], 4)
        self.assertEqual(dec["multimodal_station_ids"], [0, 1, 14, 21])

        # Installations par infrastructure
        self.assertEqual(dec["stations_by_facility"]["rail"], 2)
        self.assertEqual(dec["stations_by_facility"]["truck"], 6)
        self.assertEqual(dec["stations_by_facility"]["bus"], 16)
        self.assertEqual(dec["stations_by_facility"]["airport"], 4)
        self.assertEqual(dec["stations_by_facility"]["dock"], 0)

        # Détail des stations
        self.assertEqual(len(dec["stations_detail"]), 24)
        self.assertEqual(len(dec["unresolved_stations"]), 0)
        self.assertEqual(dec["other_owner_stations"], 0)

        stnn_bad = copy.deepcopy(stnn)
        first_key = next(iter(stnn_bad))
        stnn_bad[first_key] = "not-a-station"
        dec_bad = decode_stations(stnn_bad, target_owner=0)
        self.assertFalse(dec_bad["chunk_valid"])
        self.assertIn("not_a_dict", dec_bad["chunk_error"])
        self.assertGreater(len(dec_bad["unresolved_stations"]), 0)

        stnn_all_bad = {key: "not-a-station" for key in list(stnn)[:3]}
        dec_all_bad = decode_stations(stnn_all_bad, target_owner=0)
        self.assertFalse(dec_all_bad["chunk_valid"])
        self.assertEqual(dec_all_bad["total_stations"], 0)

        # Un waypoint sans corps `normal` ne doit pas invalider le chunk.
        stnn_wp = copy.deepcopy(stnn)
        stnn_wp["waypoint-only"] = {"waypoint": [{"xy": 1}], "facilities": 0}
        dec_wp = decode_stations(stnn_wp, target_owner=0)
        self.assertTrue(dec_wp["chunk_valid"], dec_wp["chunk_error"])
        self.assertEqual(dec_wp["total_stations"], 24)

        rated = [r for ratings in dec["ratings_by_station"].values() for r in ratings]
        self.assertEqual(len(rated), 20)
        self.assertEqual(min(rated), 82)
        self.assertEqual(max(rated), 203)

    def test_fail_closed_on_missing_and_invalid_chunks(self):
        """Vérifie le principe 'fail-closed' : aucun chunk absent ne produit un faux zéro crédible."""
        # Chunk VEHS manquant (None)
        res_v_none = decode_vehicles(None, target_owner=0)
        self.assertFalse(res_v_none["chunk_valid"])
        self.assertEqual(res_v_none["chunk_error"], "chunk_missing")
        self.assertIsNone(res_v_none["primary_vehicles_count"])
        self.assertIsNone(res_v_none["vehicle_pool_entries"])
        self.assertIsNone(res_v_none["total_pool_entries"])
        self.assertIsNone(res_v_none["components_breakdown"])
        self.assertIsNone(res_v_none["non_company_entries"])
        self.assertIsNone(res_v_none["capacities_by_cargo"])
        self.assertIsNone(res_v_none["fleet_status"])
        self.assertIsNone(res_v_none["primary_vehicles_detail"])
        self.assertEqual(len(res_v_none["unclassified_entries"]), 1)
        self.assertEqual(res_v_none["unclassified_entries"][0]["reason"], "chunk_missing")

        # Chunk VEHS d'un type inattendu (chaîne ou entier)
        res_v_bad = decode_vehicles("corrupt_type", target_owner=0)
        self.assertFalse(res_v_bad["chunk_valid"])
        self.assertEqual(res_v_bad["chunk_error"], "invalid_chunk_type")
        self.assertIsNone(res_v_bad["primary_vehicles_count"])
        self.assertEqual(len(res_v_bad["unclassified_entries"]), 1)

        # Chunk STNN manquant (None)
        res_s_none = decode_stations(None, target_owner=0)
        self.assertFalse(res_s_none["chunk_valid"])
        self.assertEqual(res_s_none["chunk_error"], "chunk_missing")
        self.assertIsNone(res_s_none["total_stations"])
        self.assertIsNone(res_s_none["n_multimodal_stations"])
        self.assertIsNone(res_s_none["station_ids"])
        self.assertIsNone(res_s_none["stations_detail"])
        self.assertIsNone(res_s_none["other_owner_stations"])
        self.assertIsNone(res_s_none["ratings_by_station"])
        self.assertEqual(len(res_s_none["unresolved_stations"]), 1)
        self.assertEqual(res_s_none["unresolved_stations"][0]["reason"], "chunk_missing")

        # Chunk STNN de type inattendu
        res_s_bad = decode_stations(12345, target_owner=0)
        self.assertFalse(res_s_bad["chunk_valid"])
        self.assertEqual(res_s_bad["chunk_error"], "invalid_chunk_type")
        self.assertIsNone(res_s_bad["total_stations"])
        self.assertEqual(len(res_s_bad["unresolved_stations"]), 1)

    def test_consist_corruption_detection(self):
        """Vérifie la détection explicite et fail-closed de corruption de chaîne de consist."""
        vehs = copy.deepcopy(self.c66_data["chunks"]["VEHS"])

        # 1. Pointeur 'next' vers une cible inexistante
        # Le train 12 a next=15 (cible index 14). Remplaçons par next=9999 (index 9998 inexistant)
        vehs_corrupt_target = copy.deepcopy(vehs)
        head_common = vehs_corrupt_target["12"]["train"][0]["common"][0]
        head_common["next"] = 9999

        dec = decode_vehicles(vehs_corrupt_target, target_owner=0)
        self.assertFalse(dec["chunk_valid"])
        self.assertIn("corrupted_consist_pointer_missing_target", dec["chunk_error"])
        self.assertGreater(len(dec["unclassified_entries"]), 0)
        reasons = [e["reason"] for e in dec["unclassified_entries"]]
        self.assertIn("corrupted_consist_pointer_missing_target", reasons)
        train = [v for v in dec["primary_vehicles_detail"] if v["index"] == 12][0]
        self.assertFalse(train["consist_valid"])
        self.assertNotIn(9998, train["consist_indices"])

        # 2. Cycle dans la chaîne de consist
        # Faisons boucler le wagon 13 (dernier du convoi) sur lui-même ou sur 14
        vehs_cycle = copy.deepcopy(vehs)
        wagon_13_common = vehs_cycle["13"]["train"][0]["common"][0]
        wagon_13_common["next"] = 15  # Pointeur vers 14 (15 - 1 = 14 déjà visité)

        dec_cycle = decode_vehicles(vehs_cycle, target_owner=0)
        self.assertFalse(dec_cycle["chunk_valid"])
        self.assertIn("consist_cycle_detected", dec_cycle["chunk_error"])
        self.assertGreater(len(dec_cycle["unclassified_entries"]), 0)
        reasons_cycle = [e["reason"] for e in dec_cycle["unclassified_entries"]]
        self.assertIn("consist_cycle_detected", reasons_cycle)
        train_cycle = [v for v in dec_cycle["primary_vehicles_detail"] if v["index"] == 12][0]
        self.assertFalse(train_cycle["consist_valid"])

        # 3. Composant sans bloc common
        vehs_no_common = copy.deepcopy(vehs)
        vehs_no_common["14"]["train"][0]["common"] = []

        dec_no_common = decode_vehicles(vehs_no_common, target_owner=0)
        self.assertFalse(dec_no_common["chunk_valid"])
        self.assertGreater(len(dec_no_common["unclassified_entries"]), 0)
        reasons_no_common = [e["reason"] for e in dec_no_common["unclassified_entries"]]
        self.assertIn("missing_consist_component_common", reasons_no_common)

        # 4. Composant déjà malformé (non-dict) ciblé par next : pas d'AttributeError.
        vehs_str_comp = copy.deepcopy(vehs)
        vehs_str_comp["14"] = "not-a-vehicle"
        dec_str = decode_vehicles(vehs_str_comp, target_owner=0)
        self.assertFalse(dec_str["chunk_valid"])
        reasons_str = [e["reason"] for e in dec_str["unclassified_entries"]]
        self.assertIn("not_a_dict", reasons_str)
        self.assertIn("consist_component_not_a_dict", reasons_str)
        train_str = [v for v in dec_str["primary_vehicles_detail"] if v["index"] == 12][0]
        self.assertFalse(train_str["consist_valid"])

    def test_vehstatus_observables_and_bitmasks(self):
        """Vérifie l'exactitude des masques de bits OpenTTD 15.3 (src/vehicle_base.h)."""
        # VehState::Hidden = 0 (0x01)
        # VehState::Stopped = 1 (0x02)
        # VehState::TrainSlowing = 4 (0x10) - NE DOIT PAS être confondu avec Stopped !
        # VehState::AircraftBroken = 6 (0x40)
        # VehState::Crashed = 7 (0x80)

        # Créer un convoi de test avec chaque état
        test_vehs = {
            "0": {
                "type": 0,
                "train": [{
                    "common": [{
                        "owner": 0, "unitnumber": 1, "subtype": 1,
                        "vehstatus": 0x02,  # Stopped
                        "cur_speed": 0, "next": 0,
                    }]
                }]
            },
            "1": {
                "type": 0,
                "train": [{
                    "common": [{
                        "owner": 0, "unitnumber": 2, "subtype": 1,
                        "vehstatus": 0x10,  # TrainSlowing (NOT stopped)
                        "cur_speed": 15, "next": 0,
                    }]
                }]
            },
            "2": {
                "type": 0,
                "train": [{
                    "common": [{
                        "owner": 0, "unitnumber": 3, "subtype": 1,
                        "vehstatus": 0x01,  # Hidden
                        "cur_speed": 0, "next": 0,
                    }]
                }]
            },
            "3": {
                "type": 0,
                "train": [{
                    "common": [{
                        "owner": 0, "unitnumber": 4, "subtype": 1,
                        "vehstatus": 0x80,  # Crashed
                        "cur_speed": 0, "next": 0,
                    }]
                }]
            },
            "4": {
                "type": 3,
                "aircraft": [{
                    "common": [{
                        "owner": 0, "unitnumber": 5, "subtype": 0,
                        "vehstatus": 0x40,  # AircraftBroken
                        "cur_speed": 0, "next": 0,
                    }]
                }]
            },
        }

        dec = decode_vehicles(test_vehs, target_owner=0)
        self.assertEqual(dec["primary_vehicles_count"], 5)
        v_by_unit = {v["unitnumber"]: v for v in dec["primary_vehicles_detail"]}

        # Unit 1 : Stopped (0x02) -> is_stopped=True, is_not_stopped=False, is_running=False
        self.assertTrue(v_by_unit[1]["is_stopped"])
        self.assertFalse(v_by_unit[1]["is_not_stopped"])
        self.assertFalse(v_by_unit[1]["is_running"])
        self.assertFalse(v_by_unit[1]["is_hidden"])

        # Unit 2 : TrainSlowing (0x10) -> is_stopped=False, is_not_stopped=True, is_running=True
        self.assertFalse(v_by_unit[2]["is_stopped"])
        self.assertTrue(v_by_unit[2]["is_not_stopped"])
        self.assertTrue(v_by_unit[2]["is_running"])
        self.assertFalse(v_by_unit[2]["is_hidden"])

        # Unit 3 : Hidden (0x01) -> not stopped mais running=False car hidden
        self.assertTrue(v_by_unit[3]["is_hidden"])
        self.assertFalse(v_by_unit[3]["is_stopped"])
        self.assertTrue(v_by_unit[3]["is_not_stopped"])
        self.assertFalse(v_by_unit[3]["is_running"])

        # Unit 4 : Crashed (0x80) -> not stopped mais running=False car crashed
        self.assertTrue(v_by_unit[4]["is_crashed"])
        self.assertFalse(v_by_unit[4]["is_stopped"])
        self.assertTrue(v_by_unit[4]["is_not_stopped"])
        self.assertFalse(v_by_unit[4]["is_running"])

        # Unit 5 : Broken (0x40) -> not stopped mais running=False car broken
        self.assertTrue(v_by_unit[5]["is_broken"])
        self.assertFalse(v_by_unit[5]["is_stopped"])
        self.assertTrue(v_by_unit[5]["is_not_stopped"])
        self.assertFalse(v_by_unit[5]["is_running"])

        # Fleet status
        self.assertEqual(dec["fleet_status"]["stopped"], 1)
        self.assertEqual(dec["fleet_status"]["not_stopped"], 4)
        self.assertEqual(dec["fleet_status"]["running"], 1)
        self.assertEqual(dec["fleet_status"]["hidden"], 1)
        self.assertEqual(dec["fleet_status"]["broken"], 1)
        self.assertEqual(dec["fleet_status"]["crashed"], 1)
        self.assertEqual(dec["fleet_status"]["stopped"] + dec["fleet_status"]["not_stopped"], 5)

    def test_c53_fixture_regression(self):
        """Vérifie la non-régression sur la fixture historique C53 (2 trains dont 1 pax)."""
        chunks = self.c53_data.get("chunks", self.c53_data)
        vehs = chunks["VEHS"]
        dec = decode_vehicles(vehs, target_owner=0)

        self.assertEqual(dec["schema_version"], SCHEMA_VERSION)
        self.assertTrue(dec["chunk_valid"])
        self.assertEqual(dec["total_pool_entries"], 47)
        self.assertEqual(dec["vehicle_pool_entries"], 38)
        self.assertEqual(dec["non_company_entries"]["effects"], 9)

        # 38 possédés = 30 pilotables + 8 composants (4 wagons + 4 ombres)
        self.assertEqual(dec["primary_vehicles_count"], 30)
        self.assertEqual(dec["primary_vehicles_by_mode"]["rail"], 2)
        self.assertEqual(dec["primary_vehicles_by_mode"]["road"], 24)
        self.assertEqual(dec["primary_vehicles_by_mode"]["air"], 4)
        self.assertEqual(dec["primary_vehicles_by_mode"]["water"], 0)

        self.assertEqual(dec["components_breakdown"]["rail_wagons"], 4)
        self.assertEqual(dec["components_breakdown"]["aircraft_shadows_rotors"], 4)
        self.assertEqual(len(dec["unclassified_entries"]), 0)


if __name__ == "__main__":
    unittest.main()
