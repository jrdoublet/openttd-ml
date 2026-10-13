"""How net AIR aircraft expansion co-occurs with profit of incumbent planes.

For each arm and same seed, pair ACTIVE stations between adjacent December
snapshots, then classify routes by change in the count of active primary
aircraft. Only surviving *same IDs at same stations* contribute to the profit
delta, so recent entrant age cannot mechanically create the decline.
Association is not intervention: growth is endogenous, demand and rivals move.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median

from analyse_p0_air_fleet_incumbents_20261012 import air_services, pair_services


CATS = ("expanded", "unchanged", "contracted")
ARMS = ("OpexAI", "AAAHogEx")


def analyze(c66, year=1973, policy="reference"):
    grouped = {}
    for row in c66["line_telemetry"]["snapshots"]:
        if row.get("duel_policy_id") != policy or row.get("year") not in (year - 1, year):
            continue
        key = row["seed"], row["arm"], row["year"]
        if key in grouped:
            raise ValueError(f"duplicate snapshot {key}")
        grouped[key] = row

    by_seed, excluded = {}, []
    for seed in c66["seeds"]:
        observations = [grouped.get((seed, arm, y)) for arm in ARMS
                        for y in (year - 1, year)]
        if any(item is None or item.get("ok") is not True or
               item.get("unresolved_vehicles") for item in observations):
            excluded.append(seed)
            continue
        by_seed[str(seed)] = {}
        for arm in ARMS:
            prior = air_services(grouped[(seed, arm, year - 1)])
            current = air_services(grouped[(seed, arm, year)])
            by_seed[str(seed)][arm] = pair_services(prior, current)

    if not by_seed:
        raise ValueError("zero qualified paired seeds")
    summary = {}
    for arm in ARMS:
        summary[arm] = {}
        for cat in CATS:
            rows = [result[arm]["aggregates"][cat] for result in by_seed.values()]
            services = sum(item["matched_services"] for item in rows)
            survivors = sum(item["surviving_aircraft"] for item in rows)
            profit = sum(item["total_incumbent_profit_change_gbp"] for item in rows)
            populated = [item["total_incumbent_profit_change_gbp"] for item in rows
                         if item["surviving_aircraft"] > 0]
            summary[arm][cat] = {
                "matched_active_services_all_seeds": services,
                "surviving_aircraft_all_seeds": survivors,
                "mean_surviving_aircraft_per_seed": round(survivors / len(by_seed), 3),
                "total_incumbent_ytd_profit_change_gbp": round(profit, 2),
                "mean_incumbent_ytd_profit_change_per_seed_gbp": round(profit / len(by_seed), 2),
                "pooled_change_per_survivor_gbp": round(profit / survivors, 2) if survivors else None,
                "populated_seeds": len(populated),
                "seeds_with_negative_incumbent_profit_delta": sum(x < 0 for x in populated),
                "seeds_with_positive_incumbent_profit_delta": sum(x > 0 for x in populated),
                "median_profit_change_per_populated_seed_gbp": round(median(populated), 2)
                    if populated else None,
            }
    return {"campaign": c66["campaign_id"], "bundle": c66["source_bundle_sha256"],
            "policy": policy, "period": [year - 1, year],
            "paired_n": len(by_seed), "excluded": excluded,
            "summary": summary, "by_seed": by_seed,
            "limitations": [
                "Only pairs of ACTIVE same-station-ID services surviving two December checkpoints.",
                "Only vehicle IDs present within the same service in both years enter profit deltas.",
                "The route category expanded/unchanged/contracted is NET active aircraft count change, not orders/purchase timestamps.",
                "Selection on surviving vehicle IDs, demand changes, competitor services, stations and pricing are uncontrolled.",
                "A correlation between net added planes and incumbent lost profit is NOT proof that additions caused it.",
                "Source vehicle profit_this_year is YTD, not company profit_year, and does not include infrastructure/credit costs.",
                "Only same frozen paired C66 reference policy is used; OFF/ON or different bundles are not mixed.",
            ]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("c66", type=Path)
    p.add_argument("--year", type=int, default=1973)
    p.add_argument("--policy", default="reference")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error("refusing to overwrite existing report")
    result = analyze(json.loads(args.c66.read_text(encoding="utf-8")), args.year, args.policy)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"paired_n": result["paired_n"], "excluded": result["excluded"],
                      "summary": result["summary"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
