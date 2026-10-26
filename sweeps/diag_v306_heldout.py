#!/usr/bin/env python3
"""V306: read-only calibration exposure on independent historical seeds.

The target is the existing RAIL-CAL4 reference arm, NOT its intervened arm.
The training SOLO and held-out multimodal reference runs have different source
policies/protocols: this reports transfer coverage, not a causal profit gain
or evidence sufficient to enable a model in the AI.

Usage:
  python -X utf8 sweeps/diag_v306_heldout.py \
    --train results/calibration_pc_20261021/results/calib_solo_40x10_pc_20261021_engine \
    --heldout results/rail_cal4_40x10_multimodal_pc_20261021_engine \
    --out results/v306_heldout_20261026.json
"""

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from statistics import median

try:
    from sweeps.analyse_calibration_projets import (
        MIN_CELL, cell_seed_support, cross_validate, factor_tables,
        load_campaign, predict_error, ratio,
    )
except ModuleNotFoundError:
    from analyse_calibration_projets import (
        MIN_CELL, cell_seed_support, cross_validate, factor_tables,
        load_campaign, predict_error, ratio,
    )


def seed_balanced_error(heldout, modes, cells):
    """Median of each independent seed's median errors, not of line-years.

    Multiple arms or repetitions of one seed remain a single unit. This is a
    descriptive sensitivity check; factors and the original micro score stay
    unchanged, and seeds with no valid ratios have explicitly missing scores.
    """
    by_seed = defaultdict(dict)
    for key, game in heldout.items():
        by_seed[key[1]][key] = game
    rows = []
    for seed, games in sorted(by_seed.items()):
        scores = predict_error(games, modes, cells)
        rows.append({"seed": seed, "n_valid_rows": scores["n"],
                     **{metric: scores[metric] for metric in ("raw", "mode", "cell")}})
    valid = [row for row in rows if row["n_valid_rows"] > 0]
    return {
        "distinct_seeds": len(rows),
        "seeds_with_valid_rows": len(valid),
        "seeds_without_valid_rows": [row["seed"] for row in rows
                                     if row["n_valid_rows"] == 0],
        "median_of_seed_medians": {
            metric: round(median(row[metric] for row in valid), 4) if valid else None
            for metric in ("raw", "mode", "cell")
        },
        "by_seed": rows,
    }


ABLATION = ("raw", "mode", "mode_cargo", "mode_distance", "mode_era", "cell")


def _ablation_key(row, variable):
    """Key for one marginal variable; keep the original cell's binning."""
    parts = row["cell"].split("|")
    if len(parts) != 4 or parts[0] != row["mode"]:
        raise ValueError(f"V306 inconsistent calibration cell: {row['cell']!r}")
    positions = {"mode_cargo": 1, "mode_distance": 2, "mode_era": 3, "cell": None}
    return row["cell"] if variable == "cell" else f"{parts[0]}|{parts[positions[variable]]}"


