#!/usr/bin/env python3
"""Concise causal diagnostics for the C121 first-live-growth paired campaign."""

from __future__ import annotations

import json
from pathlib import Path
import statistics
import argparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path,
                        default=Path("results/c121_first_live_growth_bal90_5x6_20261001_r1.json"))
    args = parser.parse_args()
    data = json.loads(args.source.read_text(encoding="utf-8"))
    cmp = data["policy_comparison"]
    rows = []
    for pair in cmp["per_pair"]:
        m = pair["metrics"]
        a = pair.get("air_structural_metrics", {})
        row = {
            "seed": pair["seed"],
            "profit_year": m["profit_year"]["policy_delta"],
            "gap_profit_year": m["profit_year"]["duel_gap_evolution"],
            "company_value": m["company_value"]["policy_delta"],
            "gap_company_value": m["company_value"]["duel_gap_evolution"],
            "vehicles": m["primary_vehicles"]["policy_delta"],
        }
        for key in (
            "airport_slots_opex",
            "airport_towns_opex_present",
            "airport_towns_aaahogex_2_opex_0",
            "airport_towns_shared_1_1",
        ):
            row[key] = (a.get(key) or {}).get("policy_delta")
        rows.append(row)

    print("per_seed")
    for row in rows:
        print(json.dumps(row, sort_keys=True))
    print("means")
    for key in rows[0]:
        if key == "seed":
            continue
        vals = [r[key] for r in rows if r[key] is not None]
        print(key, round(statistics.mean(vals), 3) if vals else None)

    trajectories = {pair["seed"]: pair.get("annual_trajectory", []) for pair in cmp["per_pair"]}
    print("annual_gap_profit_mean")
    years = sorted({p["year"] for vals in trajectories.values() for p in vals})
    for year in years:
        vals = []
        opex = []
        for tr in trajectories.values():
            p = next((x for x in tr if x["year"] == year), None)
            if p is None:
                continue
            vals.append(p.get("duel_gap_evolution"))
            opex.append(p.get("policy_delta"))
        vals = [x for x in vals if x is not None]
        opex = [x for x in opex if x is not None]
        print(year, "opex_delta", round(statistics.mean(opex), 1) if opex else None,
              "gap_delta", round(statistics.mean(vals), 1) if vals else None)

    print("line_telemetry_keys", sorted((data.get("line_telemetry") or {}).keys()))


if __name__ == "__main__":
    main()
