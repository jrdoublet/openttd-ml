#!/usr/bin/env python3
"""Summarize C115 versus reference on the C114 loss/win seed split."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


C114_LOSS_SEEDS = {100, 7, 17, 314, 1024, 12345, 424242, 8675309}
VARIANT_POLICY = "c115_capital_replay_corrected"
REFERENCE_POLICY = "reference"


def mean(values):
    return sum(values) / len(values) if values else 0.0


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def summary_index(data):
    return {
        (int(row["seed"]), row["policy_id"], row["arm"]): row
        for row in data["summary"]
    }


def pair_index(data):
    return {int(row["seed"]): row for row in data["policy_comparison"]["per_pair"]}


def analyze_group(name, seeds, pairs, summaries):
    rows = []
    for seed in sorted(seeds):
        pair = pairs[seed]
        ref = summaries[(seed, REFERENCE_POLICY, "OpexAI")]
        var = summaries[(seed, VARIANT_POLICY, "OpexAI")]
        ref_air = int(ref["primary_vehicles_by_mode"]["air"])
        var_air = int(var["primary_vehicles_by_mode"]["air"])
        ref_cap = int(ref["capacities_by_cargo"].get("0", 0))
        var_cap = int(var["capacities_by_cargo"].get("0", 0))
        rows.append(
            {
                "seed": seed,
                "profit_year": int(pair["metrics"]["profit_year"]["policy_delta"]),
                "company_value": int(pair["metrics"]["company_value"]["policy_delta"]),
                "airports": int(pair["air_structural_metrics"]["airport_slots_opex"]["policy_delta"]),
                "air_fleet": var_air - ref_air,
                "pax_capacity": var_cap - ref_cap,
                "ref_air": ref_air,
                "var_air": var_air,
                "ref_cap": ref_cap,
                "var_cap": var_cap,
            }
        )

    profits = [r["profit_year"] for r in rows]
    return {
        "name": name,
        "n": len(rows),
        "seeds": [r["seed"] for r in rows],
        "profit_year_mean": mean(profits),
        "profit_year_median": statistics.median(profits),
        "wins": sum(v > 0 for v in profits),
        "losses": sum(v < 0 for v in profits),
        "company_value_mean_delta": mean([r["company_value"] for r in rows]),
        "airport_mean_delta": mean([r["airports"] for r in rows]),
        "air_fleet_mean_delta": mean([r["air_fleet"] for r in rows]),
        "pax_capacity_mean_delta": mean([r["pax_capacity"] for r in rows]),
        "ref_air_mean": mean([r["ref_air"] for r in rows]),
        "var_air_mean": mean([r["var_air"] for r in rows]),
        "ref_pax_capacity_mean": mean([r["ref_cap"] for r in rows]),
        "var_pax_capacity_mean": mean([r["var_cap"] for r in rows]),
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default="results/c115_c100_capital_replay_20x10_20260927_corrected.json",
    )
    args = parser.parse_args()
    data = load(Path(args.path))
    pairs = pair_index(data)
    summaries = summary_index(data)
    all_seeds = set(pairs)
    result = {
        "c114_old_losses": analyze_group(
            "c114_old_losses", C114_LOSS_SEEDS & all_seeds, pairs, summaries
        ),
        "c114_old_wins": analyze_group(
            "c114_old_wins", all_seeds - C114_LOSS_SEEDS, pairs, summaries
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
