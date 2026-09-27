#!/usr/bin/env python3
"""Compare les portefeuilles AIR OpexAI reference/variante d'une campagne C66.4."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

from analyse_early_slot_lines import aggregate_markets


def mean(values):
    values = list(values)
    return statistics.mean(values) if values else None


def summarize_pair(ref, var):
    shared = set(ref) & set(var)
    ref_only = set(ref) - set(var)
    var_only = set(var) - set(ref)

    def profit(rows, keys):
        return sum(rows[k]["profit_this_year_gbp"] for k in keys)

    def vehicles(rows, keys):
        return sum(rows[k]["vehicles"] for k in keys)

    def capacity(rows, keys):
        return sum(sum(rows[k]["capacity_by_cargo"].values()) for k in keys)

    return {
        "reference_markets": len(ref),
        "variant_markets": len(var),
        "shared_markets": len(shared),
        "reference_only_markets": len(ref_only),
        "variant_only_markets": len(var_only),
        "jaccard": len(shared) / len(set(ref) | set(var)) if (ref or var) else 1.0,
        "reference_profit": profit(ref, ref),
        "variant_profit": profit(var, var),
        "shared_reference_profit": profit(ref, shared),
        "shared_variant_profit": profit(var, shared),
        "shared_profit_delta": profit(var, shared) - profit(ref, shared),
        "reference_only_profit": profit(ref, ref_only),
        "variant_only_profit": profit(var, var_only),
        "reference_vehicles": vehicles(ref, ref),
        "variant_vehicles": vehicles(var, var),
        "reference_capacity": capacity(ref, ref),
        "variant_capacity": capacity(var, var),
        "ref_only": sorted(
            ({"market_key": k, **ref[k]} for k in ref_only),
            key=lambda x: x["profit_this_year_gbp"], reverse=True),
        "var_only": sorted(
            ({"market_key": k, **var[k]} for k in var_only),
            key=lambda x: x["profit_this_year_gbp"], reverse=True),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.path.read_text(encoding="utf-8"))
    comparison = payload.get("policy_comparison") or {}
    ref_policy = comparison.get("reference_policy_id") or payload.get("policy_id")
    var_policy = comparison.get("variant_policy_id")
    if not var_policy:
        raise SystemExit("variant_policy_id absent")

    snaps = (payload.get("line_telemetry") or {}).get("snapshots") or []
    index = {
        (s.get("duel_policy_id"), s.get("arm"), s.get("seed"), s.get("repeat", 0), s.get("year")): s
        for s in snaps if s.get("ok")
    }
    keys = sorted({
        (seed, repeat, year)
        for policy, arm, seed, repeat, year in index
        if policy == ref_policy and arm == "OpexAI" and year is not None
        and (var_policy, "OpexAI", seed, repeat, year) in index
    })

    rows = []
    for seed, repeat, year in keys:
        ref_snap = index[(ref_policy, "OpexAI", seed, repeat, year)]
        var_snap = index[(var_policy, "OpexAI", seed, repeat, year)]
        row = summarize_pair(
            aggregate_markets(ref_snap.get("lines"), "air"),
            aggregate_markets(var_snap.get("lines"), "air"),
        )
        row.update(seed=seed, repeat=repeat, year=year)
        rows.append(row)

    per_year = {}
    scalar_fields = [
        "reference_markets", "variant_markets", "shared_markets",
        "reference_only_markets", "variant_only_markets", "jaccard",
        "reference_profit", "variant_profit", "shared_profit_delta",
        "reference_only_profit", "variant_only_profit",
        "reference_vehicles", "variant_vehicles",
        "reference_capacity", "variant_capacity",
    ]
    for year in sorted({r["year"] for r in rows}):
        yr = [r for r in rows if r["year"] == year]
        per_year[str(year)] = {field: mean(r[field] for r in yr) for field in scalar_fields}

    final_year = max((r["year"] for r in rows), default=None)
    final_rows = [r for r in rows if r["year"] == final_year]
    final_detail = []
    for row in final_rows:
        final_detail.append({
            "seed": row["seed"],
            "reference_markets": row["reference_markets"],
            "variant_markets": row["variant_markets"],
            "shared_markets": row["shared_markets"],
            "jaccard": row["jaccard"],
            "shared_profit_delta": row["shared_profit_delta"],
            "reference_only_profit": row["reference_only_profit"],
            "variant_only_profit": row["variant_only_profit"],
            "top_ref_only": [
                {"market_key": m["market_key"], "profit": m["profit_this_year_gbp"], "vehicles": m["vehicles"]}
                for m in row["ref_only"][:5]
            ],
            "top_var_only": [
                {"market_key": m["market_key"], "profit": m["profit_this_year_gbp"], "vehicles": m["vehicles"]}
                for m in row["var_only"][:5]
            ],
        })

    print(json.dumps({
        "reference_policy": ref_policy,
        "variant_policy": var_policy,
        "pairs": len(rows),
        "final_year": final_year,
        "per_year": per_year,
        "final_detail": final_detail,
    }, indent=2))


if __name__ == "__main__":
    main()
