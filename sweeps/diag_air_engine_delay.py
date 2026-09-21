"""Mesure passive du temps aeroportuaire reel par EngineID."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
import sys

from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import make_cfg

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
TICKS_PER_DAY = 74.0
MAP_SIZE_X = 256

# OpenTTD src/table/engines.h::_orig_aircraft_vehicle_info.
# Tuples: acceleration, speed-code, name. Vanilla aircraft IDs are 215..255.
AIRCRAFT_SOURCE = [
    (18,37,"Sampson U52"), (20,37,"Coleman Count"), (35,74,"FFP Dart"), (50,181,"Yate Haugan"),
    (20,37,"Bakewell Cotswald LB-3"), (40,74,"Bakewell Luckett LB-8"), (35,74,"Bakewell Luckett LB-9"),
    (40,74,"Bakewell Luckett LB80"), (40,74,"Bakewell Luckett LB-10"), (40,74,"Bakewell Luckett LB-11"),
    (35,74,"Yate Aerospace YAC 1-11"), (40,74,"Darwin 100"), (40,74,"Darwin 200"), (40,74,"Darwin 300"),
    (40,74,"Darwin 400"), (40,74,"Darwin 500"), (40,74,"Darwin 600"), (40,74,"Guru Galaxy"),
    (40,74,"Airtaxi A21"), (40,74,"Airtaxi A31"), (40,74,"Airtaxi A32"), (40,74,"Airtaxi A33"),
    (50,74,"Yate Aerospace YAe46"), (40,74,"Dinger 100"), (40,74,"AirTaxi A34-1000"),
    (40,74,"Yate Z-Shuttle"), (40,74,"Kelling K1"), (40,74,"Kelling K6"), (40,74,"Kelling K7"),
    (40,74,"Darwin 700"), (40,181,"FFP Hyperdart 2"), (40,74,"Dinger 200"), (50,181,"Dinger 1000"),
    (18,37,"Ploddyphut 100"), (20,37,"Ploddyphut 500"), (40,74,"Flashbang X1"),
    (40,74,"Juggerplane M1"), (50,181,"Flashbang Wizzer"), (20,25,"Tricario Helicopter"),
    (20,40,"Guru X2 Helicopter"), (20,25,"Powernaut Helicopter"),
]
BASE = {
    215 + i: {
        "engine_id": 215 + i,
        "acceleration": acceleration,
        "max_speed": (speed_code * 128) // 10,
        "name": name,
    }
    for i, (acceleration, speed_code, name) in enumerate(AIRCRAFT_SOURCE)
}


def first(value):
    return value[0] if isinstance(value, list) and value else value


def station_index(chunks):
    result = {}
    stnn = (chunks or {}).get("STNN") or {}
    records = stnn.items() if isinstance(stnn, dict) else enumerate(stnn)
    for raw_id, station in records:
        if not isinstance(station, dict):
            continue
        body = first(station.get("normal"))
        base = first((body or {}).get("base")) if isinstance(body, dict) else None
        if not isinstance(base, dict) or not (int(base.get("facilities") or 0) & 8):
            continue
        try:
            station_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        result[station_id] = {
            "xy": body.get("airport.tile", base.get("xy")),
            "airport_type": body.get("airport.type"),
        }
    return result


def manhattan(tile_a, tile_b):
    if not isinstance(tile_a, int) or not isinstance(tile_b, int):
        return None
    ax, ay = tile_a % MAP_SIZE_X, tile_a // MAP_SIZE_X
    bx, by = tile_b % MAP_SIZE_X, tile_b // MAP_SIZE_X
    return abs(ax - bx) + abs(ay - by)


def order_list(chunks, common):
    head = first(common.get("orders")) if isinstance(common, dict) else None
    if head in (None, -1, 65535):
        return None
    try:
        key = str(int(head) - 1)
    except (TypeError, ValueError):
        return None
    entry = first(((chunks or {}).get("ORDL") or {}).get(key))
    if not isinstance(entry, dict) or not isinstance(entry.get("orders"), list):
        return None
    return key, entry["orders"]


def air_samples(chunks, owner=0):
    stations = station_index(chunks)
    result = []
    vehs = (chunks or {}).get("VEHS") or {}
    records = list(vehs.items() if isinstance(vehs, dict) else enumerate(vehs))
    engines_by_orders = defaultdict(set)
    for _raw_vehicle_id, record in records:
        if not isinstance(record, dict) or str(record.get("type")) != "3":
            continue
        body = first(record.get("aircraft"))
        common = first((body or {}).get("common")) if isinstance(body, dict) else None
        if not isinstance(common, dict) or common.get("owner") != owner:
            continue
        if int(common.get("unitnumber") or 0) <= 0:
            continue
        resolved = order_list(chunks, common)
        if resolved is not None:
            engines_by_orders[resolved[0]].add(common.get("engine_type"))
    for raw_vehicle_id, record in records:
        if not isinstance(record, dict) or str(record.get("type")) != "3":
            continue
        body = first(record.get("aircraft"))
        common = first((body or {}).get("common")) if isinstance(body, dict) else None
        if not isinstance(common, dict) or common.get("owner") != owner:
            continue
        if int(common.get("unitnumber") or 0) <= 0:
            continue
        engine_id = common.get("engine_type")
        spec = BASE.get(engine_id)
        if spec is None:
            continue
        resolved = order_list(chunks, common)
        if resolved is None:
            continue
        order_key, raw_orders = resolved
        # travel_time appartient a l'ORDL partagee. Une flotte mixte peut donc
        # publier un temps mesure par un autre moteur : ne pas la calibrer.
        if len(engines_by_orders[order_key]) != 1:
            continue
        orders = []
        for order in raw_orders:
            if not isinstance(order, dict):
                continue
            raw_type = order.get("type")
            if not isinstance(raw_type, int) or (raw_type & 0x0F) != 1:
                continue
            try:
                destination = int(order.get("dest"))
            except (TypeError, ValueError):
                continue
            travel_ticks = order.get("travel_time")
            if destination not in stations or not isinstance(travel_ticks, (int, float)) or travel_ticks <= 0:
                continue
            orders.append({
                "station": destination,
                "travel_ticks": float(travel_ticks),
                "wait_ticks": float(order.get("wait_time") or 0),
            })
        if len(orders) != 2:
            continue
        station_a = stations[orders[0]["station"]]
        station_b = stations[orders[1]["station"]]
        distance = manhattan(station_a["xy"], station_b["xy"])
        if not distance:
            continue
        flight_days = distance / (0.036 * (spec["max_speed"] / 4.0))
        for direction, order in enumerate(orders):
            actual_days = order["travel_ticks"] / TICKS_PER_DAY
            result.append({
                "vehicle_id": int(raw_vehicle_id),
                "order_list_id": order_key,
                "engine_id": engine_id,
                "engine_name": spec["name"],
                "acceleration": spec["acceleration"],
                "max_speed": spec["max_speed"],
                "direction": direction,
                "from_station": orders[1 - direction]["station"],
                "to_station": order["station"],
                "from_airport_type": (station_b if direction == 0 else station_a)["airport_type"],
                "to_airport_type": (station_a if direction == 0 else station_b)["airport_type"],
                "distance": distance,
                "travel_ticks": order["travel_ticks"],
                "actual_days": actual_days,
                "flight_days_model": flight_days,
                "airport_delay_days": actual_days - flight_days,
                "wait_ticks": order["wait_ticks"],
            })
    return result


def keep(row):
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "samples": air_samples(row.get("chunks") or {}),
    },)


def dedupe(rows):
    # Une mesure finale par ligne/direction. Sinon les changements successifs
    # de travel_time surponderent les lignes les plus instables.
    latest = {}
    for row in rows:
        for sample in row["samples"]:
            key = (
                row["seed"], sample["order_list_id"], sample["engine_id"], sample["direction"],
                sample["from_station"], sample["to_station"],
            )
            item = dict(sample)
            item.update(seed=row["seed"], date=row["date"])
            previous = latest.get(key)
            if previous is None or item["date"] >= previous["date"]:
                latest[key] = item
    return list(latest.values())


def stat(values):
    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def summarize(samples):
    by_engine = defaultdict(list)
    by_pair = defaultdict(list)
    for sample in samples:
        by_engine[sample["engine_id"]].append(sample["airport_delay_days"])
        pair = (sample["engine_id"], sample["from_airport_type"], sample["to_airport_type"])
        by_pair[pair].append(sample["airport_delay_days"])
    return {
        "sample_count": len(samples),
        "negative_delay_samples": sum(sample["airport_delay_days"] < 0 for sample in samples),
        "engine_counts": dict(Counter(str(sample["engine_id"]) for sample in samples)),
        "by_engine": {
            str(engine): {**BASE[engine], **stat(values)}
            for engine, values in sorted(by_engine.items())
        },
        "by_engine_airport_pair": {
            f"{engine}|{airport_a}|{airport_b}": stat(values)
            for (engine, airport_a, airport_b), values in sorted(by_pair.items(), key=lambda item: str(item[0]))
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100])
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_air_engine_delay.json")
    args = parser.parse_args()

    settings = (
        ("air_route_plane_selection", 1),
        ("air_best_equipment", 1),
        ("air_capital_frontier", 1),
        ("air_capital_frontier_probe", 0),
    )
    ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", settings)
    experiments = [
        {
            "seed": seed,
            "days": 365 * args.years,
            "openttd_config": make_cfg(1970),
            "ais": (ai,),
            "bench_arm": "delay",
        }
        for seed in args.seeds
    ]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=args.workers,
        result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    samples = dedupe(rows)
    payload = {
        "years": args.years,
        "seeds": args.seeds,
        "summary": summarize(samples),
        "samples": samples,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    print("written", args.out)


if __name__ == "__main__":
    main()
