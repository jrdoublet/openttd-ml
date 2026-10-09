#!/usr/bin/env python3
"""Appariement de la premiere divergence physique/economique N2, snapshots JSONL.

Observations, sans attribution d'un evenement Squirrel: les logs qualificatifs
ont volontairement ete desactives dans la campagne V102.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import mean, median


KEYS = ("company_value", "profit_year", "money", "n_stations", "primary_vehicles_by_mode")


def analyze(path, variant_policy_id="gate"):
    data = {}
    with path.open(encoding="utf-8") as stream:
        for raw in stream:
            entry = json.loads(raw)
            run = entry.get("run", [])
            if len(run) < 3 or run[0] != "OpexAI":
                continue
            data[(entry.get("duel_policy_id"), run[1], run[2], entry["date"])] = entry
    seeds = sorted({seed for (policy, seed, repeat, date) in data if policy == "reference"})
    first = []
    yearly = {}
    for seed in seeds:
        dates = sorted({date for (policy, s, repeat, date) in data
                        if policy == "reference" and s == seed and repeat == 0})
        for date in dates:
            a = data.get((variant_policy_id, seed, 0, date))
            b = data.get(("reference", seed, 0, date))
            if a is None or b is None:
                continue
            if any(a.get(key) != b.get(key) for key in KEYS):
                first.append({"seed": seed, "date": date,
                              "profit_delta": (a.get("profit_year") or 0) - (b.get("profit_year") or 0),
                              "rail_vehicles_delta": a.get("primary_vehicles_by_mode", {}).get("rail", 0)
                              - b.get("primary_vehicles_by_mode", {}).get("rail", 0)})
                break
        for year in (1970, 1971, 1972):
            a = data.get((variant_policy_id, seed, 0, f"{year}-12-01"))
            b = data.get(("reference", seed, 0, f"{year}-12-01"))
            if a is None or b is None:
                continue
            for metric in ("profit_year", "company_value", "money"):
                if a.get(metric) is not None and b.get(metric) is not None:
                    yearly.setdefault((year, metric), []).append(a[metric] - b[metric])
            for mode in ("rail", "road", "air", "water"):
                delta = a.get("primary_vehicles_by_mode", {}).get(mode, 0) - b.get("primary_vehicles_by_mode", {}).get(mode, 0)
                yearly.setdefault((year, mode + "_vehicles"), []).append(delta)
    return {
        "seeds": len(seeds),
        "first_divergences": first,
        "first_divergence_years": dict(Counter(row["date"][:4] for row in first)),
        "first_divergence_without_train_delta": sum(row["rail_vehicles_delta"] == 0 for row in first),
        "end_of_year": {f"{year}_{metric}": {"n": len(values), "mean": mean(values),
                                              "median": median(values),
                                              "wins": sum(d > 0 for d in values),
                                              "losses": sum(d < 0 for d in values),
                                              "ties": sum(d == 0 for d in values)}
                        for (year, metric), values in sorted(yearly.items())},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--variant-policy-id", default="gate")
    args = ap.parse_args()
    if args.out.exists():
        ap.error("refusing to overwrite existing output " + str(args.out))
    result = analyze(args.jsonl, args.variant_policy_id)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("first divergence years:", result["first_divergence_years"])
    print("no train difference at first divergence:", result["first_divergence_without_train_delta"])
    print("first events:", sorted(result["first_divergences"], key=lambda x: x["date"])[:12])


if __name__ == "__main__":
    main()
