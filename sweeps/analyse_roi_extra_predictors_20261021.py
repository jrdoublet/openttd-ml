#!/usr/bin/env python3
"""Ablations des variables reseau, materiel, reutilisation et geometrie.

Ne relance aucun banc. Les variables de reseau sont figees au moment de
PROJECT_CHOSEN ; les variables BUILD/RAIL_ATTEMPT sont des diagnostics
posterieurs, interdits dans un score au catalogue tant qu'une valeur
equivalente n'est pas disponible et journalisee a la selection.
"""
import argparse
import json
import math
import os
from collections import Counter, defaultdict
from glob import glob

import numpy as np

from analyse_calibration_projets import KV_RE, LINE_RE, SEED_RE, open_text
from analyse_roi_predictors_20261021 import parse, num, med


def features_per_build(folder):
    """Network state is computed on *earlier* builds; never uses later lines."""
    result = {}
    qc = Counter()
    for file in sorted(glob(os.path.join(folder, "*.log")) + glob(os.path.join(folder, "*.log.gz"))):
        match = SEED_RE.search(os.path.basename(file).replace(".gz", ""))
        if not match:
            continue
        seed = int(match.group(1))
        degree = defaultdict(Counter)
        directed = defaultdict(Counter)
        current = Counter()
        chosen = {}
        attempts = {}
        with open_text(file) as fh:
            for raw in fh:
                match_line = LINE_RE.search(raw)
                if match_line is None:
                    continue
                tag = match_line.group(4)
                if tag not in ("PROJECT_CHOSEN", "AIR_BUILD", "RAIL_BUILD",
                               "ROAD_BUILD", "RAIL_ATTEMPT"):
                    continue
                kv = dict(KV_RE.findall(match_line.group(5)))
                mode = (tag.split("_")[0].lower() if tag != "PROJECT_CHOSEN" else kv.get("mode"))
                src, dst = kv.get("src"), kv.get("dst")
                if not mode or src is None or dst is None:
                    continue
                key = (mode, src, dst)
                if tag == "PROJECT_CHOSEN":
                    ds = degree[mode]
                    cs, cd = ds[src], ds[dst]
                    chosen[key] = {
                        "prior_stage": current[mode],
                        "prior_src_degree": cs,
                        "prior_dst_degree": cd,
                        "prior_degree_sum": cs + cd,
                        "prior_degree_min": min(cs, cd),
                        "prior_degree_max": max(cs, cd),
                        "prior_degree_gap": abs(cs - cd),
                        "prior_pair_repeated": directed[mode][(src, dst)],
                        "prior_is_new_src": int(cs == 0),
                        "prior_is_new_dst": int(cd == 0),
                        "chose_year": int(match_line.group(1)),
                        "chose_month": int(match_line.group(2)),
                        "choice_rank": num(kv.get("rank")) or 0,
                    }
                elif tag == "RAIL_ATTEMPT":
                    if kv.get("ok") == "1":
                        attempts[key] = {
                            "post_route_length": num(kv.get("len")),
                            "post_actual_quote": num(kv.get("quote")),
                            "post_astar_iters": num(kv.get("iters")),
                            "attempt_model_capital": num(kv.get("model")),
                            "attempt_pre_capital": num(kv.get("pre")),
                            "attempt_pred_astar": num(kv.get("pred_astar")),
                        }
                else:
                    line = kv.get("line")
                    if line is None:
                        continue
                    qc["build_events"] += 1
                    feature = chosen.get(key)
                    if feature is None:
                        qc["no_prechoice_snapshot"] += 1
                        feature = {}
                    feature = dict(feature)
                    feature.update({
                        "post_engine": kv.get("engine", "unknown"),
                        "post_vehicles_initial": num(kv.get("planes") or kv.get("trains") or kv.get("vehicles")),
                        "post_wagons": num(kv.get("wagons")),
                        "plan_reuse": kv.get("reuse", "0"),
                        "plan_shared_dest": kv.get("shared_dest", "0"),
                        "plan_join_end": kv.get("join_end", "-"),
                        "air_arm": kv.get("arm", "none"),
                    })
                    if mode == "rail":
                        feature.update(attempts.get(key, {}))
                    result[(seed, mode, str(line))] = feature
                    # Historical count, not current active lines. Does not
                    # observe closures; excludes the current construction.
                    degree[mode][src] += 1
                    degree[mode][dst] += 1
                    directed[mode][(src, dst)] += 1
                    current[mode] += 1
        qc["games"] += 1
    return result, dict(qc)


