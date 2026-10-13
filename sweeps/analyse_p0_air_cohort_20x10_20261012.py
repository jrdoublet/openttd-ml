"""Annual active-aircraft ID cohorts, not purchase dates or build causes.

The reference Opex/AAA companies share the same seed/map *within* each C66
duel. Annual checkpoints identify surviving AIR vehicle IDs; new-to-checkpoint
IDs include replacements and reassigned or reappearing aircraft.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from analyse_p0_air_vehicle_cohorts_20261012 import air_vehicles, cohort


def air_vehicle_markets(snapshot):
    """ID → (town market, station ID pair, YTD profit), no birth inference."""
    if snapshot.get("ok") is not True or snapshot.get("unresolved_vehicles"):
        raise ValueError("invalid active AIR snapshot")
    out = {}
    for line in snapshot.get("lines", []):
        if line.get("mode") != "air":
            continue
        market = line.get("market_key")
        stations = tuple(sorted(line.get("station_ids") or []))
        for vehicle in line.get("vehicle_financials", []):
            ident = vehicle.get("vehicle_id")
            value = vehicle.get("profit_this_year_gbp")
            if ident is None or type(value) not in (int, float):
                raise ValueError("invalid AIR financial vehicle")
            if ident in out:
                raise ValueError("duplicate AIR vehicle id")
            out[ident] = (market, stations, value)
    return out


def stable_market_cohort(current, previous):
    """Profit differences for the SAME vehicle on the SAME town-pair market."""
    continuing = set(current) & set(previous)
    same_market = [ident for ident in continuing if current[ident][0] is not None
                   and current[ident][0] == previous[ident][0]]
    same_station_pair = [ident for ident in same_market
                         if current[ident][1] and current[ident][1] == previous[ident][1]]
    def change(ids):
        return round(sum(current[k][2] - previous[k][2] for k in ids), 2)
    return {"continuing_count": len(continuing),
            "same_market_count": len(same_market),
            "same_station_pair_count": len(same_station_pair),
            "same_market_ytd_profit_change_gbp": change(same_market),
            "same_station_pair_ytd_profit_change_gbp": change(same_station_pair)}


def analyze(report, policy="reference", year=1973):
    snaps = {}
    for t in report["line_telemetry"]["snapshots"]:
        if t["duel_policy_id"] != policy or t["year"] not in (year - 1, year):
            continue
        key = (t["seed"], t["arm"], t["year"])
        if key in snaps:
            raise ValueError(f"duplicate {key}")
        snaps[key] = t
    valid = []
    excluded = []
    by_seed = {}
    for seed in report["seeds"]:
        observations = [snaps.get((seed, arm, y)) for arm in ("OpexAI", "AAAHogEx")
                        for y in (year - 1, year)]
        if any(s is None or s.get("ok") is not True or s.get("unresolved_vehicles")
               for s in observations):
            excluded.append(seed)
            continue
        valid.append(seed)
        by_seed[str(seed)] = {}
        for arm in ("OpexAI", "AAAHogEx"):
            previous_snap = snaps[(seed, arm, year - 1)]
            current_snap = snaps[(seed, arm, year)]
            previous = air_vehicles(previous_snap)
            current = air_vehicles(current_snap)
            by_seed[str(seed)][arm] = cohort(current, previous)
            by_seed[str(seed)][arm]["stable_market_cohort"] = stable_market_cohort(
                air_vehicle_markets(current_snap), air_vehicle_markets(previous_snap))
    if not valid:
        raise ValueError("no complete paired AIR cohorts")
    by_arm = {}
    for arm in ("OpexAI", "AAAHogEx"):
        records = [by_seed[str(s)][arm] for s in valid]
        by_arm[arm] = {}
        for field in ("continuing", "not_seen_prior_december", "continuing_same_ids_prior_year", "all"):
            count = sum(r[field]["planes"] for r in records)
            gain = sum(r[field]["sum_profit_gbp"] for r in records)
            by_arm[arm][field] = {
                "mean_aircraft_per_seed": round(count / len(records), 3),
                "total_aircraft_observations": count,
                "mean_vehicle_ytd_profit_per_seed_gbp": round(gain / len(records), 2),
                "pooled_ytd_profit_per_aircraft_gbp": round(gain / count, 2) if count else None,
            }
        by_arm[arm]["continuing_same_ids_change_gbp_per_seed"] = round(
            mean(r["continuing_profit_change_same_ids_gbp"] for r in records), 2)
        by_arm[arm]["newly_observed_fraction_of_current"] = round(
            sum(r["not_seen_prior_december"]["planes"] for r in records) /
            sum(r["all"]["planes"] for r in records), 4)
        stable = [r["stable_market_cohort"] for r in records]
        by_arm[arm]["stable_market"] = {
            "mean_continuing_count": round(mean(x["continuing_count"] for x in stable), 3),
            "mean_same_market_count": round(mean(x["same_market_count"] for x in stable), 3),
            "fraction_of_continuing_in_same_market": round(
                sum(x["same_market_count"] for x in stable) /
                sum(x["continuing_count"] for x in stable), 4),
            "mean_same_station_pair_count": round(mean(x["same_station_pair_count"] for x in stable), 3),
            "mean_same_market_profit_change_gbp": round(mean(
                x["same_market_ytd_profit_change_gbp"] for x in stable), 2),
            "mean_same_station_pair_profit_change_gbp": round(mean(
                x["same_station_pair_ytd_profit_change_gbp"] for x in stable), 2),
            "seeds_negative_same_market_change": sum(
                x["same_market_ytd_profit_change_gbp"] < 0 for x in stable),
            "seeds_positive_same_market_change": sum(
                x["same_market_ytd_profit_change_gbp"] > 0 for x in stable),
        }
    return {"campaign": report["campaign_id"], "policy": policy,
            "source_bundle_sha256": report["source_bundle_sha256"],
            "year": year, "paired_seeds": valid, "excluded": excluded,
            "aggregates": by_arm, "per_seed": by_seed,
            "limitations": [
                "Identified by annual December active AIR vehicle IDs; not purchase or new-service timestamps.",
                "Not seen previously also covers replacements, reassignments or earlier telemetry invisibility.",
                "Current-year profits of newly observed vehicles can cover fewer operating months than incumbents.",
                "Vehicle YTD profit does not include all company revenues/costs and is not profit_year.",
                "Surviving-vehicle change is selected on survival and cannot identify causes of fleet saturation.",
                "Same market_key means same town pair, not necessarily same airport or identical order sequence.",
                "No A/B causal comparison of air_fleet or capital allocation policy is asserted.",
            ]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("c66", type=Path)
    p.add_argument("--policy", default="reference")
    p.add_argument("--year", type=int, default=1973)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        p.error("refusing to overwrite existing report")
    result = analyze(json.loads(a.c66.read_text(encoding="utf-8")), a.policy, a.year)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"n": len(result["paired_seeds"]), "excluded": result["excluded"],
                      "by_arm": result["aggregates"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
