"""Face-a-face OpexAI / AAAHogEx dans une seule partie OpenTTD partagee."""
import argparse
import json
import math
from pathlib import Path
import statistics

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

from physical_counters import decode_stations, decode_vehicles

from bench_v2 import (
    CFG,
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    make_cfg,
    quarter_profit,
    station_ratings,
    year_profit,
)

ROOT = Path("/work")
VEHICLE_MODES = {0: "rail", 1: "road", 2: "water", 3: "air"}
CAPTURE_OUTPUT = False


def first(value):
    if isinstance(value, list):
        return value[0] if value else None
    if isinstance(value, dict):
        if "owner" in value or "common" in value or "base" in value:
            return value
        return next(iter(value.values()), None)
    return value


def vehicle_common(vehicle):
    if not isinstance(vehicle, dict):
        return None
    for kind in ("train", "roadveh", "ship", "aircraft"):
        body = first(vehicle.get(kind))
        if not isinstance(body, dict):
            continue
        common = first(body.get("common"))
        if isinstance(common, dict):
            return common
    return None


def vehicle_owner(vehicle):
    common = vehicle_common(vehicle)
    return common.get("owner") if common is not None else None


def mode_profit(vehicles, owner):
    modes = {
        mode: {"n_lead_vehicles": 0, "profit_last_year": 0}
        for mode in VEHICLE_MODES.values()
    }
    for vehicle in vehicles.values():
        common = vehicle_common(vehicle)
        if common is None or common.get("owner") != owner:
            continue
        if common.get("unitnumber", 0) == 0:
            continue
        mode = VEHICLE_MODES.get(vehicle.get("type"))
        if mode is None:
            continue
        modes[mode]["n_lead_vehicles"] += 1
        # VEHS conserve Money avec 8 bits fractionnaires, contrairement a PLYR.
        raw_profit = common.get("profit_last_year") or 0
        modes[mode]["profit_last_year"] += round(raw_profit / 256)
    return modes


def station_owner(station):
    if not isinstance(station, dict):
        return None
    body = first(station.get("normal"))
    if body is None:
        body = station
    if not isinstance(body, dict):
        return None
    base = first(body.get("base"))
    return base.get("owner") if isinstance(base, dict) else None


