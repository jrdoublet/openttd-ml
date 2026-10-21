#!/usr/bin/env python3
"""RAIL-CAL-1 step 1: SOLO-trained cost and net profit calibration, DUEL shadow.

Nothing is changed in ai/OpexAI or the simulated world. Five disjoint seed folds
exclude a DUEL seed from the SOLO data used to predict its score. Published
PORTFOLIO_RANK top-5 entries are *not* a counterfactual investable catalogue.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import median

import numpy as np

from analyse_calibration_quartiles import parse_logs
from demo_recentrage_rail_20261021 import load_snapshots


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results/calibration_pc_20261021/results"
SOLO = DATA / "calib_solo_40x10_pc_20261021_engine"
DUEL = DATA / "calib_duel_40x10_pc_20261021_engine"
OUT = ROOT / "evidence/review/roi_calibration_predictors_20261021/calibration_rail_jointe_20261021.json"
CUTS = (90, 127, 172)
PRIOR = 50
BOOTSTRAPS = 20000


def quartile(distance):
    return 1 + sum(float(distance) > cut for cut in CUTS)


def seed_of(row):
    return int(row["game"][1])


def fit_model(costs, profits):
    rc = [r for r in costs if r["mode"] == "rail" and r["predicted"] > 0]
    rp = [r for r in profits if r["mode"] == "rail" and r["predicted"] > 0]
    if len(rc) < 10 or len(rp) < 10:
        raise ValueError("Not enough valid SOLO rail cost/profit training rows")
    d = np.asarray([r["distance"] for r in rc], dtype=float)
    ratio = np.asarray([r["actual"] / r["predicted"] for r in rc], dtype=float)
    b, a = np.polyfit(d, ratio, 1)
    pooled = defaultdict(list)
    bycell = defaultdict(list)
    for r in rp:
        q = quartile(r["distance"])
        v = r["actual"] / r["predicted"]  # Negative annual profits are retained.
        pooled[q].append(v)
        bycell[(r["cargo"], q)].append(v)
    overall = median(v for rows in pooled.values() for v in rows)
    quartiles = {q: median(pooled[q]) if pooled[q] else overall for q in range(1, 5)}
    factors = {}
    cells = {}
    for (cargo, q), vals in sorted(bycell.items()):
        n = len(vals)
        r_cell = median(vals)
        r_q = quartiles[q]
        k = (n * r_cell + PRIOR * r_q) / (n + PRIOR)
        factors[f"{cargo}|Q{q}"] = float(k)
        cells[f"{cargo}|Q{q}"] = {"n": n, "cell_median": float(r_cell),
                                  "quartile_median": float(r_q), "k": float(k)}
    return {"a": float(a), "b": float(b), "cost_train_n": len(rc),
            "profit_train_n_line_years": len(rp), "shrinkage_prior": PRIOR,
            "quartile_profit": {str(q): float(v) for q, v in quartiles.items()},
            "global_profit": float(overall), "factors": factors, "cells": cells}


def cost_factor(model, d):
    value = model["a"] + model["b"] * float(d)
    if value <= 0:
        raise ValueError("Nonpositive projected RAIL capital correction")
    return value


def profit_factor(model, cargo, d):
    q = quartile(d)
    value = model["factors"].get(f"{cargo}|Q{q}", model["quartile_profit"][str(q)])
    if value <= 0:
        raise ValueError(f"Nonpositive fitted profit factor for {cargo}, Q{q}: {value}")
    return value


def rail_factor(model, cargo, d):
    return profit_factor(model, cargo, d) / cost_factor(model, d)


def score_factor(item, model):
    return rail_factor(model, item["cargo"], item["distance"]) if item["mode"] == "rail" else 1.0


def aggregate(items):
    before = sum(x["before"] for x in items)
    after = sum(x["after"] for x in items)
    return {"n": len(items), "before": round(before, 3), "after": round(after, 3),
            "factor": round(after / before, 7) if before > 0 else None,
            "delta_pct": round((after / before - 1) * 100, 3) if before > 0 else None}


def cluster_bootstrap(seed_mass):
    seeds = sorted(seed_mass)
    before = np.asarray([seed_mass[s][0] for s in seeds])
    after = np.asarray([seed_mass[s][1] for s in seeds])
    if len(seeds) < 2 or not np.all(before > 0):
        raise ValueError("Cluster bootstrap needs at least two positive-score seeds")
    rng = np.random.default_rng(20261021)
    choices = rng.integers(0, len(seeds), (BOOTSTRAPS, len(seeds)))
    values = (after[choices].sum(axis=1) / before[choices].sum(axis=1) - 1) * 100
    return [round(float(x), 3) for x in np.quantile(values, [0.025, 0.975])]


def shadow(snapshots, seed_models):
    scored = []
    all_modes = []
    changes = Counter()
    examples = []
    masses = defaultdict(lambda: [0., 0.])
    snapshots_n, original_not_max = 0, 0
    for snap in snapshots:
        rows = snap["items"]
        if not rows:
            continue
        model = seed_models[snap["seed"]]
        old = max(rows, key=lambda p: p["score"])
        ranked_old = min(rows, key=lambda p: p["rank"])
        if ranked_old is not old:
            original_not_max += 1
        for row in rows:
            f = score_factor(row, model)
            new_score = row["score"] * f
            group = max(0., row["score"])
            if row["mode"] == "rail" and group > 0:
                datum = {"seed": snap["seed"], "before": group, "after": group * f,
                         "quartile": "Q" + str(quartile(row["distance"])),
                         "cargo": row["cargo"], "year": snap["date"].split("-")[0],
                         "distance": row["distance"]}
                scored.append(datum)
                masses[snap["seed"]][0] += group
                masses[snap["seed"]][1] += group * f
            all_modes.append({"mode": row["mode"], "factor": f})
            row["joint_new_score"] = new_score
        new = max(rows, key=lambda p: p["joint_new_score"])
        snapshots_n += 1
        if old is not new:
            transition = old["mode"] + "->" + new["mode"]
            changes[transition] += 1
            if len(examples) < 15:
                examples.append({"seed": snap["seed"], "date": snap["date"],
                                 "from": old["mode"], "to": new["mode"],
                                 "historical_rank0": ranked_old["mode"],
                                 "old_score": old["score"], "new_score": new["joint_new_score"]})
    by = {}
    for name in ("quartile", "cargo", "year"):
        keys = sorted(set(x[name] for x in scored))
        by[name] = {key: aggregate([x for x in scored if x[name] == key]) for key in keys}
    modes = {}
    for m in sorted({x["mode"] for x in all_modes}):
        a = [x["factor"] for x in all_modes if x["mode"] == m]
        modes[m] = {"n": len(a), "factor_min": round(min(a), 7),
                    "factor_max": round(max(a), 7)}
    return {"weighted_rail_top5": aggregate(scored),
            "bootstrap_cluster_seed_ci95_delta_pct": cluster_bootstrap(masses),
            "mass_by": by, "mode_factor_guard": modes,
            "leader_numeric_transitions": dict(changes),
            "leader_numeric_changes": sum(changes.values()),
            "snapshots": snapshots_n, "historical_rank0_not_numeric_max": original_not_max,
            "examples": examples,
            "seeds": len(masses),
            "per_seed": {str(s): {"before": round(v[0], 2), "after": round(v[1], 2),
                                  "factor": round(v[1] / v[0], 6)}
                         for s, v in sorted(masses.items()) if v[0] > 0}}


def validation(costs, profits, models):
    """Four ablations evaluated on DUEL: cost and annual net profit in GBP.

    ROI is evaluated only when a mature profit year can be joined to a valid
    construction cost. Repeated line-years are not independent trials.
    """
    names = ("raw", "cost_only", "profit_only", "joint")
    cost_errors = {k: [] for k in names}
    profit_errors = {k: [] for k in names}
    profit_signed_errors = {k: [] for k in names}
    profit_by_cargo_quartile = defaultdict(lambda: defaultdict(list))
    roi_err = {k: [] for k in names}
    roi_ratios = defaultdict(lambda: defaultdict(list))
    obs_by_seed_line = defaultdict(list)
    cost_index = {(r["game"], r["line"]): r for r in costs if r["mode"] == "rail"}
    for r in costs:
        if r["mode"] != "rail":
            continue
        model = models[seed_of(r)]
        for k in names:
            cf = cost_factor(model, r["distance"]) if k in ("cost_only", "joint") else 1.
            cost_errors[k].append(abs(r["predicted"] * cf - r["actual"]))
    for r in profits:
        if r["mode"] != "rail":
            continue
        model = models[seed_of(r)]
        for k in names:
            pf = profit_factor(model, r["cargo"], r["distance"]) if k in ("profit_only", "joint") else 1.
            err = r["predicted"] * pf - r["actual"]
            profit_errors[k].append(abs(err))
            profit_signed_errors[k].append(err)
            profit_by_cargo_quartile[k][f'{r["cargo"]}|Q{quartile(r["distance"])}'].append(err)
        construction = cost_index.get((r["game"], r["line"]))
        if construction is None or construction["actual"] <= 0 or construction["predicted"] <= 0:
            continue
        real_roi = r["actual"] / construction["actual"] * 100
        for k in names:
            cf = cost_factor(model, r["distance"]) if k in ("cost_only", "joint") else 1.
            pf = profit_factor(model, r["cargo"], r["distance"]) if k in ("profit_only", "joint") else 1.
            pred_roi = r["predicted"] * pf / (construction["predicted"] * cf) * 100
            roi_err[k].append(pred_roi - real_roi)
            if pred_roi > 0:
                roi_ratios[k][quartile(r["distance"])].append(real_roi / pred_roi)
            obs_by_seed_line[(seed_of(r), r["line"])].append((k, pred_roi, real_roi))
    seed_ranks = defaultdict(lambda: defaultdict(list))
    for (seed, _line), observations in obs_by_seed_line.items():
        for k in names:
            selected = [r for r in observations if r[0] == k]
            if selected:
                seed_ranks[k][seed].append((median(r[1] for r in selected),
                                            median(r[2] for r in selected)))
    rank_quality = {}
    for k in names:
        correlations = []
        for seed, selected in seed_ranks[k].items():
            if len(selected) < 4:
                continue
            pred = np.array([x[0] for x in selected])
            real = np.array([x[1] for x in selected])
            if pred.std() > 1e-9 and real.std() > 1e-9:
                rp = np.argsort(np.argsort(pred))
                rr = np.argsort(np.argsort(real))
                correlations.append(float(np.corrcoef(rp, rr)[0, 1]))
        rank_quality[k] = {"seeds": len(correlations),
                           "median_within_seed_spearman": round(float(median(correlations)), 4)
                           if correlations else None}
    def error_summary(k):
        e = np.asarray(roi_err[k])
        return {"n_cost": len(cost_errors[k]),
                "cost_mae_gbp": round(float(np.mean(cost_errors[k])), 2),
                "n_profit_line_years": len(profit_errors[k]),
                "profit_mae_gbp_year": round(float(np.mean(profit_errors[k])), 2),
                "profit_bias_pred_minus_real_gbp_year": round(float(np.mean(profit_signed_errors[k])), 2),
                "n_roi_line_years": len(e),
                "roi_mae_points": round(float(np.mean(np.abs(e))), 3),
                "roi_bias_points": round(float(np.mean(e)), 3),
                "roi_ranking": rank_quality[k],
                "roi_real_over_pred_median_by_quartile": {
                    "Q" + str(q): round(float(median(roi_ratios[k][q])), 4)
                    if roi_ratios[k][q] else None for q in range(1, 5)}}
    summary = {k: error_summary(k) for k in names}
    summary["profit_error_by_cargo_quartile"] = {
        k: {cell: {"n": len(errs), "mae_gbp_year": round(float(np.mean(np.abs(errs))), 2),
                   "bias_pred_minus_real_gbp_year": round(float(np.mean(errs)), 2)}
            for cell, errs in sorted(by.items())}
        for k, by in profit_by_cargo_quartile.items()}
    return summary


def run(solo_path, duel_path):
    _, solo_costs, solo_profits, solo_counts = parse_logs(str(solo_path), "solo")
    _, duel_costs, duel_profits, duel_counts = parse_logs(str(duel_path), "duel")
    solo_snaps = load_snapshots(str(solo_path))
    duel_snaps = load_snapshots(str(duel_path))
    solo_seeds = set(seed_of(r) for r in solo_costs)
    duel_seeds = set(seed_of(r) for r in duel_costs)
    seeds = sorted(solo_seeds & duel_seeds)
    if len(seeds) != 40 or solo_counts["games"] != 40 or duel_counts["games"] != 40:
        raise ValueError(f"Expected 40 SOLO and DUEL matched seeds; got {len(seeds)}")
    full = fit_model(solo_costs, solo_profits)
    seed_models, fold_meta = {}, []
    for fold in range(5):
        held = set(seeds[fold::5])
        model = fit_model([r for r in solo_costs if seed_of(r) not in held],
                          [r for r in solo_profits if seed_of(r) not in held])
        for seed in held:
            seed_models[seed] = model
        fold_meta.append({"fold": fold, "test_seeds": sorted(held),
                          "train_cost_n": model["cost_train_n"],
                          "train_profit_n": model["profit_train_n_line_years"],
                          "a": model["a"], "b": model["b"]})
    shadow_report = shadow(duel_snaps, seed_models)
    validated = validation(duel_costs, duel_profits, seed_models)
    flat = validated["joint"]["roi_real_over_pred_median_by_quartile"]
    flat_ratio = (flat["Q1"] / flat["Q4"] if flat["Q4"] else None)
    return {"source": {"solo": str(solo_path), "duel": str(duel_path),
                       "solo_counts": solo_counts, "duel_counts": duel_counts,
                       "solo_top5_snapshots": len(solo_snaps), "duel_top5_snapshots": len(duel_snaps)},
            "method": {"distance_quartile_cuts": CUTS, "fit": "OLS SOLO cost ratio actual/quoted ~ a+b*d; SOLO median mature net-profit realization cargo x distance quartile shrunk toward quartile (n+50)",
                       "validation": "5 folds, 8 held-out DUEL seeds/fold, no SOLO same-seed training",
                       "weights": "positive historical rail top-5 rank_score; raw RAIL candidate score, no normalization",
                       "bootstrap": "20,000 cluster resamples of 40 distinct seeds, RNG seed=20261021"},
            "fixed_constants_full_solo": full, "folds": fold_meta,
            "shadow": shadow_report, "ablations_duel": validated,
            "joint_roi_flatness_q1_over_q4": round(flat_ratio, 4) if flat_ratio else None,
            "warnings": ["RAIL selected construction ROI and profit are noncausal samples",
                         "Physical quote after A* is already exact; only pre-A* score is targeted",
                         "Historical top-5 are not all fundable candidates; C77 tiers and AIR bonuses remain",
                         "Mature line-year repeats are not independent; 95% CI uses top-5 score per seed",
                         "No changes to AIR, AIR fleet, ROAD, AI code, or runtime"]}


def selftest():
    costs = [{"mode": "rail", "distance": float(d), "actual": 1000 * (1.1 + .003 * d),
              "predicted": 1000} for d in (30, 40, 50, 80, 100, 120, 150, 175, 200, 250)]
    profits = [{"mode": "rail", "cargo": "COAL", "distance": float(d),
                "actual": 1000 * (0.6 if d <= 90 else 1.2), "predicted": 1000}
               for d in (30, 40, 50, 80, 100, 120, 150, 175, 200, 250)]
    model = fit_model(costs, profits)
    assert abs(model["a"] - 1.1) < 1e-8
    assert abs(model["b"] - .003) < 1e-8
    assert profit_factor(model, "COAL", 60) < profit_factor(model, "COAL", 200)
    assert score_factor({"mode": "air", "cargo": "PASS", "distance": 80}, model) == 1.
    assert quartile(90) == 1 and quartile(127) == 2 and quartile(172) == 3
    assert cluster_bootstrap({i: (100, 80) for i in range(40)}) == [-20., -20.]
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--solo", type=Path, default=SOLO)
    ap.add_argument("--duel", type=Path, default=DUEL)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    result = run(args.solo, args.duel)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("JSON", args.out)
    print("FULL SOLO", result["fixed_constants_full_solo"]["a"], result["fixed_constants_full_solo"]["b"])
    print("SHADOW", result["shadow"]["weighted_rail_top5"], result["shadow"]["bootstrap_cluster_seed_ci95_delta_pct"])
    print("BY", json.dumps(result["shadow"]["mass_by"], ensure_ascii=False))
    print("TRANSITIONS", result["shadow"]["leader_numeric_transitions"])
    print("ABLATIONS", result["ablations_duel"])


if __name__ == "__main__":
    main()