def add_features(rows, folder):
    by_build, counts = features_per_build(folder)
    merged = []
    for row in rows:
        r = dict(row)
        extras = by_build.get((r["seed"], r["mode"], str(r["line"])), {})
        r.update(extras)
        merged.append(r)
    counts["joined_mature"] = sum("prior_stage" in r for r in merged)
    counts["unjoined_mature"] = sum("prior_stage" not in r for r in merged)
    return merged, counts


BASE = ("roi", "roi2", "capital", "roi_capital", "dist", "cargo",
        "year", "rank", "subtype", "reuse")

MODELS = {
    "roi_quadratic": ("roi", "roi2"),
    "base_existing": BASE,
    "plus_log_profit": BASE + ("log_profit",),
    "plus_year_month": BASE + ("chose_month",),
    "plus_stage": BASE + ("prior_stage",),
    "plus_src_degree": BASE + ("prior_src_degree",),
    "plus_dst_degree": BASE + ("prior_dst_degree",),
    "plus_endpoint_degree": BASE + ("prior_degree_sum", "prior_degree_gap"),
    "plus_prior_endpoint_novelty": BASE + ("prior_is_new_src", "prior_is_new_dst"),
    "plus_past_pair": BASE + ("prior_pair_repeated",),
    "plus_network": BASE + ("prior_stage", "prior_degree_sum",
                             "prior_degree_gap", "prior_is_new_src", "prior_is_new_dst"),
    "plus_plan_joining": BASE + ("plan_shared_dest", "plan_join_end"),
    "plus_engine_POST": BASE + ("post_engine",),
    "plus_fleet_POST": BASE + ("post_vehicles_initial", "post_wagons"),
    "plus_route_len_POST": BASE + ("post_route_length",),
    "plus_route_model_POST": BASE + ("attempt_model_capital", "attempt_pre_capital",
                                     "attempt_pred_astar"),
    "plus_geometry_POST": BASE + ("post_route_length", "post_astar_iters"),
    "all_prechoice": BASE + ("chose_month", "prior_stage",
                             "prior_src_degree", "prior_dst_degree",
                             "prior_degree_gap", "prior_is_new_src",
                             "prior_is_new_dst", "prior_pair_repeated"),
    "all_postdiagnostic": BASE + ("post_engine", "post_vehicles_initial", "post_wagons",
                                  "post_route_length", "attempt_pre_capital",
                                  "attempt_model_capital"),
}

CATEGORICAL = {"cargo", "subtype", "reuse", "post_engine", "plan_shared_dest",
               "plan_join_end"}


def values(r):
    roi = r["roi_pred"]
    capital = math.log(max(1., r["capital"]))
    return {
        "roi": roi, "roi2": roi ** 2, "capital": capital,
        "roi_capital": roi * capital, "dist": r["dist"],
        "year": r["year"] - 1970, "rank": min(r["rank"], 12),
        "log_profit": math.log(max(1., r["pred_profit"])),
        "chose_month": r.get("chose_month", 6),
        "prior_stage": math.log1p(r.get("prior_stage", 0)),
        "prior_src_degree": math.log1p(r.get("prior_src_degree", 0)),
        "prior_dst_degree": math.log1p(r.get("prior_dst_degree", 0)),
        "prior_degree_sum": math.log1p(r.get("prior_degree_sum", 0)),
        "prior_degree_gap": math.log1p(r.get("prior_degree_gap", 0)),
        "prior_is_new_src": r.get("prior_is_new_src", 1),
        "prior_is_new_dst": r.get("prior_is_new_dst", 1),
        "prior_pair_repeated": math.log1p(r.get("prior_pair_repeated", 0)),
        "post_vehicles_initial": r.get("post_vehicles_initial") or r.get("n0", 1),
        "post_wagons": r.get("post_wagons") or 0,
        "post_route_length": r.get("post_route_length") or r["dist"],
        "post_astar_iters": math.log1p(r.get("post_astar_iters") or 0),
        "attempt_pre_capital": math.log1p(r.get("attempt_pre_capital") or 0),
        "attempt_model_capital": math.log1p(r.get("attempt_model_capital") or 0),
        "attempt_pred_astar": math.log1p(r.get("attempt_pred_astar") or 0),
    }


def design(train, test, columns):
    rows = train + test
    n = len(train)
    numeric = [values(r) for r in rows]
    matrix = [np.ones(len(rows))]
    for key in columns:
        if key in CATEGORICAL:
            levels = Counter(str(r.get(key, "unknown")) for r in train)
            if len(levels) < 2:
                continue
            top = levels.most_common()[0][0]  # learn baseline from train only
            for level, freq in sorted(levels.items()):
                if freq < 12 or level == top:
                    continue
                vector = np.array([float(str(r.get(key, "unknown")) == level) for r in rows])
                sd = vector[:n].std()
                if sd > 1e-8:
                    matrix.append((vector-vector[:n].mean())/sd)
        else:
            vector = np.array([float(r[key]) for r in numeric])
            sd = vector[:n].std()
            if sd > 1e-8:
                matrix.append((vector-vector[:n].mean())/sd)
    return np.array(matrix).T


