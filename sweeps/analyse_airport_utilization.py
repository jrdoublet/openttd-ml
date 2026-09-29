#!/usr/bin/env python3
"""Relie le résidu AIR observé à l'utilisation temporelle C61 des aéroports."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics


# OpenTTD 15.3 AirportTypes enum: 0 small, 1 large, 2 heliport,
# 3 metropolitan, 4 international, 5 commuter, 6 helidepot, 7 intercon.
SPAN_BY_TYPE = {0: 20.0, 1: 10.0, 3: 8.0, 4: 5.0, 5: 16.0, 7: 4.0}


def median(values):
    values = list(values)
    return statistics.median(values) if values else None


def band(util):
    if util < 0.50: return "<0.50"
    if util < 0.75: return "0.50-0.75"
    if util < 0.90: return "0.75-0.90"
    if util < 1.00: return "0.90-1.00"
    if util < 1.25: return "1.00-1.25"
    if util < 1.50: return "1.25-1.50"
    return ">=1.50"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    rows = json.loads(args.path.read_text(encoding="utf-8"))["measurements"]

    by_route = defaultdict(list)
    for row in rows:
        by_route[(row["seed"], row["order_list_id"])].append(row)

    route_info = {}
    station_routes = defaultdict(list)
    for key, group in by_route.items():
        by_direction = defaultdict(list)
        for row in group:
            by_direction[(row["src_station"], row["dst_station"])].append(row)
        if len(by_direction) < 2:
            continue
        leg_days = []
        for direction_rows in by_direction.values():
            leg_days.append(median(
                r["observed_days"] + r.get("wait_ticks", 0) / 74.0
                for r in direction_rows
            ))
        roundtrip = sum(leg_days)
        if roundtrip <= 0:
            continue
        sample = group[0]
        aircraft = int(sample.get("route_aircraft", 1))
        stations = {sample["src_station"], sample["dst_station"]}
        info = {"roundtrip": roundtrip, "aircraft": aircraft, "stations": stations}
        route_info[key] = info
        for station in stations:
            station_routes[(sample["seed"], station)].append((key, group))

    station_util = {}
    for skey, route_groups in station_routes.items():
        util = 0.0
        for key, group in route_groups:
            info = route_info.get(key)
            if info is None: continue
            sample = group[0]
            station = skey[1]
            if station == sample["src_station"]:
                airport_type = int(sample["src_airport_type"])
            else:
                airport_type = int(sample["dst_airport_type"])
            span = SPAN_BY_TYPE.get(airport_type, 12.0)
            util += info["aircraft"] * span / info["roundtrip"]
        station_util[skey] = util

    enriched = []
    for row in rows:
        ua = station_util.get((row["seed"], row["src_station"]), 0.0)
        ub = station_util.get((row["seed"], row["dst_station"]), 0.0)
        item = dict(row)
        item["util_max"] = max(ua, ub)
        enriched.append(item)

    buckets = defaultdict(list)
    for row in enriched:
        buckets[band(row["util_max"])].append(row)

    order = ["<0.50", "0.50-0.75", "0.75-0.90", "0.90-1.00", "1.00-1.25", "1.25-1.50", ">=1.50"]
    result = {
        "stations": len(station_util),
        "utilization": {
            "median": median(station_util.values()),
            "min": min(station_util.values()) if station_util else None,
            "max": max(station_util.values()) if station_util else None,
        },
        "bands": {},
    }
    for name in order:
        group = buckets.get(name, [])
        if not group: continue
        result["bands"][name] = {
            "n": len(group),
            "util_median": median(r["util_max"] for r in group),
            "delay_median": median(r["delay_days_corrected"] for r in group),
            "delay_mean": statistics.mean(r["delay_days_corrected"] for r in group),
            "wait_median": median(r.get("wait_ticks", 0) / 74.0 for r in group),
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
