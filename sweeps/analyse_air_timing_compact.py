#!/usr/bin/env python3
"""Vue compacte du diagnostic AIR timing, centrée sur la faible charge."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics


def med(values):
    values = list(values)
    return statistics.median(values) if values else None


def brief(group):
    return {
        "n": len(group),
        "delay_med": round(med(r["delay_days_corrected"] for r in group), 3) if group else None,
        "wait_med": round(med(r["wait_days"] for r in group), 3) if group else None,
        "speed_api_med": round(med(r["speed_api"] for r in group), 3) if group else None,
        "distance_med": round(med(r["distance"] for r in group), 3) if group else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    rows = json.loads(args.path.read_text(encoding="utf-8"))["measurements"]
    for row in rows:
        row["aircraft_max"] = max(row.get("src_station_aircraft", 0), row.get("dst_station_aircraft", 0))
        row["routes_max"] = max(row.get("src_station_routes", 0), row.get("dst_station_routes", 0))
        row["wait_days"] = row.get("wait_ticks", 0) / 74.0
    low = [r for r in rows if r["aircraft_max"] <= 7 and r["routes_max"] <= 6]
    by_engine = defaultdict(list)
    by_speed = defaultdict(list)
    by_airport_pair = defaultdict(list)
    for row in low:
        by_engine[str(row["engine"])].append(row)
        by_speed[str(row["speed_api"])].append(row)
        by_airport_pair[f"{row.get('src_airport_type')}->{row.get('dst_airport_type')}"] .append(row)
    print(json.dumps({
        "overall": brief(rows),
        "low_load": brief(low),
        "by_engine_low_load": {engine: brief(group) for engine, group in sorted(by_engine.items())},
        "by_speed_low_load": {
            speed: brief(group) for speed, group in sorted(by_speed.items(), key=lambda kv: float(kv[0]))
        },
        "by_airport_pair_low_load": {
            pair: brief(group) for pair, group in sorted(by_airport_pair.items())
        },
    }, indent=2))


if __name__ == "__main__":
    main()
