"""Calibre le temps fixe AIR par EngineID a partir des timetables OpenTTD.

Diagnostic passif : aucune instrumentation Squirrel. OpenTTD remplit
ORDL.orders[*].travel_time avec le temps reel de l'ordre (ticks), tandis que
wait_time est separe. Pour chaque avion OpexAI on reconstruit les deux gares,
la distance OpexFlightDistance et le residu :

    airport_delay = travel_time / 74 - flight_time

Deux flight_time sont publies :
  - legacy : AIEngine.GetMaxSpeed redivise encore par 4, comme builder_air.nut ;
  - corrected : AIEngine.GetMaxSpeed tel que l'API NoAI 15.3 le renvoie deja,
    donc avec vehicle.plane_speed applique une seule fois.

Le mapping de vitesse n'est utilise que dans ce diagnostic. Il reproduit les
41 AircraftVehicleInfo du jeu de base OpenTTD 15.3 (engines.h), EngineID
215..255. La correction de production continue d'utiliser AIEngine.GetMaxSpeed.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
TICKS_PER_DAY = 74.0
PLANE_SPEED = 4
AIRCRAFT_ENGINE_BASE = 215

# OpenTTD 15.3 src/table/engines.h, _orig_aircraft_vehicle_info max_speed field.
AIRCRAFT_OLD_SPEED = [
    37, 37, 74, 181, 37, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74,
    74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 74, 181, 74, 181, 37,
    37, 74, 74, 181, 25, 40, 25,
]

CFG = """[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = 1970
map_x = 8
map_y = 8
"""


def _first(value):
    return value[0] if isinstance(value, list) and value else value


def _script_air_speed(engine_id):
    """Reproduit AIEngine.GetMaxSpeed pour les avions de base, plane_speed=4."""
    idx = int(engine_id) - AIRCRAFT_ENGINE_BASE
    if idx < 0 or idx >= len(AIRCRAFT_OLD_SPEED):
        return None
    display_speed = (AIRCRAFT_OLD_SPEED[idx] * 128) // 10
    return display_speed // PLANE_SPEED


def _tile_xy(tile, map_width=256):
    tile = int(tile)
    return tile % map_width, tile // map_width


def _flight_distance(tile_a, tile_b):
    ax, ay = _tile_xy(tile_a)
    bx, by = _tile_xy(tile_b)
    dx, dy = abs(ax - bx), abs(ay - by)
    lo, hi = min(dx, dy), max(dx, dy)
    return max(1, (lo * 414) // 1000 + hi)


def _station_index(chunks):
    result = {}
    stnn = chunks.get("STNN") or {}
    iterator = stnn.items() if isinstance(stnn, dict) else enumerate(stnn)
    for raw_sid, raw in iterator:
        if not isinstance(raw, dict):
            continue
        body = _first(raw.get("normal"))
        if not isinstance(body, dict):
            continue
        base = _first(body.get("base"))
        if not isinstance(base, dict):
            continue
        facilities = int(base.get("facilities") or 0)
        if (facilities & 8) == 0:
            continue
        try:
            sid = int(raw_sid)
        except (TypeError, ValueError):
            continue
        tile = base.get("xy")
        airport_type = body.get("airport.type")
        if tile is None or airport_type is None:
            continue
        result[sid] = {"tile": int(tile), "airport_type": int(airport_type)}
    return result


def _order_list(chunks, common):
    raw_head = _first(common.get("orders"))
    if raw_head in (None, -1, 0, 65535):
        return None
    try:
        key = str(int(raw_head) - 1)
    except (TypeError, ValueError):
        return None
    entry = (chunks.get("ORDL") or {}).get(key)
    entry = _first(entry)
    orders = entry.get("orders") if isinstance(entry, dict) else None
    return (key, orders) if isinstance(orders, list) else None


def _air_usage(chunks, stations):
    vehs = chunks.get("VEHS") or {}
    iterator = vehs.items() if isinstance(vehs, dict) else enumerate(vehs)
    station_aircraft = defaultdict(int)
    station_routes = defaultdict(set)
    route_aircraft = defaultdict(int)
    for _vehicle_id, raw in iterator:
        if not isinstance(raw, dict) or str(raw.get("type")) != "3": continue
        body = _first(raw.get("aircraft"))
        common = _first(body.get("common")) if isinstance(body, dict) else None
        if not isinstance(common, dict) or common.get("owner") != 0: continue
        if int(_first(common.get("unitnumber", 0)) or 0) <= 0: continue
        resolved = _order_list(chunks, common)
        if resolved is None: continue
        order_key, orders = resolved
        destinations = set()
        for order in orders:
            if not isinstance(order, dict): continue
            raw_type = order.get("type")
            if not isinstance(raw_type, int) or (raw_type & 0x0F) != 1: continue
            try: dest = int(order.get("dest"))
            except (TypeError, ValueError): continue
            if dest in stations: destinations.add(dest)
        if len(destinations) < 2: continue
        route_aircraft[order_key] += 1
        for dest in destinations:
            station_aircraft[dest] += 1
            station_routes[dest].add(order_key)
    return station_aircraft, station_routes, route_aircraft


def extract_measurements(chunks, seed, date):
    stations = _station_index(chunks)
    station_aircraft, station_routes, route_aircraft = _air_usage(chunks, stations)
    vehs = chunks.get("VEHS") or {}
    iterator = vehs.items() if isinstance(vehs, dict) else enumerate(vehs)
    rows = []
    for vehicle_id, raw in iterator:
        if not isinstance(raw, dict) or str(raw.get("type")) != "3":
            continue
        body = _first(raw.get("aircraft"))
        common = _first(body.get("common")) if isinstance(body, dict) else None
        if not isinstance(common, dict) or common.get("owner") != 0:
            continue
        if int(_first(common.get("unitnumber", 0)) or 0) <= 0:
            continue
        engine = common.get("engine_type")
        speed = _script_air_speed(engine) if engine is not None else None
        if speed is None or speed <= 0:
            continue
        resolved = _order_list(chunks, common)
        if resolved is None:
            continue
        order_key, orders = resolved
        station_orders = []
        for order_index, order in enumerate(orders):
            if not isinstance(order, dict):
                continue
            raw_type = order.get("type")
            if not isinstance(raw_type, int) or (raw_type & 0x0F) != 1:
                continue
            try:
                dest = int(order.get("dest"))
                travel_ticks = int(order.get("travel_time") or 0)
            except (TypeError, ValueError):
                continue
            if dest not in stations or travel_ticks <= 0:
                continue
            station_orders.append((order_index, dest, travel_ticks, int(order.get("wait_time") or 0)))
        if len(station_orders) < 2:
            continue
        for pos, (order_index, dest, travel_ticks, wait_ticks) in enumerate(station_orders):
            prev_dest = station_orders[pos - 1][1]
            if prev_dest == dest:
                continue
            src = stations[prev_dest]
            dst = stations[dest]
            distance = _flight_distance(src["tile"], dst["tile"])
            observed_days = travel_ticks / TICKS_PER_DAY
            flight_corrected = distance / (0.036 * float(speed))
            flight_legacy = distance / (0.036 * (float(speed) / 4.0))
            rows.append({
                "seed": seed,
                "date": date,
                "vehicle_id": str(vehicle_id),
                "order_list_id": order_key,
                "unitnumber": int(_first(common.get("unitnumber", 0)) or 0),
                "engine": int(engine),
                "speed_api": speed,
                "order_index": order_index,
                "src_station": prev_dest,
                "dst_station": dest,
                "src_tile": src["tile"],
                "dst_tile": dst["tile"],
                "route_aircraft": route_aircraft.get(order_key, 0),
                "src_station_aircraft": station_aircraft.get(prev_dest, 0),
                "dst_station_aircraft": station_aircraft.get(dest, 0),
                "src_station_routes": len(station_routes.get(prev_dest, set())),
                "dst_station_routes": len(station_routes.get(dest, set())),
                "src_airport_type": src["airport_type"],
                "dst_airport_type": dst["airport_type"],
                "distance": distance,
                "travel_ticks": travel_ticks,
                "wait_ticks": wait_ticks,
                "observed_days": observed_days,
                "flight_days_corrected": flight_corrected,
                "flight_days_legacy": flight_legacy,
                "delay_days_corrected": observed_days - flight_corrected,
                "delay_days_legacy": observed_days - flight_legacy,
            })
    return rows


def keep(row):
    seed = row["experiment"]["seed"]
    date = str(row["date"])
    return ({
        "seed": seed,
        "date": date,
        "measurements": extract_measurements(row.get("chunks") or {}, seed, date),
    },)


def _summary(rows, key_fn):
    buckets = defaultdict(list)
    for row in rows:
        buckets[key_fn(row)].append(row)
    result = {}
    for key, values in sorted(buckets.items(), key=lambda item: str(item[0])):
        corrected = [v["delay_days_corrected"] for v in values]
        legacy = [v["delay_days_legacy"] for v in values]
        observed = [v["observed_days"] for v in values]
        result[str(key)] = {
            "n": len(values),
            "median_delay_corrected": statistics.median(corrected),
            "mean_delay_corrected": statistics.mean(corrected),
            "min_delay_corrected": min(corrected),
            "max_delay_corrected": max(corrected),
            "median_delay_legacy": statistics.median(legacy),
            "median_observed_days": statistics.median(observed),
            "median_distance": statistics.median(v["distance"] for v in values),
            "seeds": sorted({v["seed"] for v in values}),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=1970)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results" / "diag_airport_delay_engine_5x6.json")
    args = parser.parse_args()

    # Diagnostic passif sur les vrais defaults courants. Les anciennes versions
    # de cette sonde forçaient trois politiques AIR historiques, ce qui rendait
    # leur distribution de congestion non représentative du défaut moderne.
    settings = (("decision_log", 0),)
    ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", settings)
    cfg = CFG.replace("starting_year = 1970", f"starting_year = {args.start_year}")
    experiments = [
        {"seed": seed, "days": 365 * args.years, "openttd_config": cfg, "ais": (ai,)}
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

    latest = {}
    for row in rows:
        seed = row["seed"]
        if seed not in latest or row["date"] > latest[seed]["date"]:
            latest[seed] = row
    measurements = [m for row in latest.values() for m in row["measurements"]]
    payload = {
        "start_year": args.start_year,
        "years": args.years,
        "seeds": args.seeds,
        "latest_dates": {str(seed): row["date"] for seed, row in latest.items()},
        "n_measurements": len(measurements),
        "by_engine": _summary(measurements, lambda r: r["engine"]),
        "by_engine_airports": _summary(
            measurements,
            lambda r: (r["engine"], r["src_airport_type"], r["dst_airport_type"]),
        ),
        "measurements": measurements,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("written", args.out, "measurements", len(measurements))
    for engine, summary in payload["by_engine"].items():
        print("engine", engine, summary)


if __name__ == "__main__":
    main()
