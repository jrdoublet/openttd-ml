"""Reconstruit les trajectoires annuelles appariees de la campagne C50b depuis les JSONL."""
import argparse
import json
import math
from pathlib import Path
import statistics

BASELINE = "OpexAI"
BUFFER = "OpexAI[air_fleet_buffer=-1]"
VARIANTS = (
    BUFFER,
    "OpexAI[air_cadence_cap=0]",
    "OpexAI[c50b_road_cap_relax=1]",
    "OpexAI[road_loading_fix=1]",
)
METRICS = (
    "company_value", "profit_year", "performance_history",
    "median_station_rating", "n_vehicles", "n_stations",
)


def sign_pvalue(wins, losses):
    n = wins + losses
    if n == 0:
        return None
    tail = sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def load_year_ends(path, allowed_arms):
    latest = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        arm, seed, repeat = row["run"]
        if arm not in allowed_arms or repeat != 0:
            continue
        year = int(row["date"][:4])
        key = (arm, seed, year)
        if key not in latest or row["date"] > latest[key]["date"]:
            latest[key] = row
    return latest


def paired_stats(indexed, variant, year, metric):
    seeds = sorted(
        seed for arm, seed, y in indexed
        if arm == variant and y == year and (BASELINE, seed, year) in indexed
    )
    pairs = [
        (indexed[variant, seed, year].get(metric), indexed[BASELINE, seed, year].get(metric))
        for seed in seeds
    ]
    pairs = [(variant_value, baseline_value) for variant_value, baseline_value in pairs
             if variant_value is not None and baseline_value is not None]
    deltas = [variant_value - baseline_value for variant_value, baseline_value in pairs]
    wins = sum(delta > 0 for delta in deltas)
    losses = sum(delta < 0 for delta in deltas)
    baseline_mean = statistics.mean(baseline_value for _, baseline_value in pairs) if pairs else None
    mean = statistics.mean(deltas) if deltas else None
    return {
        "n": len(deltas),
        "mean_variant_minus_baseline": round(mean, 6) if mean is not None else None,
        "median_variant_minus_baseline": round(statistics.median(deltas), 6) if deltas else None,
        "mean_difference_percent": (
            round(100 * mean / baseline_mean, 6) if mean is not None and baseline_mean else None
        ),
        "wins": wins,
        "losses": losses,
        "ties": len(deltas) - wins - losses,
        "sign_test_two_sided_p": round(sign_pvalue(wins, losses), 6) if wins + losses else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial", type=Path, required=True)
    parser.add_argument("--remaining", type=Path, required=True)
    parser.add_argument("--extension", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    indexed = {}
    indexed.update(load_year_ends(args.initial, {BASELINE, BUFFER}))
    indexed.update(load_year_ends(args.remaining, set(VARIANTS) - {BUFFER}))
    indexed.update(load_year_ends(args.extension, {BASELINE, *VARIANTS} - {BUFFER}))

    years = list(range(1970, 1980))
    trajectories = {}
    for variant in VARIANTS:
        trajectories[variant] = {
            str(year): {metric: paired_stats(indexed, variant, year, metric) for metric in METRICS}
            for year in years
        }
        expected_n = 20 if variant == BUFFER else 40
        for year in years:
            actual_n = trajectories[variant][str(year)]["company_value"]["n"]
            if actual_n != expected_n:
                raise SystemExit(f"serie incomplete: {variant} {year}: {actual_n}/{expected_n}")

    payload = {
        "years": years,
        "baseline": BASELINE,
        "variants": list(VARIANTS),
        "metric_direction": "variant minus baseline",
        "sources": {
            "initial": str(args.initial),
            "remaining": str(args.remaining),
            "extension": str(args.extension),
        },
        "trajectories": trajectories,
    }
    args.out.write_text(json.dumps(payload, indent=1) + "\n")
    print("ecrit", args.out)
    for variant in VARIANTS:
        print("\n", variant)
        print("year   value_delta  value_%  V/D/N    profit_delta   veh_delta   stations_delta")
        for year in years:
            row = trajectories[variant][str(year)]
            value = row["company_value"]
            print(
                f"{year} {value['mean_variant_minus_baseline']:>13.0f} "
                f"{value['mean_difference_percent']:>7.2f}% "
                f"{value['wins']:>2}/{value['losses']:<2}/{value['ties']:<2} "
                f"{row['profit_year']['mean_variant_minus_baseline']:>13.0f} "
                f"{row['n_vehicles']['mean_variant_minus_baseline']:>11.2f} "
                f"{row['n_stations']['mean_variant_minus_baseline']:>16.2f}"
            )


if __name__ == "__main__":
    main()