def ablate_variables(train, heldout, modes, cells):
    """Disjoint-seed marginal ablation of revenue factors, without refitting on test.

    Every extension uses the historical MIN_CELL line-year threshold and falls
    straight back to the same mode factor when support is too small. Its seed
    support is descriptive: MIN_CELL itself does not enforce independent seeds.
    """
    variables = ("mode_cargo", "mode_distance", "mode_era")
    grouped = {name: defaultdict(list) for name in variables}
    seed_support = {name: defaultdict(set) for name in variables}
    for (_, seed), game in train.items():
        for row in game["rows"]:
            value = ratio(row["real_rev"], row["pred_rev"], row["scale"])
            if value is None:
                continue
            for variable in variables:
                key = _ablation_key(row, variable)
                grouped[variable][key].append(value)
                seed_support[variable][key].add(seed)
    factors = {
        name: {key: (median(values), len(values))
               for key, values in groups.items()}
        for name, groups in grouped.items()
    }
    training_support = {
        name: {
            "groups_with_valid_rows": len(groups),
            "groups_eligible_by_line_years": sum(len(values) >= MIN_CELL
                                                  for values in groups.values()),
            "eligible_groups_with_at_least_5_seeds": sum(
                len(values) >= MIN_CELL and len(seed_support[name][key]) >= 5
                for key, values in groups.items()),
        }
        for name, groups in grouped.items()
    }
    losses = {name: [] for name in ABLATION}
    per_mode = defaultdict(lambda: {name: [] for name in ABLATION})
    per_seed = defaultdict(lambda: {name: [] for name in ABLATION})
    for _, seed in heldout:
        _ = per_seed[seed]  # Even a seed with no valid revenue rows is observed.
    selected = Counter()
    fallback = Counter()
    for (_, seed), game in heldout.items():
        for row in game["rows"]:
            value = ratio(row["real_rev"], row["pred_rev"], row["scale"])
            if value is None:
                continue
            fm = modes.get(row["mode"], 1.0)
            selected_factors = {"raw": 1.0, "mode": fm}
            for variable in variables + ("cell",):
                key = row["cell"] if variable == "cell" else _ablation_key(row, variable)
                candidate = (cells if variable == "cell" else factors[variable]).get(key)
                if candidate and candidate[1] >= MIN_CELL:
                    selected_factors[variable] = candidate[0]
                    selected[variable] += 1
                else:
                    selected_factors[variable] = fm
                    fallback[variable] += 1
            for variable, factor in selected_factors.items():
                error = abs(math.log(value / factor))
                losses[variable].append(error)
                per_mode[row["mode"]][variable].append(error)
                per_seed[seed][variable].append(error)

    def scores(groups):
        return {name: round(median(groups[name]), 4) if groups[name] else None
                for name in ABLATION}

    per_seed_scores = {
        seed: {"n_valid_rows": len(group["raw"]), **scores(group)}
        for seed, group in sorted(per_seed.items())
    }
    valid_seed_scores = [group for group in per_seed_scores.values()
                         if group["n_valid_rows"]]
    seed_balanced = {
        name: (round(median(group[name] for group in valid_seed_scores), 4)
               if valid_seed_scores else None)
        for name in ABLATION
    }
    return {
        "n_valid_heldout_rows": len(losses["raw"]),
        "micro_median_abs_log_error": scores(losses),
        "seed_balanced_median_of_seed_medians": seed_balanced,
        "n_distinct_heldout_seeds": len({seed for _, seed in heldout}),
        "n_heldout_seeds_with_valid_rows": len(valid_seed_scores),
        "by_mode": {mode: {"n_valid_rows": len(group["raw"]), **scores(group)}
                    for mode, group in sorted(per_mode.items())},
        "by_seed": [{"seed": seed, **data} for seed, data in per_seed_scores.items()],
        "trained_variable_support": training_support,
        "heldout_rows_using_group_factor": {
            name: selected[name] for name in variables + ("cell",)
        },
        "heldout_rows_falling_back_to_mode": {
            name: fallback[name] for name in variables + ("cell",)
        },
    }


