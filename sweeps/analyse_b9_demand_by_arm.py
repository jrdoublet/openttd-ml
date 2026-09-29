#!/usr/bin/env python3
"""Compare le proxy monthlyPax historique à la production couverte estimée, par bras AIR."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

from diag_b9_air_catchment import collect_probe_events_from_engine_logs, pair_builds


def stats(values):
    values = [float(v) for v in values]
    if not values:
        return {"n": 0, "mean": None, "median": None, "pstdev": None,
                "p25": None, "p75": None, "iqr": None, "min": None, "max": None}
    if len(values) >= 2:
        p25, _, p75 = statistics.quantiles(values, n=4, method="inclusive")
    else:
        p25 = p75 = values[0]
    return {"n": len(values), "mean": statistics.mean(values),
            "median": statistics.median(values), "pstdev": statistics.pstdev(values),
            "p25": p25, "p75": p75, "iqr": p75 - p25,
            "min": min(values), "max": max(values)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine_dir", type=Path)
    args = parser.parse_args()
    games = collect_probe_events_from_engine_logs(args.engine_dir)
    rows = defaultdict(list)
    for events in games.values():
        builds, _, _ = pair_builds(events)
        for build in builds:
            endpoints = build.get("endpoints") or []
            if len(endpoints) != 2:
                continue
            base = build.get("base_monthly")
            if not isinstance(base, (int, float)) or base <= 0:
                continue
            airport_est = [e.get("airport_pax_month_est") for e in endpoints]
            union_est = [e.get("union_pax_month_est") for e in endpoints]
            if not all(isinstance(v, (int, float)) for v in airport_est + union_est):
                continue
            airport_total = sum(airport_est)
            union_total = sum(union_est)
            route_div = [build.get("route_div_a", 1), build.get("route_div_b", 1)]
            route_div = [v if isinstance(v, (int, float)) and v > 0 else 1 for v in route_div]
            airport_alloc_total = sum(v / d for v, d in zip(airport_est, route_div))
            union_alloc_total = sum(v / d for v, d in zip(union_est, route_div))
            rows[str(build.get("arm") or "unknown")].append({
                "base": base,
                "airport_total": airport_total,
                "union_total": union_total,
                "airport_alloc_total": airport_alloc_total,
                "union_alloc_total": union_alloc_total,
                "base_over_airport": base / airport_total if airport_total > 0 else None,
                "base_over_union": base / union_total if union_total > 0 else None,
                "base_over_airport_alloc": base / airport_alloc_total if airport_alloc_total > 0 else None,
                "base_over_union_alloc": base / union_alloc_total if union_alloc_total > 0 else None,
                "route_div_a": route_div[0],
                "route_div_b": route_div[1],
                "reuse": f"{build.get('reuse_a')},{build.get('reuse_b')}",
            })

    out = {}
    for arm, group in sorted(rows.items()):
        patterns = defaultdict(int)
        for row in group:
            patterns[row["reuse"]] += 1
        out[arm] = {
            "n": len(group),
            "base_monthly": stats(r["base"] for r in group),
            "airport_est_total": stats(r["airport_total"] for r in group),
            "union_est_total": stats(r["union_total"] for r in group),
            "airport_est_route_allocated_total": stats(r["airport_alloc_total"] for r in group),
            "union_est_route_allocated_total": stats(r["union_alloc_total"] for r in group),
            "base_over_airport": stats(r["base_over_airport"] for r in group if r["base_over_airport"] is not None),
            "base_over_union": stats(r["base_over_union"] for r in group if r["base_over_union"] is not None),
            "base_over_airport_route_allocated": stats(r["base_over_airport_alloc"] for r in group if r["base_over_airport_alloc"] is not None),
            "base_over_union_route_allocated": stats(r["base_over_union_alloc"] for r in group if r["base_over_union_alloc"] is not None),
            "route_div_a": stats(r["route_div_a"] for r in group),
            "route_div_b": stats(r["route_div_b"] for r in group),
            "reuse_patterns": dict(sorted(patterns.items())),
        }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
