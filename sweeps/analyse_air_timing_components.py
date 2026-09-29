#!/usr/bin/env python3
"""Décompose le cycle AIR observé: croisière, manœuvres aéroportuaires et attente/chargement."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

TICKS_PER_DAY = 74.0


def stat(values):
    values = [float(v) for v in values]
    if not values:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "n": len(values), "mean": statistics.mean(values),
        "median": statistics.median(values), "min": min(values), "max": max(values),
    }


def enrich(row):
    out = dict(row)
    out["wait_days"] = float(row.get("wait_ticks", 0)) / TICKS_PER_DAY
    out["cycle_one_way_days"] = float(row["observed_days"]) + out["wait_days"]
    out["maneuver_observed_days"] = float(row["delay_days_corrected"])
    out["station_aircraft_max"] = max(
        int(row.get("src_station_aircraft", 0)), int(row.get("dst_station_aircraft", 0))
    )
    out["station_routes_max"] = max(
        int(row.get("src_station_routes", 0)), int(row.get("dst_station_routes", 0))
    )
    return out


def block(group):
    return {
        "n": len(group),
        "cruise_days_corrected": stat(r["flight_days_corrected"] for r in group),
        "maneuver_observed_days": stat(r["maneuver_observed_days"] for r in group),
        "loading_wait_days": stat(r["wait_days"] for r in group),
        "travel_without_loading_days": stat(r["observed_days"] for r in group),
        "one_way_cycle_with_loading_days": stat(r["cycle_one_way_days"] for r in group),
        "station_aircraft_max": stat(r.get("station_aircraft_max", 0) for r in group),
        "station_routes_max": stat(r.get("station_routes_max", 0) for r in group),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.path.read_text(encoding="utf-8"))
    rows = [enrich(row) for row in payload.get("measurements", [])]
    low_load = [
        row for row in rows
        if row.get("station_aircraft_max", 0) <= 7 and row.get("station_routes_max", 0) <= 6
    ]
    by_engine = defaultdict(list)
    by_engine_low = defaultdict(list)
    by_aircraft_load = defaultdict(list)
    by_route_load = defaultdict(list)
    for row in rows:
        by_engine[str(row.get("engine"))].append(row)
        by_aircraft_load[str(row.get("station_aircraft_max", 0))].append(row)
        by_route_load[str(row.get("station_routes_max", 0))].append(row)
    for row in low_load:
        by_engine_low[str(row.get("engine"))].append(row)
    result = {
        "airport_pairs": dict(Counter(f"{r.get('src_airport_type')}->{r.get('dst_airport_type')}" for r in rows)),
        "overall": block(rows),
        "low_load": block(low_load),
        "by_engine": {engine: block(group) for engine, group in sorted(by_engine.items())},
        "by_engine_low_load": {
            engine: block(group) for engine, group in sorted(by_engine_low.items())
        },
        "by_station_aircraft_max": {
            key: block(group) for key, group in sorted(by_aircraft_load.items(), key=lambda kv: int(kv[0]))
        },
        "by_station_routes_max": {
            key: block(group) for key, group in sorted(by_route_load.items(), key=lambda kv: int(kv[0]))
        },
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
