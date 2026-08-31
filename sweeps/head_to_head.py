"""Face-a-face OpexAI / AAAHogEx dans une seule partie OpenTTD partagee."""
import argparse
import json
from pathlib import Path
import statistics

from openttdlab import bananas_ai_library, local_folder, run_experiments

from bench_v2 import (
    CFG,
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    quarter_profit,
    station_ratings,
    year_profit,
)

ROOT = Path("/work")
VEHICLE_MODES = {0: "rail", 1: "road", 2: "water", 3: "air"}


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
            "n_vehicles": sum(vehicle_owner(vehicle) == owner for vehicle in vehicles.values()),
            "n_stations": sum(station_owner(station) == owner for station in stations.values()),
            "modes": mode_profit(vehicles, owner),
        })
    return ({
        "date": str(row["date"]),
        "companies": companies,
        "openttd_output": row.get("output") or "",
    },)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--years", type=int, default=20)
    parser.add_argument("--out", type=Path, default=Path("docs/head_to_head_seed42.json"))
    parser.add_argument("--setting", action="append", default=[], metavar="CLE=VALEUR",
                        help="Réglage OpexAI supplémentaire, répétable")
    args = parser.parse_args()

    opex_settings = {"rail_expand": 1}
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
    arm_names = (f"OpexAI[{setting_label}]", "AAAHogEx")
    opex = local_folder(
        str(ROOT / "ai" / "OpexAI"),
        "OpexAI",
        settings_tuple,
    )
    aaahogex = local_folder(str(ROOT / "ai" / "AAAHogEx-115"), "AAAHogEx", ())
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=1,
        result_processor=keep,
        experiments=({
            "seed": args.seed,
            "days": 365 * args.years,
            "openttd_config": CFG,
            "ais": (opex, aaahogex),
            "head_to_head_arms": arm_names,
        },),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    rows.sort(key=lambda record: record["date"])
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "seed": args.seed,
        "years": args.years,
        "arms": list(arm_names),
        "opex_settings": opex_settings,
        "shared_game": True,
        "openttd_config": CFG,
        "summary": rows[-1]["companies"] if rows else [],
        "openttd_output": rows[-1]["openttd_output"] if rows else "",
        "series": [
            {"date": record["date"], "companies": record["companies"]}
            for record in rows
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=1) + "\n")
    for company in payload["summary"]:
        print(
            f"{company['arm']:>28} value={company['company_value']} "
            f"score={company['performance_history']} profit={company['profit_year']} "
            f"rating={company['median_station_rating']} "
            f"veh={company['n_vehicles']} st={company['n_stations']}"
        )
    print("ecrit", args.out)


if __name__ == "__main__":
    main()
