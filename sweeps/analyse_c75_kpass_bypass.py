"""Analyse un duel C66.4 c75_kpass_bypass=0 -> 1 et sa telemetrie durable."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_1v1_5y_20seeds import student_t_ci95_critical_value  # noqa: E402


def _mean(values):
    return statistics.mean(values) if values else None


def _median(values):
    return statistics.median(values) if values else None


def _ci95(values):
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    sem = statistics.stdev(values) / (len(values) ** 0.5)
    tcrit = student_t_ci95_critical_value(len(values) - 1)
    return [mean - tcrit * sem, mean + tcrit * sem]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result")
    args = parser.parse_args()
    data = json.loads(Path(args.result).read_text(encoding="utf-8"))
    comparison = data.get("policy_comparison") or {}
    reference_policy = comparison.get("reference_policy_id", "c75_bypass0")
    variant_policy = comparison.get("variant_policy_id", "c75_bypass1")

    rows = [
        row for row in data.get("summary", [])
        if row.get("arm") == "OpexAI"
        and row.get("duel_policy_id") in {reference_policy, variant_policy}
    ]
    by_key = {
        (row["duel_policy_id"], int(row["seed"]), int(row.get("repeat", 0))): row
        for row in rows
    }
    seeds = sorted({
        seed for policy, seed, repeat in by_key
        if policy == reference_policy
        and (variant_policy, seed, repeat) in by_key
    })

    deltas = defaultdict(list)
    build_deltas_by_year = defaultdict(list)
    per_seed = []
    for seed in seeds:
        ref = by_key[(reference_policy, seed, 0)]
        var = by_key[(variant_policy, seed, 0)]
        row = {"seed": seed}
        for metric in ("profit_year", "company_value", "primary_vehicles", "n_stations",
                       "project_builds_sign_total"):
            rv = ref.get(metric)
            vv = var.get(metric)
            delta = (vv - rv) if isinstance(rv, (int, float)) and isinstance(vv, (int, float)) else None
            row[metric] = {"reference": rv, "variant": vv, "delta": delta}
            if delta is not None:
                deltas[metric].append(delta)
        ref_builds = ref.get("project_builds_sign_by_year") or {}
        var_builds = var.get("project_builds_sign_by_year") or {}
        for year in sorted(set(ref_builds) | set(var_builds)):
            build_deltas_by_year[str(year)].append(
                int(var_builds.get(year, 0)) - int(ref_builds.get(year, 0))
            )
        per_seed.append(row)

    profit = deltas["profit_year"]
    wins = sum(value > 0 for value in profit)
    losses = sum(value < 0 for value in profit)
    ties = sum(value == 0 for value in profit)

    ref_values = [by_key[(reference_policy, seed, 0)].get("company_value") for seed in seeds]
    var_values = [by_key[(variant_policy, seed, 0)].get("company_value") for seed in seeds]
    ratio = (
        statistics.mean(var_values) / statistics.mean(ref_values)
        if ref_values and all(value is not None for value in ref_values + var_values)
        and statistics.mean(ref_values) != 0 else None
    )

    events = []
    annual = defaultdict(Counter)
    for seed in seeds:
        var = by_key[(variant_policy, seed, 0)]
        for event in var.get("c75_bypass_events") or []:
            copied = dict(event)
            copied["seed"] = seed
            events.append(copied)
        for year, counters in (var.get("c75_bypass_years") or {}).items():
            for key, value in counters.items():
                annual[str(year)][key] += int(value)

    by_mode = Counter(event.get("mode") for event in events)
    by_kind = Counter(event.get("kind") for event in events)
    by_year = Counter(str(event.get("year")) for event in events)
    capital_k = [event["capital_k"] for event in events if "capital_k" in event]
    available_k = [event["available_k"] for event in events if "available_k" in event]
    kpass_k = [event["k_pass_k"] for event in events if "k_pass_k" in event]
    official = (data.get("policy_comparison") or {}).get("aggregates") or {}
    official_profit = (official.get("profit_year") or {}).get("policy_delta") or {}
    official_value = official.get("company_value") or {}
    official_value_ratio = (official_value.get("policy_ratio") or {}).get("ratio_of_means")

    output = {
        "campaign_id": data.get("campaign_id"),
        "reference_policy_id": reference_policy,
        "variant_policy_id": variant_policy,
        "seeds": seeds,
        "pairs": len(seeds),
        "economics": {
            "profit_year_delta_mean": _mean(profit),
            "profit_year_delta_median": _median(profit),
            "profit_year_ci95": _ci95(profit),
            "official_profit_year_student_t_ci95": official_profit.get("mean_student_t_95pct_ci"),
            "official_sign_test_p": official_profit.get("sign_test_p"),
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "company_value_ratio_of_means": (
                official_value_ratio if official_value_ratio is not None else ratio
            ),
            "company_value_pct": (
                (official_value_ratio - 1.0) * 100.0
                if official_value_ratio is not None
                else ((ratio - 1.0) * 100.0 if ratio is not None else None)
            ),
            "primary_vehicles_delta_mean": _mean(deltas["primary_vehicles"]),
            "stations_delta_mean": _mean(deltas["n_stations"]),
            "project_builds_delta_mean": _mean(deltas["project_builds_sign_total"]),
            "project_builds_delta_by_year_mean": {
                year: _mean(values) for year, values in sorted(build_deltas_by_year.items())
            },
        },
        "telemetry": {
            "consumed": len(events),
            "by_mode": dict(sorted(by_mode.items())),
            "by_kind": dict(sorted(by_kind.items())),
            "by_year": dict(sorted(by_year.items())),
            "fleet_events": sum(event.get("mode") == "F" for event in events),
            "annual_closed": {year: dict(counter) for year, counter in sorted(annual.items())},
            "capital_k_mean": _mean(capital_k),
            "capital_k_median": _median(capital_k),
            "available_k_mean": _mean(available_k),
            "available_k_median": _median(available_k),
            "k_pass_k_mean": _mean(kpass_k),
            "k_pass_k_median": _median(kpass_k),
        },
        "per_seed": per_seed,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