def evaluate(train, heldout):
    """Fit solely on training games, evaluate all held-out reference games."""
    if not train or not heldout:
        raise ValueError("V306 requires nonempty training and held-out reference runs")
    train_seeds = {seed for _, seed in train}
    test_seeds = {seed for _, seed in heldout}
    overlap = sorted(train_seeds & test_seeds)
    if overlap:
        raise ValueError(f"V306 training/heldout seeds overlap: {overlap}")

    modes, cells = factor_tables(train)
    support_train = cell_seed_support(train)
    support_test = cell_seed_support(heldout)
    prediction = predict_error(heldout, modes, cells)
    seed_balanced = seed_balanced_error(heldout, modes, cells)
    ablation = ablate_variables(train, heldout, modes, cells)
    if (ablation["n_valid_heldout_rows"] != prediction["n"]
            or any(ablation["heldout_rows_using_group_factor"][name]
                   + ablation["heldout_rows_falling_back_to_mode"][name]
                   != prediction["n"] for name in ("mode_cargo", "mode_distance",
                                                "mode_era", "cell"))
            or any(ablation["micro_median_abs_log_error"][name] != prediction[name]
                   for name in ("raw", "mode", "cell"))
            or any(ablation["seed_balanced_median_of_seed_medians"][name]
                   != seed_balanced["median_of_seed_medians"][name]
                   for name in ("raw", "mode", "cell"))):
        raise ValueError("V306 ablation does not reconcile with historical scores")
    valid_train = sum(s["n_valid_rows"] for s in support_train.values())
    valid_test = sum(s["n_valid_rows"] for s in support_test.values())
    if prediction["n"] != valid_test:
        raise ValueError("V306 valid test observation coverage contradiction")
    if sum(row["n_valid_rows"] for row in seed_balanced["by_seed"]) != valid_test:
        raise ValueError("V306 seed-balanced observation coverage contradiction")
    row_count = sum(len(game["rows"]) for game in heldout.values())
    mode_scores = {}
    for mode in sorted({row["mode"] for game in heldout.values() for row in game["rows"]}):
        subset = {
            key: {**game, "rows": [row for row in game["rows"] if row["mode"] == mode]}
            for key, game in heldout.items()
        }
        mode_scores[mode] = predict_error(subset, modes, cells)
    if sum(scores["n"] for scores in mode_scores.values()) != prediction["n"]:
        raise ValueError("V306 modal count does not reconcile")

    eligible_cells = {
        name: {
            "factor": round(factor, 6),
            "n_valid_train_rows": n,
            "n_distinct_train_seeds": support_train[name]["n_distinct_seeds"],
            "max_train_seed_share": support_train[name]["max_seed_share"],
            "n_valid_heldout_rows": support_test.get(name, {}).get("n_valid_rows", 0),
        }
        for name, (factor, n) in sorted(cells.items()) if n >= MIN_CELL
    }
    folds = cross_validate(train, heldout)
    if sum(fold["n"] for fold in folds) != prediction["n"]:
        raise ValueError("V306 held-out folds do not cover all valid rows")

    return {
        "scope": "historical independent-world revenue calibration exposure only",
        "training": {
            "games": len(train), "distinct_seeds": len(train_seeds),
            "mature_line_years": sum(len(g["rows"]) for g in train.values()),
            "valid_revenue_rows": valid_train,
            "unmatched_line_reports": sum(g["unmatched"] for g in train.values()),
        },
        "heldout": {
            "games": len(heldout), "distinct_seeds": len(test_seeds),
            "mature_line_years": row_count,
            "valid_revenue_rows": valid_test,
            "invalid_or_missing_revenue_ratio_rows": row_count - valid_test,
            "unmatched_line_reports": sum(g["unmatched"] for g in heldout.values()),
        },
        "train_and_heldout_seed_overlap": overlap,
        "min_cell_valid_train_rows": MIN_CELL,
        "learned_mode_revenue_factors": {
            name: round(value, 6) for name, value in sorted(modes.items())
        },
        "eligible_training_cells": eligible_cells,
        "heldout_median_abs_log_error": prediction,
        "heldout_seed_balanced_error": seed_balanced,
        "heldout_revenue_variable_ablation": ablation,
        "heldout_error_by_mode": mode_scores,
        "heldout_seed_folds": [
            {key: fold[key] for key in ("fold", "raw", "mode", "cell", "n")}
            for fold in folds
        ],
        "heldout_cell_seed_support": support_test,
        "limits": [
            "Training SOLO and RAIL-CAL4 multimodal reference have different "
            "code, difficulty/scenario or rival settings; source bundles are not "
            "proven equivalent.",
            "Revenue factors concern mature constructed lines (age >= 2), "
            "normalized to their initial fleets; not project profit, ROI or CAPEX.",
            "A single cell may have many line-years from one seed; "
            "MIN_CELL is a line-year count, not independent-seed support.",
            "The seed-balanced check gives each held-out seed one median, "
            "regardless of its line-year count; it is not a causal gain estimate.",
            "Only already constructed lines have realized revenue. No failed "
            "project counterfactual, causality, door A/B or default adoption.",
            "Marginal mode+one-variable revenue factors only; sparse groups "
            "fall back to mode, and line-year support is not independent-seed support.",
        ],
    }


def analyze(train_path, heldout_path, train_arm="reference", heldout_arm="reference",
            expected_train=40, expected_heldout=40):
    if Path(train_path).resolve() == Path(heldout_path).resolve():
        raise ValueError("V306 training and heldout directories must differ")
    train = load_campaign(str(train_path), arm=train_arm)
    heldout = load_campaign(str(heldout_path), arm=heldout_arm)
    if len(train) != expected_train or len(heldout) != expected_heldout:
        raise ValueError(
            f"V306 expected {expected_train} training and {expected_heldout} heldout "
            f"logical games; got {len(train)} and {len(heldout)}"
        )
    result = evaluate(train, heldout)
    result["sources"] = {
        "train_folder": str(Path(train_path)),
        "train_arm": train_arm,
        "heldout_folder": str(Path(heldout_path)),
        "heldout_arm": heldout_arm,
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", required=True, type=Path)
    parser.add_argument("--heldout", required=True, type=Path)
    parser.add_argument("--train-arm", default="reference")
    parser.add_argument("--heldout-arm", default="reference")
    parser.add_argument("--expected-train", type=int, default=40)
    parser.add_argument("--expected-heldout", type=int, default=40)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.expected_train < 1 or args.expected_heldout < 1:
            raise ValueError("expected game counts must be positive")
        if args.out is not None and args.out.exists():
            raise ValueError(f"existing held-out report: {args.out}")
        report = analyze(args.train, args.heldout, args.train_arm,
                         args.heldout_arm, args.expected_train, args.expected_heldout)
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        print(json.dumps({
            "training": report["training"], "heldout": report["heldout"],
            "errors": report["heldout_median_abs_log_error"],
            "seed_overlap": report["train_and_heldout_seed_overlap"],
            "out": str(args.out) if args.out is not None else None,
        }, ensure_ascii=False, allow_nan=False))
    except (OSError, ValueError, EOFError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
