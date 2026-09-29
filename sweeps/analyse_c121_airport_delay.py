#!/usr/bin/env python3
"""Diagnostique le résidu AIR réel face au helper de manoeuvre C100.1.

Les dimensions viennent de OpenTTD 15.3 src/table/airport_defaults.h.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics

TICKS_PER_DAY = 74.0
TILE_SPEED_SCALE = 1.6
AIRPORT_WH = {
    0: (4, 3), 1: (6, 6), 3: (6, 6),
    4: (7, 7), 5: (5, 4), 7: (9, 11),
}

def c100_maneuver_days(row):
    src, dst, speed = row.get("src_airport_type"), row.get("dst_airport_type"), row.get("speed_api")
    if src not in AIRPORT_WH or dst not in AIRPORT_WH or not isinstance(speed, (int, float)) or speed <= 0:
        return None
    ground_tiles = (sum(AIRPORT_WH[src]) + sum(AIRPORT_WH[dst])) * (2.0 / 3.0)
    taxi_days = ground_tiles * 4096.0 / (TICKS_PER_DAY * TILE_SPEED_SCALE * min(float(speed), 50.0))
    return taxi_days + 300.0 / TICKS_PER_DAY

def stats(values):
    vals = sorted(float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(float(v)))
    if not vals:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None}
    def q(frac):
        pos = (len(vals) - 1) * frac
        lo, hi = int(math.floor(pos)), int(math.ceil(pos))
        return vals[lo] if lo == hi else vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)
    return {"n": len(vals), "mean": statistics.fmean(vals), "median": statistics.median(vals),
            "p25": q(0.25), "p75": q(0.75)}

def summarize(group):
    return {
        "delay_days_corrected": stats([r["delay_days_corrected"] for r in group]),
        "c100_maneuver_days": stats([r["c100_maneuver_days"] for r in group]),
        "actual_over_c100_maneuver": stats([r["actual_over_c100_maneuver"] for r in group]),
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    rows = []
    for row in payload.get("measurements", []):
        pred, actual = c100_maneuver_days(row), row.get("delay_days_corrected")
        if pred is None or not isinstance(actual, (int, float)) or pred <= 0:
            continue
        max_routes = max(int(row.get("src_station_routes", 0)), int(row.get("dst_station_routes", 0)))
        rows.append({**row, "c100_maneuver_days": pred, "actual_over_c100_maneuver": actual / pred,
                     "max_station_routes": max_routes,
                     "max_station_aircraft": max(int(row.get("src_station_aircraft", 0)),
                                                int(row.get("dst_station_aircraft", 0)))})
    by_airports, by_route_band = defaultdict(list), defaultdict(list)
    for row in rows:
        by_airports[(row["src_airport_type"], row["dst_airport_type"])].append(row)
        routes = row["max_station_routes"]
        by_route_band["<=3" if routes <= 3 else ("4-5" if routes <= 5 else ">=6")].append(row)
    result = {
        "source": args.input.name,
        "model": "C100.1 dimensions + taxi cap 50 + 300 ticks vertical",
        "overall": summarize(rows),
        "by_airports": {f"{a}->{b}": summarize(g) for (a, b), g in sorted(by_airports.items())},
        "by_max_station_routes": {k: summarize(g) for k, g in sorted(by_route_band.items())},
        "rows": rows,
    }
    out = args.out or args.input.with_name(args.input.stem + "_summary.json")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    print(f"Sortie: {out}")

if __name__ == "__main__":
    main()
