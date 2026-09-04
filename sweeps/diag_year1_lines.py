"""Diagnostic detaille de l'Annee 1 (1970) sur la graine 42 :
OpexAI vs AAAHogEx.

Identifie precisement :
- Les lignes construites par AAAHogEx (origine, destination, mode, cargo, vehicules, profit 1970)
- Les lignes construites par OpexAI
- Pourquoi OpexAI n'a pas fait les lignes d'AAAHogEx (rejets vivier, ROI, budget, mode).
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path("/home/deploy/projects/openttd-ml")
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import make_cfg, quarter_profit, year_profit

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
AAAHOGEX_DIR = "AAAHogEx-115"
TYPE_TO_MODE = {"0": "train", "1": "roadveh", "2": "ship", "3": "aircraft"}
CARGO_NAMES = {
    0: "passengers",
    1: "coal",
    2: "mail",
    3: "oil",
    4: "livestock",
    5: "goods",
    6: "grain",
    7: "wood",
    8: "iron_ore",
    9: "steel",
    10: "valuable",
}

_real_check_output = openttdlab.subprocess.check_output

def _hook(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)

openttdlab.subprocess.check_output = _hook

def _first(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value

def extract_station_info(chunks, owner=0):
    stations = {}
    stnn = chunks.get("STNN") or {}
    for st_id_str, station in stnn.items():
        st_id = int(st_id_str)
        body = _first(station.get("normal") if isinstance(station, dict) else None)
        if body is None and isinstance(station, dict):
            body = station
        if not isinstance(body, dict):
            continue
        base = _first(body.get("base"))
        if isinstance(base, dict) and base.get("owner", owner) != owner:
            continue
        town = base.get("town") if isinstance(base, dict) else None
        xy = base.get("xy") if isinstance(base, dict) else None
        name = base.get("name") if isinstance(base, dict) else ""
        if not name:
            name = f"Station_{st_id}"
        facilities = base.get("facilities", 0) if isinstance(base, dict) else 0
        stations[st_id] = {
            "id": st_id,
            "name": name,
            "town": town,
            "xy": xy,
            "facilities": facilities,
        }
    return stations

def extract_vehicles_and_routes(chunks, stations, owner=0):
    vehs_chunk = chunks.get("VEHS") or {}
    ordr_chunk = chunks.get("ORDR") or {}

    vehicles = []
    for vkey, vdata in vehs_chunk.items():
        if not isinstance(vdata, dict):
            continue
        vtype = str(vdata.get("type"))
        if vtype not in TYPE_TO_MODE:
            continue
        mode = TYPE_TO_MODE[vtype]
        body = _first(vdata.get(mode))
        common = _first((body or {}).get("common")) if isinstance(body, dict) else None
        if not isinstance(common, dict) or common.get("owner") != owner:
            continue

        vid = int(vkey)
        cargo_type = common.get("cargo_type", 0)
        cargo_name = CARGO_NAMES.get(cargo_type, f"cargo_{cargo_type}")
        profit = common.get("profit_this_year", 0)
        value = common.get("value", 0)
        cap = common.get("cargo_cap", 0)
        unitnumber = common.get("unitnumber", vid)

        visited_stations = []
        cur_order_dest = common.get("current_order.dest")
        orders_head = common.get("orders")

        curr = orders_head
        loop_guard = 0
        while curr is not None and str(curr) in ordr_chunk and loop_guard < 50:
            loop_guard += 1
            o = ordr_chunk[str(curr)]
            dest = o.get("dest")
            if dest is not None and dest in stations:
                if dest not in visited_stations:
                    visited_stations.append(dest)
            nxt = o.get("next")
            if nxt == curr or nxt is None:
                break
            curr = nxt

        if not visited_stations and cur_order_dest is not None and cur_order_dest in stations:
            visited_stations.append(cur_order_dest)

        vehicles.append({
            "id": vid,
            "unitnumber": unitnumber,
            "mode": mode,
            "cargo_type": cargo_type,
            "cargo": cargo_name,
            "profit": profit,
            "value": value,
            "capacity": cap,
            "stations": visited_stations,
        })

    routes = defaultdict(lambda: {
        "mode": "",
        "cargo": "",
        "stations": [],
        "station_names": [],
        "vehicles": 0,
        "total_profit": 0,
        "total_value": 0,
        "units": [],
    })

    for v in vehicles:
        st_tuple = tuple(sorted(v["stations"])) if v["stations"] else (f"unknown_{v['id']}",)
        key = (v["mode"], v["cargo"], st_tuple)
        r = routes[key]
        r["mode"] = v["mode"]
        r["cargo"] = v["cargo"]
        r["stations"] = list(st_tuple)
        r["station_names"] = [stations[sid]["name"] if sid in stations else str(sid) for sid in st_tuple]
        r["vehicles"] += 1
        r["total_profit"] += v["profit"]
        r["total_value"] += v["value"]
        r["units"].append(v)

    return vehicles, list(routes.values())

def keep(row):
    chunks = row["chunks"]
    player = (chunks.get("PLYR") or {}).get(0) or (chunks.get("PLYR") or {}).get("0") or {}
    closed = player.get("old_economy") or []
    last = closed[0] if closed else {}
    stations = extract_station_info(chunks, owner=0)
    vehicles, routes = extract_vehicles_and_routes(chunks, stations, owner=0)
    signs = [s["name"] for s in chunks.get("SIGN", {}).values()]

    return ({
        "arm": row["experiment"]["arm_name"],
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "company_value": last.get("company_value", 0),
        "profit_year": year_profit(closed) or 0,
        "profit_quarter": quarter_profit(last) or 0,
        "performance_history": last.get("performance_history", 0),
        "money": player.get("money", 0),
        "current_loan": player.get("current_loan", 0),
        "stations": stations,
        "vehicles": vehicles,
        "routes": routes,
        "signs": signs,
        "output": row.get("output"),
    },)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "diag_year1_lines.json")
    args = parser.parse_args()

    cfg = make_cfg(1970)
    experiments = [
        {
            "arm_name": "AAAHogEx",
            "seed": args.seed,
            "days": 365,
            "openttd_config": cfg,
            "ais": (local_folder(str(ROOT / "ai" / AAAHOGEX_DIR), "AAAHogEx", ()),),
        },
        {
            "arm_name": "OpexAI",
            "seed": args.seed,
            "days": 365,
            "openttd_config": cfg,
            "ais": (local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("decision_log", 1),)),),
        },
    ]

    print(f"=== Lancement Diagnostic An 1 (1970) sur la graine {args.seed} ===")
    results = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=2,
        result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    data_by_arm = {r["arm"]: r for r in results}

    print("\n" + "=" * 100)
    print(f"DIAGNOSTIC ANNEE 1 (1970) — GRAINE {args.seed}")
    print("=" * 100)

    for arm_name in ("AAAHogEx", "OpexAI"):
        arm_data = data_by_arm.get(arm_name)
        if not arm_data:
            continue
        print(f"\n############################# {arm_name} #############################")
        print(f"Valeur d'entreprise : {arm_data['company_value']:>10,.0f} £")
        print(f"Profit Annuel       : {arm_data['profit_year']:>10,.0f} £")
        print(f"Score officiel      : {arm_data['performance_history']}")
        print(f"Tresorerie / Emprunt: {arm_data['money']:>10,.0f} £ / {arm_data['current_loan']:>10,.0f} £")
        print(f"Total Vehicules     : {len(arm_data['vehicles'])}")
        print(f"Total Gares/Stations: {len(arm_data['stations'])}")
        print(f"Nombre de lignes/OD : {len(arm_data['routes'])}")

        print("\n--- DETAIL DES LIGNES EXPLOITEES EN 1970 ---")
        print(f"{'Mode':<9} | {'Cargo':<11} | {'Veh':>3} | {'Profit An':>11} | {'Capital':>11} | {'Gares / Destinations'}")
        print("-" * 95)
        sorted_routes = sorted(arm_data["routes"], key=lambda r: r["total_profit"], reverse=True)
        for r in sorted_routes:
            st_names = " <-> ".join(r["station_names"]) if r["station_names"] else "Station(s) non identifiee(s)"
            print(f"{r['mode']:<9} | {r['cargo']:<11} | {r['vehicles']:>3} | {r['total_profit']:>10,.0f}£ | {r['total_value']:>10,.0f}£ | {st_names}")

    opex_data = data_by_arm.get("OpexAI")
    if opex_data and opex_data.get("output"):
        print("\n" + "=" * 100)
        print("DECISIONS ET REJETS D'OPEXAI EN ANNEE 1 (EXTRAITS DU LOG)")
        print("=" * 100)
        opex_lines = opex_data["output"].splitlines()
        decisions = [line for line in opex_lines if "OPEX" in line]
        for line in decisions:
            if any(k in line for k in ("AIR_BUILD", "FEEDER_BUILD", "FEEDER_MAIL_BUILD", "RAIL_BUILD", "VIVIER_GEN", "VIVIER_REJECT", "PORTFOLIO_RANK", "VIVIER_INFUNDABLE", "FEEDER_REFUSE", "AIR_REFUSE")):
                print(" ", line.strip()[:140])

    hogex_data = data_by_arm.get("AAAHogEx")
    if hogex_data and hogex_data.get("output"):
        print("\n" + "=" * 100)
        print("CHRONOLOGIE DE CONSTRUCTION AAAHOGEX EN ANNEE 1 (EXTRAITS DU LOG)")
        print("=" * 100)
        hogex_lines = hogex_data["output"].splitlines()
        for line in hogex_lines:
            if any(k in line for k in ("BuildTrain", "BuildRoad", "BuildFirstTrain", "BuildAircraft", "ChooseEngine", "BuildRoadVehicle", "AddPlace", "RouteBuilder", "TrainRoute")):
                if not any(w in line for w in ("failed", "Cannot", "EstimateCargoProductions")):
                    print(" ", line.strip()[:140])

    with open(args.out, "w") as f:
        clean_data = {}
        for k, v in data_by_arm.items():
            clean_rec = dict(v)
            clean_rec.pop("output", None)
            clean_data[k] = clean_rec
        json.dump(clean_data, f, indent=2)
    print(f"\nRapport complet ecrit dans {args.out}")

if __name__ == "__main__":
    main()
