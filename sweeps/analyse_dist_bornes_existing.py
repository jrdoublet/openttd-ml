"""DIST-BORNES-1: snapshot-only distance/profit audit, without game runs.

The station-to-station Manhattan distance is a geometric proxy, not the
physical road/rail path length or OpenTTD's AIR_BUILD flight distance.
"""

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def distance_from_stations(line, width):
    tiles = line.get("ordered_station_tiles")
    if not isinstance(tiles, list) or len(tiles) < 2 or width <= 0:
        return None
    if not all(isinstance(tile, int) and not isinstance(tile, bool)
               and 0 <= tile < width * width for tile in (tiles[0], tiles[-1])):
        return None
    x0, y0 = tiles[0] % width, tiles[0] // width
    x1, y1 = tiles[-1] % width, tiles[-1] // width
    return abs(x0 - x1) + abs(y0 - y1)


def collect(path, width, year):
    snapshots = {}
    with Path(path).open(encoding="utf-8") as stream:
        for line_no, raw in enumerate(stream, 1):
            row = json.loads(raw)
            stamp = row.get("date", "")
            if not isinstance(stamp, str) or not stamp.startswith(f"{year}-"):
                continue
            identity = tuple(row["run"])
            key = (row.get("duel_policy_id"), identity)
            if key in snapshots and snapshots[key]["date"] == stamp and snapshots[key] != row:
                raise ValueError(f"{path}:{line_no}: conflicting equal-date snapshot {key}")
            if key not in snapshots or stamp > snapshots[key]["date"]:
                snapshots[key] = row
    groups = defaultdict(lambda: {"games": set(), "lines": [], "no_distance": 0})
    for (policy, identity), row in snapshots.items():
        telem = row.get("line_telemetry")
        if not isinstance(telem, dict) or telem.get("ok") is not True:
            continue
        group = (identity[0], policy)
        groups[group]["games"].add((identity[1], identity[2]))
        for line in telem.get("lines", []):
            dist = distance_from_stations(line, width)
            mode = line.get("mode", "unknown")
            if dist is None:
                groups[(identity[0], policy, mode)]["no_distance"] += 1
                continue
            data = groups[(identity[0], policy, mode)]
            data["games"].add((identity[1], identity[2]))
            data["lines"].append((dist, line.get("profit_this_year_gbp"), line.get("profit_last_year_gbp")))
    result = {}
    for key, data in sorted(groups.items(), key=lambda x: str(x[0])):
        if len(key) != 3:
            continue
        lines = data["lines"]
        dists = [p[0] for p in lines]
        profits_ytd = [p[1] for p in lines if isinstance(p[1], (int, float))]
        profits_prior = [p[2] for p in lines if isinstance(p[2], (int, float))]
        result["|".join(str(k) for k in key)] = {
            "games_with_lines": len(data["games"]), "lines": len(lines),
            "missing_distance": data["no_distance"],
            "min_manhattan_station": min(dists) if dists else None,
            "median_manhattan_station": statistics.median(dists) if dists else None,
            "max_manhattan_station": max(dists) if dists else None,
            "bands_station": {
                "0-7": sum(d <= 7 for d in dists),
                "8-160": sum(8 <= d <= 160 for d in dists),
                "161-200": sum(161 <= d <= 200 for d in dists),
                "201+": sum(d > 200 for d in dists),
            },
            "profit_ytd_observed": len(profits_ytd),
            "profit_ytd_total_gbp": round(sum(profits_ytd), 2),
            "profit_prior_observed": len(profits_prior),
            "profit_prior_total_gbp": round(sum(profits_prior), 2),
        }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", nargs="+", type=Path)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--year", type=int, default=1974)
    opts = parser.parse_args()
    print(json.dumps({str(path): collect(path, opts.width, opts.year)
                      for path in opts.jsonl}, indent=2, ensure_ascii=False))