def fit(train, test, columns):
    x = design(train, test, columns)
    n = len(train)
    y = np.array([r["roi_real"] for r in train])
    ridge = np.eye(x.shape[1])*(.05*n)
    ridge[0,0] = 0.
    coef = np.linalg.solve(x[:n].T @ x[:n] + ridge, x[:n].T @ y)
    return x[n:] @ coef


def cross_validate(rows, source=None):
    res = {}
    for mode in sorted(set(r["mode"] for r in rows)):
        subset = [r for r in rows if r["mode"] == mode]
        if len(subset) < 20:
            continue
        training = [r for r in (source if source is not None else rows) if r["mode"] == mode]
        seeds = sorted(set(r["seed"] for r in subset))
        predictions = {name: {} for name in MODELS}
        for fold in range(5):
            holdout = set(seeds[fold::5])
            train = [r for r in training if r["seed"] not in holdout]
            test = [r for r in subset if r["seed"] in holdout]
            for name, columns in MODELS.items():
                estimated = fit(train, test, columns)
                for row, pred in zip(test, estimated):
                    predictions[name][(row["seed"], row["line"])] = float(pred)
        byseed = defaultdict(list)
        for r in subset:
            byseed[r["seed"]].append(r)
        scores = {}
        for name, preds in predictions.items():
            error = [abs(preds[(r["seed"], r["line"])]-r["roi_real"]) for r in subset]
            gains_per_seed = []
            rho = []
            for seed, group in sorted(byseed.items()):
                base_error = np.mean([abs(predictions["base_existing"][(r["seed"], r["line"])]-r["roi_real"]) for r in group])
                model_error = np.mean([abs(preds[(r["seed"], r["line"])]-r["roi_real"]) for r in group])
                gains_per_seed.append(base_error - model_error)
                if len(group) >= 4:
                    predicted = np.array([preds[(r["seed"], r["line"])] for r in group])
                    actual = np.array([r["roi_real"] for r in group])
                    if predicted.std() and actual.std():
                        # Simplified Spearman with unique rank via sorted order.
                        rho.append(float(np.corrcoef(np.argsort(np.argsort(predicted)),
                                                       np.argsort(np.argsort(actual)))[0,1]))
            rng = np.random.default_rng(20261021)
            arr = np.array(gains_per_seed)
            boots = rng.integers(0, len(arr), size=(2000,len(arr)))
            bounds = np.percentile(arr[boots].mean(axis=1), [2.5,97.5])
            scores[name] = {
                "n": len(subset),
                "mae_roi_points": round(float(np.mean(error)), 3),
                "median_abs_roi_points": round(float(np.median(error)), 3),
                "median_rank_rho": round(float(med(rho)),3) if rho else None,
                "gain_mae_per_seed_vs_baseline": round(float(np.mean(arr)),3),
                "gain_ci95": [round(float(v),3) for v in bounds],
                "seed_wins": int((arr>0).sum()),
                "seeds": len(seeds),
            }
        res[mode] = scores
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", action="append", required=True)
    ap.add_argument("--train", default="duel")
    ap.add_argument("--test", default="duel")
    ap.add_argument("--out-prefix", required=True)
    args = ap.parse_args()
    arms = {}
    stats = {}
    join_stats = {}
    for spec in args.campaign:
        arm, folder = spec.split("=", 1)
        original, stats[arm] = parse(folder, arm)
        arms[arm], join_stats[arm] = add_features(original, folder)
    if args.train not in arms or args.test not in arms:
        raise ValueError("train/test arm must be in --campaign")
    scores = cross_validate(arms[args.test],
                            None if args.train == args.test else arms[args.train])
    output = {"train": args.train, "test": args.test, "stats": stats,
              "join_stats": join_stats, "scores": scores}
    os.makedirs(os.path.dirname(args.out_prefix) or ".", exist_ok=True)
    with open(args.out_prefix+".json", "w", encoding="utf-8") as f:
        json.dump(output,f,indent=2,ensure_ascii=False)
    print("train", args.train, "test", args.test, "stats",stats, "network",join_stats)
    for mode, results in scores.items():
        print("\n",mode)
        for name, val in results.items():
            print(f"{name:26s} MAE {val['mae_roi_points']:8.3f} rank {val['median_rank_rho']}"
                  f" gain {val['gain_mae_per_seed_vs_baseline']:7.3f}"
                  f" CI {val['gain_ci95']} wins {val['seed_wins']}/{val['seeds']}")


if __name__ == "__main__":
    main()