def keep(row):
    chunks = row["chunks"]
    players = chunks.get("PLYR") or {}
    vehicles = chunks.get("VEHS") or {}
    stations = chunks.get("STNN") or {}
    companies = []
    for owner, arm in enumerate(row["experiment"]["head_to_head_arms"]):
        player = players.get(owner) or players.get(str(owner)) or {}
        closed = player.get("old_economy") or []
        latest = closed[0] if closed else {}
        ratings = station_ratings(chunks, owner)
        veh_dec = decode_vehicles(vehicles, target_owner=owner)
        stn_dec = decode_stations(stations, target_owner=owner)
        companies.append({
            "arm": arm,
            "owner": owner,
            "company_value": latest.get("company_value"),
            "performance_history": latest.get("performance_history"),
            "profit": quarter_profit(latest),
            "profit_year": year_profit(closed),
            "median_station_rating": statistics.median(ratings) if ratings else None,
            "money": player.get("money"),
            "current_loan": player.get("current_loan"),
            "months_of_bankruptcy": player.get("months_of_bankruptcy"),
            "n_vehicles": veh_dec["primary_vehicles_count"] if veh_dec["chunk_valid"] else None,
            "n_stations": stn_dec["total_stations"] if stn_dec["chunk_valid"] else None,
            "vehicle_pool_entries": veh_dec["vehicle_pool_entries"] if veh_dec["chunk_valid"] else None,
            "primary_vehicles_by_mode": veh_dec["primary_vehicles_by_mode"] if veh_dec["chunk_valid"] else None,
            "qualified_modes": veh_dec["qualified_modes"],
            "vehs_chunk_valid": veh_dec["chunk_valid"],
            "vehs_chunk_error": veh_dec["chunk_error"],
            "stnn_chunk_valid": stn_dec["chunk_valid"],
            "stnn_chunk_error": stn_dec["chunk_error"],
            "modes": mode_profit(vehicles, owner),
        })
    record = {
        "date": str(row["date"]),
        "companies": companies,
        "signs": [s["name"] for s in chunks.get("SIGN", {}).values()] if "SIGN" in chunks else [],
    }
    if CAPTURE_OUTPUT:
        record["openttd_output"] = row.get("output") or ""
    return (record,)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--seeds", type=int, nargs="+", default=None)
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--starting-year", type=int, default=1970)
    parser.add_argument("--map-size", type=int, default=256,
                        help="Longueur de cote, puissance de deux (defaut : 256)")
    parser.add_argument("--capture-output", action="store_true",
                        help="Capture les journaux Script niveau 4 dans le JSON (diagnostic seulement)")
    parser.add_argument("--out", type=Path, default=Path("results/head_to_head_results.json"))
    parser.add_argument("--setting", action="append", default=[], metavar="CLE=VALEUR",
                        help="Réglage OpexAI supplémentaire, répétable")
    args = parser.parse_args()

    global CAPTURE_OUTPUT
    CAPTURE_OUTPUT = args.capture_output

    if args.map_size < 64 or args.map_size & (args.map_size - 1):
        parser.error("--map-size doit etre une puissance de deux d'au moins 64")
    map_exponent = int(math.log2(args.map_size))

    if CAPTURE_OUTPUT:
        real_check_output = openttdlab.subprocess.check_output

        def check_output_with_script_debug(command, *rest, **kwargs):
            command = tuple(command)
            if any(str(arg).startswith("-vnull") for arg in command):
                command = command[:1] + ("-d", "script=4") + command[1:]
            return real_check_output(command, *rest, **kwargs)

        openttdlab.subprocess.check_output = check_output_with_script_debug

    seeds = args.seeds if args.seeds is not None else ([args.seed] if args.seed is not None else [42])

    opex_settings = {}
    for raw in args.setting:
        if "=" not in raw:
            parser.error(f"--setting attend CLE=VALEUR, reçu {raw!r}")
        key, value = raw.split("=", 1)
        try:
            opex_settings[key.strip()] = int(value)
        except ValueError:
            parser.error(f"valeur entière attendue pour --setting {raw!r}")
    settings_tuple = tuple(opex_settings.items())
    setting_label = ",".join(f"{key}={value}" for key, value in settings_tuple)
    arm_names = (f"OpexAI[{setting_label}]" if setting_label else "OpexAI", "AAAHogEx")
    opex = local_folder(
        str(ROOT / "ai" / "OpexAI"),
        "OpexAI",
        settings_tuple,
    )
    aaahogex = local_folder(str(ROOT / "ai" / "AAAHogEx-115"), "AAAHogEx", ())
    cfg = make_cfg(args.starting_year)
    default_map = "map_x = 8\nmap_y = 8\n"
    requested_map = f"map_x = {map_exponent}\nmap_y = {map_exponent}\n"
    if default_map not in cfg:
        raise RuntimeError("configuration de carte par defaut introuvable dans make_cfg")
    cfg = cfg.replace(default_map, requested_map, 1)
    
    experiments = tuple(
        {
            "seed": s,
            "days": 365 * args.years,
            "openttd_config": cfg,
            "ais": (opex, aaahogex),
            "head_to_head_arms": arm_names,
        }
        for s in seeds
    )

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=min(len(seeds), 4),
        result_processor=keep,
        experiments=experiments,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    rows.sort(key=lambda record: record["date"])
    
    # Structure per seed
    results_by_seed = {}
    for r in rows:
        # group by seed
        # each row has companies
        results_by_seed[str(r.get("date"))] = r

    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "seeds": seeds,
        "years": args.years,
        "starting_year": args.starting_year,
        "map_size": args.map_size,
        "map_exponent": map_exponent,
        "arms": list(arm_names),
        "opex_settings": opex_settings,
        "shared_game": True,
        "openttd_config": cfg,
        "runs": [
            {
                "date": record["date"],
                "companies": record["companies"],
                "signs": record.get("signs", []),
                **({"openttd_output": record.get("openttd_output", "")} if CAPTURE_OUTPUT else {}),
            }
            for record in rows
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"=== FACE-A-FACE PARTAGE ({args.starting_year}, {args.years} ANS, {len(seeds)} GRAINES, {args.map_size}x{args.map_size}) ===")
    for record in rows:
        print(f"--- Run {record['date']} ---")
        for company in record["companies"]:
            print(
                f"{company['arm']:>28} value={company['company_value']} "
                f"score={company['performance_history']} profit={company['profit_year']} "
                f"rating={company['median_station_rating']} "
                f"veh={company['n_vehicles']} st={company['n_stations']}"
            )
    print("ecrit", args.out)


if __name__ == "__main__":
    main()
