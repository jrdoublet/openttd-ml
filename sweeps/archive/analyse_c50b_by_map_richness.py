"""Teste les interactions C50b avec la richesse initiale, exogene, de la carte."""
import argparse
import json
import math
from pathlib import Path
import statistics

import numpy as np

from analyse_c50b_by_richness import correlation, rankdata

BASELINE = "OpexAI"
METRICS = (
    "company_value", "company_value_pct", "profit_year", "profit_year_pct",
    "performance_history", "n_vehicles", "n_stations",
)
FEATURES = (
    "richness_rank_composite", "n_towns", "mean_town_population",
    "total_population", "max_town_population", "n_industries",
)
PERMUTATIONS = 20_000
INDUSTRY_THRESHOLD = 50


def percentile_ranks(records, field):
    values = [record[field] for record in records]
    ranks = rankdata(values)
    denominator = max(1, len(values) - 1)
    return {record["seed"]: rank / denominator for record, rank in zip(records, ranks)}


def add_composite(records):
    components = [
        percentile_ranks(records, "n_towns"),
        percentile_ranks(records, "mean_town_population"),
        percentile_ranks(records, "n_industries"),
    ]
    for record in records:
        seed = record["seed"]
        record["richness_rank_composite"] = statistics.mean(part[seed] for part in components)


