#!/usr/bin/env python3
"""Summarize C116 5x6 structural deltas versus the C115 current default."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import statistics
import sys


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "results/c116_marginal_capital_5x6_20260927.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    checkpoints_path = path.with_suffix(".jsonl")
    reference_id = data["policy_comparison"]["reference_policy_id"]
    variant_id = data["policy_comparison"]["variant_policy_id"]

    summaries = {}
    for row in data["summary"]:
        if row.get("arm") != "OpexAI":
            continue
        summaries[(row["duel_policy_id"], int(row["seed"]))] = row

    final_checkpoints = {}
    with checkpoints_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("run", [None])[0] != "OpexAI":
                continue
            if row.get("date") != data["expected_last_checkpoint"]:
                continue
            final_checkpoints[(row["duel_policy_id"], int(row["run"][1]))] = row

    seeds = sorted({seed for policy, seed in summaries if policy == reference_id})
    rows = []
    aggregate_engines = {reference_id: Counter(), variant_id: Counter()}
    for seed in seeds:
        ref = summaries[(reference_id, seed)]
        var = summaries[(variant_id, seed)]
        ref_final = final_checkpoints[(reference_id, seed)]
        var_final = final_checkpoints[(variant_id, seed)]
        ref_air = int(ref_final.get("air_primary_vehicles") or 0)
        var_air = int(var_final.get("air_primary_vehicles") or 0)
        ref_pax = int(ref_final.get("air_passenger_capacity") or 0)
        var_pax = int(var_final.get("air_passenger_capacity") or 0)
        ref_airports = int(ref_final.get("air_airports") or 0)
        var_airports = int(var_final.get("air_airports") or 0)
        ref_engines = {str(k): int(v) for k, v in (ref_final.get("air_engine_counts") or {}).items()}
        var_engines = {str(k): int(v) for k, v in (var_final.get("air_engine_counts") or {}).items()}
        aggregate_engines[reference_id].update(ref_engines)
        aggregate_engines[variant_id].update(var_engines)
        rows.append({
            "seed": seed,
            "profit_year_delta": int(var["profit_year"]) - int(ref["profit_year"]),
            "company_value_delta": int(var["company_value"]) - int(ref["company_value"]),
            "air_fleet_ref": ref_air,
            "air_fleet_var": var_air,
            "air_fleet_delta": var_air - ref_air,
            "pax_capacity_ref": ref_pax,
            "pax_capacity_var": var_pax,
            "pax_capacity_delta": var_pax - ref_pax,
            "airports_ref": ref_airports,
            "airports_var": var_airports,
            "airports_delta": var_airports - ref_airports,
            "engines_ref": ref_engines,
            "engines_var": var_engines,
            "activity_ref": (ref.get("activity") or {}).get("signal"),
            "activity_var": (var.get("activity") or {}).get("signal"),
        })

    engine_mix = {}
    for policy in (reference_id, variant_id):
        counts = aggregate_engines[policy]
        total = sum(counts.values())
        engine_mix[policy] = {
            "total_aircraft": total,
            "counts": dict(sorted(counts.items(), key=lambda kv: int(kv[0]))),
            "shares_pct": {
                k: (100.0 * v / total if total else 0.0)
                for k, v in sorted(counts.items(), key=lambda kv: int(kv[0]))
            },
        }

    comparison = data["policy_comparison"]
    per_pair = {int(row["seed"]): row for row in comparison["per_pair"]}
    gap_evolution = {
        metric: [per_pair[s]["metrics"][metric]["duel_gap_evolution"] for s in seeds]
        for metric in ("profit_year", "company_value")
    }

    result = {
        "seeds": seeds,
        "rows": rows,
        "means": {
            "profit_year_delta": mean(r["profit_year_delta"] for r in rows),
            "company_value_delta": mean(r["company_value_delta"] for r in rows),
            "air_fleet_ref": mean(r["air_fleet_ref"] for r in rows),
            "air_fleet_var": mean(r["air_fleet_var"] for r in rows),
            "air_fleet_delta": mean(r["air_fleet_delta"] for r in rows),
            "pax_capacity_ref": mean(r["pax_capacity_ref"] for r in rows),
            "pax_capacity_var": mean(r["pax_capacity_var"] for r in rows),
            "pax_capacity_delta": mean(r["pax_capacity_delta"] for r in rows),
            "airports_ref": mean(r["airports_ref"] for r in rows),
            "airports_var": mean(r["airports_var"] for r in rows),
            "airports_delta": mean(r["airports_delta"] for r in rows),
            "profit_gap_evolution": mean(gap_evolution["profit_year"]),
            "value_gap_evolution": mean(gap_evolution["company_value"]),
        },
        "medians": {
            "air_fleet_delta": statistics.median(r["air_fleet_delta"] for r in rows),
            "pax_capacity_delta": statistics.median(r["pax_capacity_delta"] for r in rows),
            "airports_delta": statistics.median(r["airports_delta"] for r in rows),
        },
        "engine_mix": engine_mix,
        "duel_gap_evolution_by_seed": gap_evolution,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
