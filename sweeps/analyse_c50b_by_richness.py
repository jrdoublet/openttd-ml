"""Teste si les effets C50b dependent de la richesse initiale de la graine.

La richesse primaire est la valeur de la reference seule fin 1971. Ce choix evite de classer une
graine avec la metrique finale qui sert aussi a calculer l'effet du traitement. Les annees 1970 et
1972 servent uniquement de sensibilite pre-enregistree.
"""
import argparse
import json
import math
from pathlib import Path
import random
import statistics
import sys

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from analyse_c50b_by_year import BASELINE, BUFFER, VARIANTS, load_year_ends

OUTCOME_YEAR = 1979
PRIMARY_RICHNESS_YEAR = 1971
SENSITIVITY_YEARS = (1970, 1972)
METRICS = (
    "company_value", "company_value_pct", "profit_year", "profit_year_pct",
    "performance_history", "n_vehicles", "n_stations",
)
PERMUTATIONS = 50_000


def rankdata(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    pos = 0
    while pos < len(order):
        end = pos + 1
        while end < len(order) and values[order[end]] == values[order[pos]]:
            end += 1
        rank = (pos + end - 1) / 2.0
        for idx in order[pos:end]:
            ranks[idx] = rank
        pos = end
    return ranks


def correlation(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs)
    dy = sum((y - my) ** 2 for y in ys)
    return numerator / math.sqrt(dx * dy) if dx and dy else 0.0


def spearman(xs, ys):
    return correlation(rankdata(xs), rankdata(ys))


def permutation_pvalue(richness, effects, observed, statistic, seed):
    rng = random.Random(seed)
    shuffled = list(effects)
    extreme = 0
    for _ in range(PERMUTATIONS):
        rng.shuffle(shuffled)
        if abs(statistic(richness, shuffled)) >= abs(observed) - 1e-12:
            extreme += 1
    return (extreme + 1) / (PERMUTATIONS + 1)


def group_summary(seeds, richness, effects):
    values = [effects[seed] for seed in seeds]
    rich_values = [richness[seed] for seed in seeds]
    return {
        "n": len(seeds),
        "seeds": seeds,
        "mean_richness": round(statistics.mean(rich_values), 6),
        "mean_effect": round(statistics.mean(values), 6),
        "median_effect": round(statistics.median(values), 6),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "ties": sum(value == 0 for value in values),
    }


def paired_effect(indexed, variant, seed, metric):
    if metric.endswith("_pct"):
        source = metric[:-4]
        baseline = indexed[BASELINE, seed, OUTCOME_YEAR][source]
        delta = indexed[variant, seed, OUTCOME_YEAR][source] - baseline
        return 100.0 * delta / baseline if baseline else 0.0
    return indexed[variant, seed, OUTCOME_YEAR][metric] - indexed[BASELINE, seed, OUTCOME_YEAR][metric]


def interaction(indexed, variant, metric, richness_year):
    seeds = sorted(
        seed for arm, seed, year in indexed
        if arm == variant and year == OUTCOME_YEAR
        and (BASELINE, seed, OUTCOME_YEAR) in indexed
        and (BASELINE, seed, richness_year) in indexed
    )
    richness = {seed: indexed[BASELINE, seed, richness_year]["company_value"] for seed in seeds}
    effects = {seed: paired_effect(indexed, variant, seed, metric) for seed in seeds}
    ordered = sorted(seeds, key=lambda seed: (richness[seed], seed))
    half = len(ordered) // 2
    quartile = max(1, len(ordered) // 4)
    poor, rich = ordered[:half], ordered[half:]
    poorest, richest = ordered[:quartile], ordered[-quartile:]

    xs = [richness[seed] for seed in ordered]
    ys = [effects[seed] for seed in ordered]
    rho = spearman(xs, ys)

    def half_gap(_, shuffled_effects):
        return statistics.mean(shuffled_effects[half:]) - statistics.mean(shuffled_effects[:half])

    gap = statistics.mean(effects[seed] for seed in rich) - statistics.mean(effects[seed] for seed in poor)
    return {
        "richness_year": richness_year,
        "poor_half": group_summary(poor, richness, effects),
        "rich_half": group_summary(rich, richness, effects),
        "poorest_quartile": group_summary(poorest, richness, effects),
        "richest_quartile": group_summary(richest, richness, effects),
        "rich_minus_poor_mean_effect": round(gap, 6),
        "half_interaction_permutation_p": round(
            permutation_pvalue(xs, ys, gap, half_gap, 5000 + richness_year + len(metric)), 6
        ),
        "spearman_rho": round(rho, 6),
        "spearman_permutation_p": round(
            permutation_pvalue(xs, ys, rho, spearman, 9000 + richness_year + len(metric)), 6
        ),
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

    analyses = {}
    for variant in VARIANTS:
        analyses[variant] = {}
        for metric in METRICS:
            analyses[variant][metric] = {
                "primary": interaction(indexed, variant, metric, PRIMARY_RICHNESS_YEAR),
                "sensitivity": {
                    str(year): interaction(indexed, variant, metric, year)
                    for year in SENSITIVITY_YEARS
                },
            }

    payload = {
        "definition": "baseline company_value at end of 1971; outcome is variant-baseline at end of 1979",
        "primary_richness_year": PRIMARY_RICHNESS_YEAR,
        "sensitivity_years": list(SENSITIVITY_YEARS),
        "permutations": PERMUTATIONS,
        "sources": {
            "initial": str(args.initial),
            "remaining": str(args.remaining),
            "extension": str(args.extension),
        },
        "analyses": analyses,
    }
    args.out.write_text(json.dumps(payload, indent=1) + "\n")
    print("ecrit", args.out)
    for variant in VARIANTS:
        print("\n", variant)
        for metric in ("company_value", "company_value_pct", "profit_year_pct", "n_vehicles"):
            row = analyses[variant][metric]["primary"]
            print(
                f"{metric:20} poor={row['poor_half']['mean_effect']:>11.0f} "
                f"rich={row['rich_half']['mean_effect']:>11.0f} "
                f"rich-poor={row['rich_minus_poor_mean_effect']:>11.0f} "
                f"p={row['half_interaction_permutation_p']:.3f} "
                f"rho={row['spearman_rho']:+.3f} p_rho={row['spearman_permutation_p']:.3f}"
            )


if __name__ == "__main__":
    main()