def permutation_pvalues(xs, ys, observed_gap, observed_rho, rng):
    """Calcule les deux tests avec les memes permutations vectorisees."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    permutations = np.argsort(rng.random((PERMUTATIONS, len(ys))), axis=1)
    shuffled = ys[permutations]
    half = len(ys) // 2
    gaps = shuffled[:, half:].mean(axis=1) - shuffled[:, :half].mean(axis=1)

    ranked_xs = np.asarray(rankdata(xs.tolist()), dtype=float)
    ranked_ys = np.asarray(rankdata(ys.tolist()), dtype=float)
    centered_xs = ranked_xs - ranked_xs.mean()
    centered_ys = ranked_ys - ranked_ys.mean()
    denominator = np.sqrt(np.sum(centered_xs ** 2) * np.sum(centered_ys ** 2))
    rhos = ((centered_ys[permutations] @ centered_xs) / denominator
            if denominator else np.zeros(PERMUTATIONS))
    gap_p = (np.count_nonzero(np.abs(gaps) >= abs(observed_gap) - 1e-12) + 1) / (PERMUTATIONS + 1)
    rho_p = (np.count_nonzero(np.abs(rhos) >= abs(observed_rho) - 1e-12) + 1) / (PERMUTATIONS + 1)
    return gap_p, rho_p


def effect(indexed, variant, seed, metric):
    baseline = indexed[BASELINE, seed]
    treated = indexed[variant, seed]
    if metric.endswith("_pct"):
        source = metric[:-4]
        delta = treated[source] - baseline[source]
        return 100.0 * delta / baseline[source] if baseline[source] else 0.0
    return treated[metric] - baseline[metric]


def group(seeds, feature, effects):
    values = [effects[seed] for seed in seeds]
    return {
        "n": len(seeds),
        "seeds": seeds,
        "mean_feature": round(statistics.mean(feature[seed] for seed in seeds), 6),
        "mean_effect": round(statistics.mean(values), 6),
        "median_effect": round(statistics.median(values), 6),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "ties": sum(value == 0 for value in values),
    }


def analyse_feature(indexed, variant, metric, feature_by_seed, rng):
    seeds = sorted(
        seed for arm, seed in indexed
        if arm == variant and (BASELINE, seed) in indexed and seed in feature_by_seed
    )
    ordered = sorted(seeds, key=lambda seed: (feature_by_seed[seed], seed))
    half = len(ordered) // 2
    quartile = max(1, len(ordered) // 4)
    poor, rich = ordered[:half], ordered[half:]
    effects = {seed: effect(indexed, variant, seed, metric) for seed in ordered}
    xs = [feature_by_seed[seed] for seed in ordered]
    ys = [effects[seed] for seed in ordered]
    ranked_xs = rankdata(xs)
    ranked_ys = rankdata(ys)
    rho = correlation(ranked_xs, ranked_ys)
    gap = statistics.mean(effects[seed] for seed in rich) - statistics.mean(
        effects[seed] for seed in poor
    )

    gap_p, rho_p = permutation_pvalues(xs, ys, gap, rho, rng)

    return {
        "poor_half": group(poor, feature_by_seed, effects),
        "rich_half": group(rich, feature_by_seed, effects),
        "poorest_quartile": group(ordered[:quartile], feature_by_seed, effects),
        "richest_quartile": group(ordered[-quartile:], feature_by_seed, effects),
        "rich_minus_poor_mean_effect": round(gap, 6),
        "half_interaction_permutation_p": round(gap_p, 6),
        "spearman_rho": round(rho, 6),
        "spearman_permutation_p": round(rho_p, 6),
    }


def feature_correlations(records):
    return {
        left: {
            right: round(correlation(
                [record[left] for record in records],
                [record[right] for record in records],
            ), 6)
            for right in FEATURES if right != left
        }
        for left in FEATURES
    }


def sign_pvalue(values):
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    n = wins + losses
    if not n:
        return None
    tail = sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def industry_threshold_summary(indexed, variant, metric, seeds, by_seed):
    groups = {
        "below_50": [seed for seed in seeds if by_seed[seed]["n_industries"] < INDUSTRY_THRESHOLD],
        "at_least_50": [seed for seed in seeds if by_seed[seed]["n_industries"] >= INDUSTRY_THRESHOLD],
    }
    out = {}
    for name, selected in groups.items():
        values = [effect(indexed, variant, seed, metric) for seed in selected]
        pvalue = sign_pvalue(values)
        out[name] = {
            "n": len(values), "seeds": selected,
            "mean_effect": round(statistics.mean(values), 6),
            "wins": sum(value > 0 for value in values),
            "losses": sum(value < 0 for value in values),
            "ties": sum(value == 0 for value in values),
            "sign_test_two_sided_p": round(pvalue, 6) if pvalue is not None else None,
        }
    out["at_least_50_minus_below_50"] = round(
        out["at_least_50"]["mean_effect"] - out["below_50"]["mean_effect"], 6
    )
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench", type=Path, required=True)
    parser.add_argument("--maps", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    bench = json.loads(args.bench.read_text())
    maps = json.loads(args.maps.read_text())
    records = [dict(record) for record in maps["records"]]
    add_composite(records)
    by_seed = {record["seed"]: record for record in records}
    indexed = {
        (record["arm"], record["seed"]): record
        for record in bench["summary"] if record["run_ok"]
    }
    variants = [arm for arm in bench["arms"] if arm != BASELINE]
    rng = np.random.default_rng(20260912)
    analyses = {
        variant: {
            metric: {
                feature: analyse_feature(
                    indexed, variant, metric,
                    {seed: record[feature] for seed, record in by_seed.items()}, rng,
                )
                for feature in FEATURES
            }
            for metric in METRICS
        }
        for variant in variants
    }
    seed_blocks = {
        "initial_20": bench["seeds"][:20],
        "extension_20": bench["seeds"][20:],
        "all_40": bench["seeds"],
    }
    threshold_analysis = {
        variant: {
            metric: {
                block: industry_threshold_summary(indexed, variant, metric, seeds, by_seed)
                for block, seeds in seed_blocks.items()
                if all((variant, seed) in indexed for seed in seeds)
            }
            for metric in METRICS
        }
        for variant in variants
    }
    payload = {
        "definition": (
            "initial passive map snapshot; primary composite is the equal-weight mean of "
            "within-sample percentile ranks for town count, mean town population, and industry count"
        ),
        "classification_warning": (
            "the composite is descriptive; component analyses remain primary because map features "
            "are correlated and different transport modes use different opportunities"
        ),
        "permutations": PERMUTATIONS,
        "sources": {"bench": str(args.bench), "maps": str(args.maps)},
        "map_records": records,
        "feature_correlations": feature_correlations(records),
        "analyses": analyses,
        "industry_threshold_analysis": {
            "threshold": INDUSTRY_THRESHOLD,
            "status": "post-hoc descriptive threshold; requires a new adaptive paired bench",
            "blocks": seed_blocks,
            "analyses": threshold_analysis,
        },
    }
    args.out.write_text(json.dumps(payload, indent=1) + "\n")
    print("ecrit", args.out)
    for variant in variants:
        print("\n", variant)
        for feature in ("richness_rank_composite", "n_towns", "mean_town_population", "n_industries"):
            row = analyses[variant]["company_value_pct"][feature]
            print(
                f"{feature:26} poor={row['poor_half']['mean_effect']:+8.2f}% "
                f"rich={row['rich_half']['mean_effect']:+8.2f}% "
                f"gap={row['rich_minus_poor_mean_effect']:+8.2f} "
                f"p={row['half_interaction_permutation_p']:.3f} "
                f"rho={row['spearman_rho']:+.3f} p_rho={row['spearman_permutation_p']:.3f}"
            )


if __name__ == "__main__":
    main()
