#!/usr/bin/env python3
"""Reconstruct observed AIR route headways from diag_airport_delay_engine JSON."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics


def pickup_band(headway: float) -> str:
    if headway < 7.5:
        return "130"
    if headway < 15.0:
        return "95"
    if headway < 30.0:
        return "50"
    if headway < 52.5:
        return "25"
    return "0"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.path.read_text(encoding="utf-8"))

    by_vehicle = defaultdict(list)
    for row in payload.get("measurements", []):
        by_vehicle[(row.get("seed"), row.get("vehicle_id"))].append(row)

    by_route = defaultdict(list)
    for (seed, vehicle), legs in by_vehicle.items():
        if len(legs) < 2:
            continue
        stations = tuple(sorted((legs[0]["src_station"], legs[0]["dst_station"])))
        round_trip = sum(
            float(leg["observed_days"]) + float(leg.get("wait_ticks", 0)) / 74.0
            for leg in legs[:2]
        )
        by_route[(seed, stations)].append({
            "vehicle": vehicle,
            "engine": legs[0].get("engine"),
            "round_trip_days": round_trip,
        })

    routes = []
    for (seed, stations), vehicles in sorted(by_route.items()):
        n = len(vehicles)
        round_trip = statistics.median(v["round_trip_days"] for v in vehicles)
        headway = round_trip / n
        routes.append({
            "seed": seed,
            "stations": stations,
            "vehicles": n,
            "round_trip_days": round_trip,
            "headway_days": headway,
            "pickup_points": pickup_band(headway),
            "engines": dict(Counter(str(v["engine"]) for v in vehicles)),
        })

    headways = [r["headway_days"] for r in routes]
    result = {
        "routes": len(routes),
        "headway_days": {
            "mean": statistics.mean(headways) if headways else None,
            "median": statistics.median(headways) if headways else None,
            "min": min(headways) if headways else None,
            "max": max(headways) if headways else None,
        },
        "pickup_points_counts": dict(Counter(r["pickup_points"] for r in routes)),
        "fleet_size_counts": dict(Counter(str(r["vehicles"]) for r in routes)),
        "routes_detail": routes,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
