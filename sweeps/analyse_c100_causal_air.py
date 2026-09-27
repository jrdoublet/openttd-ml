#!/usr/bin/env python3
"""Summarise final Opex AIR fleet and line economics for a paired C100 campaign."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", type=Path)
    parser.add_argument("jsonl_path", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.json_path.read_text(encoding="utf-8"))

    latest = {}
    for raw in args.jsonl_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        run = row.get("run") or []
        company = run[0] if run else None
        key = (row.get("duel_policy_id"), company, run[1] if len(run) > 1 else None)
        if key not in latest or str(row.get("date")) > str(latest[key].get("date")):
            latest[key] = row

    telemetry = payload.get("line_telemetry") or {}
    snapshots = list(telemetry.get("snapshots", []))
    final_year = max((s.get("year") or -1 for s in snapshots), default=-1)
    line_groups = defaultdict(list)
    for snap in snapshots:
        if snap.get("year") != final_year:
            continue
        line_groups[(snap.get("duel_policy_id"), snap.get("arm"), snap.get("seed"))].extend(
            line for line in snap.get("lines", []) if line.get("mode") == "air"
        )

    policies = defaultdict(lambda: {"aircraft": [], "airports": [], "pax_capacity": [],
                                    "profits": [], "profit_per_aircraft": [], "lines": [],
                                    "engines": Counter()})
    for (policy, company, seed), row in latest.items():
        p = policies[f"{policy}:{company}"]
        aircraft = int(row.get("air_primary_vehicles") or 0)
        p["aircraft"].append(aircraft)
        p["airports"].append(int(row.get("air_airports") or 0))
        p["pax_capacity"].append(int(row.get("air_passenger_capacity") or 0))
        p["engines"].update({str(k): int(v) for k, v in (row.get("air_engine_counts") or {}).items()})
        lines = line_groups.get((policy, company, seed), [])
        profit = sum(float(line.get("profit_this_year_gbp") or 0) for line in lines)
        vehicles = sum(int(line.get("vehicles") or 0) for line in lines)
        p["profits"].append(profit)
        p["profit_per_aircraft"].append(profit / vehicles if vehicles else None)
        p["lines"].append(len(lines))

    out = {"final_year": final_year, "policies": {}}
    for policy, p in sorted(policies.items()):
        total_aircraft = sum(p["aircraft"])
        ppa = [v for v in p["profit_per_aircraft"] if v is not None]
        out["policies"][policy] = {
            "aircraft_mean": statistics.mean(p["aircraft"]) if p["aircraft"] else None,
            "airports_mean": statistics.mean(p["airports"]) if p["airports"] else None,
            "air_lines_mean": statistics.mean(p["lines"]) if p["lines"] else None,
            "air_profit_this_year_mean": statistics.mean(p["profits"]) if p["profits"] else None,
            "air_profit_per_aircraft_median": statistics.median(ppa) if ppa else None,
            "pax_capacity_per_aircraft": sum(p["pax_capacity"]) / total_aircraft if total_aircraft else None,
            "engine_counts": dict(sorted(p["engines"].items(), key=lambda item: int(item[0]))),
            "engine_shares_pct": {engine: 100.0 * count / total_aircraft for engine, count in sorted(p["engines"].items(), key=lambda item: int(item[0]))} if total_aircraft else {},
        }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
