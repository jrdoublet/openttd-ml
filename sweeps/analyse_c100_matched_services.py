#!/usr/bin/env python3
"""Compare OpexAI and AAAHogEx on identical AIR service keys in final C100 snapshots."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics


def aggregate(lines):
    out = defaultdict(lambda: {"vehicles": 0, "profit": 0.0, "capacity": defaultdict(int)})
    for line in lines:
        if line.get("mode") != "air":
            continue
        key = line.get("service_key")
        if not key:
            continue
        row = out[key]
        row["vehicles"] += int(line.get("vehicles") or 0)
        row["profit"] += float(line.get("profit_this_year_gbp") or 0.0)
        for cargo, cap in (line.get("capacity_by_cargo") or {}).items():
            row["capacity"][str(cargo)] += int(cap or 0)
    return out


def stats(values):
    values = [float(v) for v in values]
    return {"n": len(values),
            "mean": statistics.mean(values) if values else None,
            "median": statistics.median(values) if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.path.read_text(encoding="utf-8"))
    snaps = payload.get("line_telemetry", {}).get("snapshots", [])
    final_year = max((s.get("year") or -1 for s in snaps), default=-1)
    by_game = defaultdict(dict)
    for snap in snaps:
        if snap.get("year") != final_year or not snap.get("ok"):
            continue
        key = (snap.get("duel_policy_id"), snap.get("seed"))
        by_game[key][snap.get("arm")] = aggregate(snap.get("lines") or [])

    policies = defaultdict(list)
    for (policy, seed), companies in by_game.items():
        opex = companies.get("OpexAI") or {}
        aaa = companies.get("AAAHogEx") or {}
        for service in sorted(set(opex) & set(aaa)):
            o, a = opex[service], aaa[service]
            if o["vehicles"] <= 0 or a["vehicles"] <= 0:
                continue
            o_pp = o["profit"] / o["vehicles"]
            a_pp = a["profit"] / a["vehicles"]
            policies[policy].append({
                "seed": seed, "service": service,
                "opex_vehicles": o["vehicles"], "aaa_vehicles": a["vehicles"],
                "opex_profit_per_aircraft": o_pp,
                "aaa_profit_per_aircraft": a_pp,
                "aaa_over_opex_profit_per_aircraft": a_pp / o_pp if o_pp > 0 else None,
                "opex_capacity_per_aircraft": sum(o["capacity"].values()) / o["vehicles"],
                "aaa_capacity_per_aircraft": sum(a["capacity"].values()) / a["vehicles"],
            })

    out = {"final_year": final_year, "policies": {}}
    for policy, rows in sorted(policies.items()):
        ratios = [r["aaa_over_opex_profit_per_aircraft"] for r in rows if r["aaa_over_opex_profit_per_aircraft"] is not None]
        out["policies"][policy] = {
            "matched_services": len(rows),
            "aaa_over_opex_profit_per_aircraft": stats(ratios),
            "opex_profit_per_aircraft": stats(r["opex_profit_per_aircraft"] for r in rows),
            "aaa_profit_per_aircraft": stats(r["aaa_profit_per_aircraft"] for r in rows),
            "opex_capacity_per_aircraft": stats(r["opex_capacity_per_aircraft"] for r in rows),
            "aaa_capacity_per_aircraft": stats(r["aaa_capacity_per_aircraft"] for r in rows),
            "by_seed": {str(seed): stats(
                r["aaa_over_opex_profit_per_aircraft"] for r in rows
                if r["seed"] == seed and r["aaa_over_opex_profit_per_aircraft"] is not None
            ) for seed in sorted(set(r["seed"] for r in rows))},
        }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
