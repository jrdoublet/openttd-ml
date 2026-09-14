"""generate_c66_control_fixture.py - Génère la fixture de contrôle C66 avec inventaire API indépendant.

Ce script exécute une partie de contrôle (graine 42, 1 an, OpenTTD 15.3), intercepte
l'inventaire API indépendant (AIVehicleList, IsPrimaryVehicle, AIStationList) à l'état
exact de l'autosave 1971-01-01, et produit la fixture complète vérifiée :
`sweeps/fixtures/c66_control_fixture_15_3.json`.
"""
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from physical_counters import decode_stations, decode_vehicles

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug


def generate_fixture():
    with tempfile.TemporaryDirectory() as td:
        temp_ai = Path(td) / "OpexAI"
        shutil.copytree(ROOT / "ai" / "OpexAI", temp_ai)

        main_nut = (temp_ai / "main.nut").read_text()
        main_nut = main_nut.replace(
            "  _hadAbandonsThisPass = false;",
            "  _hadAbandonsThisPass = false;\n  _lastApiDumpDate = -1;",
            1,
        )

        injection = """
    local curDate = AIDate.GetCurrentDate();
    local curY = AIDate.GetYear(curDate);
    local curM = AIDate.GetMonth(curDate);
    local curD = AIDate.GetDayOfMonth(curDate);
    if (curD >= 28) {
        this.Sleep(1);
    }
    if (curD == 1) {
        local mStr = (curM < 10) ? ("0" + curM) : ("" + curM);
        local dateIso = curY + "-" + mStr + "-01";
        if (this._lastApiDumpDate != dateIso) {
            this._lastApiDumpDate = dateIso;
            AILog.Info("=== API_DUMP date=" + dateIso + " ===");
            local vl = AIVehicleList();
            AILog.Info("API_VEH_COUNT " + vl.Count());
            foreach (v, _ in vl) {
                local prim = AIVehicle.IsPrimaryVehicle(v);
                local vt = AIVehicle.GetVehicleType(v);
                local un = AIVehicle.GetUnitNumber(v);
                local inDep = AIVehicle.IsInDepot(v);
                local stpDep = AIVehicle.IsStoppedInDepot(v);
                AILog.Info("API_VEH id=" + v + " type=" + vt + " prim=" + (prim ? "1" : "0") + " unit=" + un + " in_dep=" + (inDep ? "1" : "0") + " stp_dep=" + (stpDep ? "1" : "0"));
            }
            local sl = AIStationList(AIStation.STATION_ANY);
            AILog.Info("API_STN_COUNT " + sl.Count());
            foreach (s, _ in sl) {
                local trn = AIStation.HasStationType(s, AIStation.STATION_TRAIN) ? 1 : 0;
                local trk = AIStation.HasStationType(s, AIStation.STATION_TRUCK_STOP) ? 1 : 0;
                local bus = AIStation.HasStationType(s, AIStation.STATION_BUS_STOP) ? 1 : 0;
                local air = AIStation.HasStationType(s, AIStation.STATION_AIRPORT) ? 1 : 0;
                local dok = AIStation.HasStationType(s, AIStation.STATION_DOCK) ? 1 : 0;
                AILog.Info("API_STN id=" + s + " trn=" + trn + " trk=" + trk + " bus=" + bus + " air=" + air + " dok=" + dok);
            }
        }
    }
"""
        main_nut = main_nut.replace("  while (true) {", "  while (true) {\n" + injection, 1)
        (temp_ai / "main.nut").write_text(main_nut)

        opex = local_folder(str(temp_ai), "OpexAI", ())
        cfg = "[game_creation]\nstarting_year = 1970\nmap_x = 8\nmap_y = 8\n"

        def keep_raw(row):
            return (row,)

        exps = [
            {
                "seed": 42,
                "days": 370,
                "openttd_config": cfg,
                "ais": (opex,),
                "bench_arm": "OpexAI",
                "repeat": 0,
            }
        ]

        print("Exécution de l'expérience de contrôle OpenTTD 15.3...")
        rows = list(
            run_experiments(
                openttd_version="15.3",
                opengfx_version="7.1",
                max_workers=1,
                result_processor=keep_raw,
                experiments=exps,
                ai_libraries=(
                    bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                    bananas_ai_library("5046524c", "Pathfinder.Rail"),
                ),
            )
        )

        # Extraire tous les dumps API
        all_output = "\n".join(r.get("output", "") for r in rows)
        lines = all_output.splitlines()

        dumps_by_date = {}
        current_date = None
        current_vehs = {}
        current_stns = {}

        for line in lines:
            m_header = re.search(r"=== API_DUMP date=([0-9\-]+) ===", line)
            if m_header:
                if current_date:
                    dumps_by_date[current_date] = {
                        "vehicles": current_vehs,
                        "stations": current_stns,
                    }
                current_date = m_header.group(1)
                current_vehs = {}
                current_stns = {}
                continue

            if not current_date:
                continue

            m_veh = re.search(
                r"API_VEH id=(\d+) type=(\d+) prim=(\d+) unit=(\d+) in_dep=(\d+) stp_dep=(\d+)",
                line,
            )
            if m_veh:
                vid = int(m_veh.group(1))
                current_vehs[vid] = {
                    "id": vid,
                    "type": int(m_veh.group(2)),
                    "is_primary": bool(int(m_veh.group(3))),
                    "unit": int(m_veh.group(4)),
                    "in_depot": bool(int(m_veh.group(5))),
                    "stopped_in_depot": bool(int(m_veh.group(6))),
                }
                continue

            m_stn = re.search(
                r"API_STN id=(\d+) trn=(\d+) trk=(\d+) bus=(\d+) air=(\d+) dok=(\d+)",
                line,
            )
            if m_stn:
                sid = int(m_stn.group(1))
                current_stns[sid] = {
                    "id": sid,
                    "train": bool(int(m_stn.group(2))),
                    "truck": bool(int(m_stn.group(3))),
                    "bus": bool(int(m_stn.group(4))),
                    "airport": bool(int(m_stn.group(5))),
                    "dock": bool(int(m_stn.group(6))),
                }

        if current_date:
            dumps_by_date[current_date] = {
                "vehicles": current_vehs,
                "stations": current_stns,
            }

        print(f"Dumps API capturés : {list(dumps_by_date.keys())}")

        # Sélectionner un snapshot de savegame ayant une correspondance EXACTE avec un dump API
        matching_snapshots = [r for r in rows if str(r.get("date")) in dumps_by_date]
        if not matching_snapshots:
            raise AssertionError(
                f"Aucun snapshot autosave ne correspond exactement à un dump API ! "
                f"Dates snapshots: {[r.get('date') for r in rows]}, "
                f"Dumps API: {list(dumps_by_date.keys())}"
            )

        # Prendre le snapshot le plus mûr pour une couverture multimodale maximale
        target_row = matching_snapshots[-1]
        target_date = str(target_row["date"])
        chunks = target_row["chunks"]

        assert target_date in dumps_by_date, f"Dump API manquant pour la date exacte du snapshot: {target_date}"
        api_data = dumps_by_date[target_date]
        api_vehs = api_data["vehicles"]
        api_stns = api_data["stations"]

        api_primary_ids = sorted([vid for vid, v in api_vehs.items() if v["is_primary"]])
        api_all_veh_ids = sorted(list(api_vehs.keys()))
        api_station_ids = sorted(list(api_stns.keys()))

        api_primary_by_type = {0: 0, 1: 0, 2: 0, 3: 0}
        for v in api_vehs.values():
            if v["is_primary"]:
                api_primary_by_type[v["type"]] += 1

        print(f"Snapshot et Dump API sélectionnés à la date exacte : {target_date}")
        print(f"  Total véhicules API : {len(api_all_veh_ids)}")
        print(f"  Véhicules pilotables API : {len(api_primary_ids)}")
        print(f"  Pilotables par type API : {api_primary_by_type}")
        print(f"  Gares API : {len(api_station_ids)}")

        # Décodage des chunks du savegame
        dec_v = decode_vehicles(chunks.get("VEHS"), target_owner=0)
        dec_s = decode_stations(chunks.get("STNN"), target_owner=0)

        dec_primary_ids = sorted([v["index"] for v in dec_v["primary_vehicles_detail"]])
        dec_stn_ids = sorted([s["id"] for s in dec_s["stations_detail"]])

        print("Confrontation avec le décodeur de chunks :")
        print(f"  Primary IDs match : {dec_primary_ids == api_primary_ids}")
        if dec_primary_ids != api_primary_ids:
            print(f"  Diff API - Dec : {set(api_primary_ids) - set(dec_primary_ids)}")
            print(f"  Diff Dec - API : {set(dec_primary_ids) - set(api_primary_ids)}")
            raise AssertionError("Échec de confrontation des IDs de véhicules !")

        print(f"  Station IDs match : {dec_stn_ids == api_station_ids}")
        if dec_stn_ids != api_station_ids:
            print(f"  Diff API - Dec : {set(api_station_ids) - set(dec_stn_ids)}")
            print(f"  Diff Dec - API : {set(dec_stn_ids) - set(api_station_ids)}")
            raise AssertionError("Échec de confrontation des IDs de gares !")

        # Construction du document de fixture
        fixture_payload = {
            "metadata": {
                "source": "OpenTTD 15.3 official engine run (openttdlab)",
                "seed": 42,
                "date": target_date,
                "api_dump_date": target_date,
                "ai": "OpexAI",
            },
            "api_inventory": {
                "dump_date": target_date,
                "total_vehicles_count": len(api_all_veh_ids),
                "primary_vehicles_count": len(api_primary_ids),
                "primary_vehicle_ids": api_primary_ids,
                "all_vehicle_ids": api_all_veh_ids,
                "primary_by_type": {
                    "rail": api_primary_by_type[0],
                    "road": api_primary_by_type[1],
                    "water": api_primary_by_type[2],
                    "air": api_primary_by_type[3],
                },
                "total_stations_count": len(api_station_ids),
                "station_ids": api_station_ids,
                "vehicles_detail": api_vehs,
                "stations_detail": api_stns,
            },
            "chunks": {
                "VEHS": chunks.get("VEHS"),
                "STNN": chunks.get("STNN"),
                "PLYR": chunks.get("PLYR"),
            },
        }

        out_path = ROOT / "sweeps" / "fixtures" / "c66_control_fixture_15_3.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(fixture_payload, f, indent=2)

        print(f"Fixture enregistrée avec succès dans {out_path} ({out_path.stat().st_size} octets)")


if __name__ == "__main__":
    generate_fixture()
