"""Paired yearly profits attributed to vehicles on ACTIVE services, by mode.

This is not company profit_year: vehicle financials use their own year-to-date
window and omit inactive lines, network costs and other company transactions.
Never interpret ROAD vehicle losses as proof that ROAD contributes nothing:
feeders can have indirect network effects. Nothing here proves a buildable OD.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
from statistics import mean


MODES = ("air", "rail", "road")


def profile(snapshot):
    if snapshot.get("ok") is not True or snapshot.get("unresolved_vehicles"):
        raise ValueError("incomplete active service snapshot")
    found = set()
    profits = {mode: 0.0 for mode in MODES}
    service_counts = {mode: 0 for mode in MODES}
    vehicle_counts = {mode: 0 for mode in MODES}
    for line in snapshot.get("lines", []):
        mode = line["mode"]
        if mode not in profits:
            continue
        ids = line["vehicle_ids"]
        if any(v in found for v in ids) or len(set(ids)) != len(ids):
            raise ValueError("vehicle counted in multiple services")
        found.update(ids)
        value = line.get("profit_this_year_gbp")
        if type(value) not in (float, int) or not math.isfinite(value):
            raise ValueError("missing vehicle financial profit")
        profits[mode] += value
        service_counts[mode] += 1
        vehicle_counts[mode] += len(ids)
    return {"profits": profits, "service_counts": service_counts,
            "vehicle_counts": vehicle_counts}


def analyze(data, *, policy="reference", years=(1971, 1972, 1973)):
    seeds = list(data["seeds"])
    raw = {}
    for s in data["line_telemetry"]["snapshots"]:
        if s["duel_policy_id"] != policy or s["year"] not in years:
            continue
        key = (s["seed"], s["arm"], s["year"])
        if key in raw:
            raise ValueError(f"duplicate snapshot: {key}")
        raw[key] = s
    if len(raw) != len(seeds) * 2 * len(years):
        raise ValueError("missing or duplicate annual snapshots")
    valid = {}
    excluded = {}
    for year in years:
        excluded[str(year)] = []
        for seed in seeds:
            snaps = [raw[(seed, arm, year)] for arm in ("OpexAI", "AAAHogEx")]
            if any(x.get("ok") is not True or x.get("unresolved_vehicles") for x in snaps):
                excluded[str(year)].append(seed)
                continue
            valid[(seed, year)] = {arm: profile(raw[(seed, arm, year)])
                                   for arm in ("OpexAI", "AAAHogEx")}
    by_year = {}
    for year in years:
        pairs = [valid[(seed, year)] for seed in seeds if (seed, year) in valid]
        if not pairs:
            raise ValueError(f"no complete pairs for {year}")
        by_year[str(year)] = {
            "n": len(pairs), "excluded_seeds": excluded[str(year)],
            "mean_vehicle_profit_by_mode_gbp": {
                arm: {mode: round(mean(p[arm]["profits"][mode] for p in pairs), 2)
                      for mode in MODES} for arm in ("OpexAI", "AAAHogEx")},
            "mean_opex_minus_aaa_by_mode_gbp": {
                mode: round(mean(p["OpexAI"]["profits"][mode] -
                                 p["AAAHogEx"]["profits"][mode] for p in pairs), 2)
                for mode in MODES},
            "mean_active_services": {arm: {
                mode: round(mean(p[arm]["service_counts"][mode] for p in pairs), 3)
                for mode in MODES} for arm in ("OpexAI", "AAAHogEx")},
            "mean_active_primary_vehicles": {arm: {
                mode: round(mean(p[arm]["vehicle_counts"][mode] for p in pairs), 3)
                for mode in MODES} for arm in ("OpexAI", "AAAHogEx")},
            "pooled_vehicle_profit_per_active_vehicle_gbp": {arm: {
                mode: round(sum(p[arm]["profits"][mode] for p in pairs) /
                            sum(p[arm]["vehicle_counts"][mode] for p in pairs), 2)
                if sum(p[arm]["vehicle_counts"][mode] for p in pairs) > 0 else None
                for mode in MODES} for arm in ("OpexAI", "AAAHogEx")},
        }
    growth = {}
    for earlier, later in zip(years, years[1:]):
        same = [seed for seed in seeds if (seed, earlier) in valid and (seed, later) in valid]
        if not same:
            continue
        growth[f"{earlier}_to_{later}"] = {
            "n": len(same), "excluded": [s for s in seeds if s not in same],
            "mean_change_vehicle_profit_by_mode_gbp": {
                arm: {mode: round(mean(valid[(s, later)][arm]["profits"][mode] -
                                       valid[(s, earlier)][arm]["profits"][mode]
                                       for s in same), 2) for mode in MODES}
                for arm in ("OpexAI", "AAAHogEx")},
        }
    return {"campaign": data["campaign_id"], "policy": policy,
            "source_bundle_sha256": data["source_bundle_sha256"],
            "by_year": by_year, "same_seed_growth": growth,
            "limitations": [
                "This is year-to-date profit attributed to vehicles in ACTIVE services at December checkpoint.",
                "Not trailing-four-quarter company profit_year or profit gained from new projects.",
                "Station/network/loan costs and indirect feeder benefits are not attributed to modes here.",
                "Incomplete AAA snapshots cause BOTH companies for that seed/year to be excluded.",
                "Line-telemetry groups may merge services with same station pair; line construction events unavailable.",
                "This campaign has the same LOOP_OPS probes on both economic policy arms but probes may alter trajectories.",
            ]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("c66", type=Path)
    p.add_argument("--policy", default="reference")
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    if args.out.exists():
        p.error("refusing to overwrite existing report")
    result = analyze(json.loads(args.c66.read_text(encoding="utf-8")), policy=args.policy)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"by_year": result["by_year"], "same_seed_growth": result["same_seed_growth"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
