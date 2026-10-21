#!/usr/bin/env python3
"""Shadow RAIL capital/score recentering on frozen 40x10 SOLO -> DUEL logs.

No game code, map APIs, replay, or newly simulated investments.  The 5 folds
hold out disjoint DUEL seeds; each fold fits exclusively on other SOLO seeds.
"""

import argparse
import json
import os
from collections import Counter, defaultdict
from glob import glob

import numpy as np

from analyse_calibration_projets import KV_RE, LINE_RE, SEED_RE, open_text
from analyse_roi_predictors_20261021 import med, parse
from evaluer_bandes_roi_20261021 import assign, epoch_bounds, groups_for_distance


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def load_snapshots(directory):
    """Full *published* top-5 with rank_score already including the AIR bonus."""
    snapshots = []
    for path in sorted(glob(os.path.join(directory, "reference_seed*_r0.log"))):
        match = SEED_RE.search(os.path.basename(path))
        if match is None:
            continue
        seed = int(match.group(1))
        group = []
        date = None
        with open_text(path) as lines:
            for line in lines:
                m = LINE_RE.search(line)
                if m is None or m.group(4) != "PORTFOLIO_RANK":
                    continue
                kv = dict(KV_RE.findall(m.group(5)))
                try:
                    rank = int(kv["rank"])
                    mode = kv["mode"]
                    dist = float(kv["dist"])
                    score = float(kv["rank_score"])
                    finance = float(kv["finance_capital"])
                    cost = float(kv["cost"])
                    profit = float(kv["profit"])
                except (KeyError, ValueError):
                    continue
                if rank == 0 and group:
                    snapshots.append({"seed": seed, "date": date, "items": group})
                    group = []
                if mode not in ("air", "rail", "road", "fleet"):
                    continue
                date = "-".join(m.group(i) for i in (1, 2, 3))
                group.append({
                    "mode": mode, "family": "air" if mode in ("air", "fleet") else mode,
                    "distance": dist, "rank": rank, "score": score,
                    "cost": cost, "finance_capital": finance, "profit": profit,
                    "kind": kv.get("kind", ""), "cargo": kv.get("cargo", ""),
                    "src": kv.get("src", ""), "dst": kv.get("dst", ""),
                })
        if group:
            snapshots.append({"seed": seed, "date": date, "items": group})
    return snapshots


def fit_model(rows, scheme):
    rail = [r for r in rows if r["mode"] == "rail"]
    if len(rail) < 10:
        raise ValueError("Insufficient rail construction training lines")
    ratios = np.array([r["real_capital"] / r["capital"] for r in rail])
    distances = np.array([r["dist"] for r in rail])
    global_med = float(med(ratios.tolist()))
    model = {"global_median": global_med, "n_train": len(rail), "scheme": scheme}
    if scheme in ("linear", "pivot"):
        slope, intercept = np.polyfit(distances, ratios, 1)
        model.update({"slope": float(slope), "intercept": float(intercept)})
    elif scheme == "bands4":
        groups = defaultdict(list)
        for r in rail:
            groups[r["sub4_band"]].append(r["real_capital"] / r["capital"])
        # Two distinct shrinkage strengths: score requires conservative
        # relative weights; physical price error favors the published prior=20.
        model["group_cost"] = {
            key: (global_med * (60. / (len(values) + 60.))
                  + med(values) * (len(values) / (len(values) + 60.)))
            for key, values in groups.items()
        }
        model["group_cost_physical"] = {
            key: (global_med * (20. / (len(values) + 20.))
                  + med(values) * (len(values) / (len(values) + 20.)))
            for key, values in groups.items()
        }
    else:
        raise ValueError(scheme)
    return model


def cost_k(model, d, group, physical=False):
    if model["scheme"] in ("linear", "pivot"):
        return clamp(model["intercept"] + model["slope"] * d, .5, 2.5)
    lookup = "group_cost_physical" if physical else "group_cost"
    return model[lookup].get(group, model["global_median"])


def relative(model, d, group):
    """Relative allocation only: physical calibration's global bias omitted."""
    if model["scheme"] == "pivot":
        return 1.0 + model["pivot_slope"] * (model["pivot_distance"] - d)
    return clamp(model["global_median"] / cost_k(model, d, group), .75, 1.25)


def band_for(d, bounds):
    return groups_for_distance(d, bounds)[2]


def fit_fold(train, solo_snapshots, bounds, scheme):
    model = fit_model(train, scheme)
    weights = [p for s in solo_snapshots for p in s["items"]
               if p["family"] == "rail" and p["score"] > 0]
    if not weights:
        raise ValueError("No solo positive RAIL top-5 scores")
    base_mass = sum(p["score"] for p in weights)
    if scheme == "pivot":
        # Affine first-order approximation to inverse capital correction.
        # D_ref is computed once OFFLINE; its weighted mean gives exact
        # neutrality on training, with just a difference and multiplication.
        pivot = sum(p["score"] * p["distance"] for p in weights) / base_mass
        local_cost = model["intercept"] + model["slope"] * pivot
        model["pivot_distance"] = pivot
        model["pivot_slope"] = model["slope"] / local_cost
    norm = sum(p["score"] * relative(model, p["distance"], band_for(p["distance"], bounds))
               for p in weights) / base_mass
    if norm <= 0:
        raise ValueError("Invalid normalization")
    model["solo_weighted_norm"] = norm
    model["solo_rail_ranked_entries"] = len(weights)
    return model


def factor(item, model, bounds):
    if item["mode"] != "rail":
        return 1.0
    return relative(model, item["distance"], band_for(item["distance"], bounds)) / model["solo_weighted_norm"]


def compare_top5(snapshots, models, bounds):
    counts = Counter()
    per_seed = defaultdict(Counter)
    transitions = Counter()
    family = defaultdict(lambda: {"n": 0, "before": 0.0, "after": 0.0, "factors": []})
    distances = defaultdict(lambda: {"n": 0, "before": 0.0, "after": 0.0, "factors": []})
    physical_cost_hypothesis = {"rail_ranked": 0, "finance_equals_cost": 0,
                                "physical_model_over_logged_finance": 0,
                                "physical_model_under_logged_finance": 0}
    examples = []
    for s in snapshots:
        rows = s["items"]
        if not rows:
            continue
        m = models[s["seed"]]
        for p in rows:
            f = factor(p, m, bounds)
            p["new_score"] = p["score"] * f
            q = family[p["family"]]
            q["n"] += 1
            q["before"] += max(0, p["score"])
            q["after"] += max(0, p["new_score"])
            q["factors"].append(f)
            if p["mode"] == "rail":
                physical_cost_hypothesis["rail_ranked"] += 1
                if abs(p["finance_capital"] - p["cost"]) <= .01:
                    physical_cost_hypothesis["finance_equals_cost"] += 1
                expected_physical = p["cost"] * cost_k(m, p["distance"],
                                                       band_for(p["distance"], bounds), physical=True)
                if expected_physical > p["finance_capital"]:
                    physical_cost_hypothesis["physical_model_over_logged_finance"] += 1
                elif expected_physical < p["finance_capital"]:
                    physical_cost_hypothesis["physical_model_under_logged_finance"] += 1
                d = p["distance"]
                group = ("<=55" if d <= 55 else "56-103" if d <= 103 else
                         "104-151" if d <= 151 else "152-200" if d <= 200 else ">200")
                qd = distances[group]
                qd["n"] += 1
                qd["before"] += max(0, p["score"])
                qd["after"] += max(0, p["new_score"])
                qd["factors"].append(f)
        counts["snapshots"] += 1
        old_top = min(rows, key=lambda p: p["rank"])
        score_prev = max(rows, key=lambda p: p["score"])
        score_next = max(rows, key=lambda p: p["new_score"])
        new_top = score_next
        mixed = len(set(p["family"] for p in rows)) >= 2
        if mixed:
            counts["mixed_family_snapshots"] += 1
        if old_top is not score_prev:
            counts["historical_head_not_numeric_max"] += 1
            if old_top["mode"] == "air" and any(
                p["mode"] != "air" and p["score"] > old_top["score"] for p in rows
            ):
                counts["historic_air_head_exposes_tier_priority"] += 1
        if score_prev is not score_next:
            counts["numeric_max_changes"] += 1
            if mixed:
                counts["numeric_max_changes_mixed"] += 1
            transitions[score_prev["family"] + "->" + score_next["family"]] += 1
            per_seed[s["seed"]]["numeric_max_changes"] += 1
        if old_top is not new_top:
            counts["historic_head_vs_new_numeric_max"] += 1
        # Stronger evidence: historical non-AIR head has tier=0, so *all*
        # entries behind it have tier=0; compare exact logged, bonus-adjusted scores.
        if old_top["mode"] != "air":
            counts["head_confirmed_tier0_snapshots"] += 1
            if old_top is not score_prev:
                counts["nonair_head_inconsistent_with_numeric_sort"] += 1
            elif old_top is not score_next:
                counts["tier0_visible_head_inversions"] += 1
                if mixed:
                    counts["tier0_visible_head_inversions_mixed"] += 1
                per_seed[s["seed"]]["tier0_visible_head_inversions"] += 1
                if len(examples) < 12:
                    examples.append({
                        "seed": s["seed"], "date": s["date"],
                        "old": old_top["mode"], "new": score_next["mode"],
                        "old_distance": old_top["distance"], "new_distance": score_next["distance"],
                        "old_score": round(old_top["score"], 3),
                        "new_score_before": round(score_next["score"], 3),
                        "old_score_after": round(old_top["new_score"], 3),
                        "new_score_after": round(score_next["new_score"], 3),
                    })
        # Every non-AIR pair has known C77 tier 0, even if AIR heads this list.
        nonair = [p for p in rows if p["mode"] != "air"]
        for i, p in enumerate(nonair):
            for q in nonair[i + 1:]:
                if (p["score"] - q["score"]) * (p["new_score"] - q["new_score"]) < 0:
                    counts["nonair_tier0_pair_inversions"] += 1
                    if p["family"] != q["family"]:
                        counts["nonair_intermodal_pair_inversions"] += 1
                    per_seed[s["seed"]]["nonair_tier0_pair_inversions"] += 1
    def compact(x):
        return {"n": x["n"], "score_mass_before": round(x["before"], 2),
                "score_mass_after": round(x["after"], 2),
                "weighted_mean": round(x["after"] / x["before"], 6) if x["before"] else None,
                "median_factor": round(float(med(x["factors"])), 6),
                "range": [round(min(x["factors"]), 6), round(max(x["factors"]), 6)]}
    return {
        "counts": dict(counts), "numeric_transitions": dict(transitions),
        "mode_mass": {k: compact(v) for k, v in family.items()},
        "rail_distance_mass": {k: compact(v) for k, v in distances.items()},
        "seeds_with_numeric_changes": sum(c["numeric_max_changes"] > 0 for c in per_seed.values()),
        "seeds_with_tier0_inversions": sum(c["tier0_visible_head_inversions"] > 0 for c in per_seed.values()),
        "per_seed": {str(s): dict(c) for s, c in sorted(per_seed.items())},
        "physical_cost_hypothesis": physical_cost_hypothesis,
        "examples": examples,
    }


def run(solo_folder, duel_folder):
    sb, s_games = epoch_bounds(solo_folder)
    db, d_games = epoch_bounds(duel_folder)
    if len(sb + db) != 1:
        raise ValueError("Epoch bounds differ; need contemporaneous bound per snapshot")
    bounds = (sb + db).most_common(1)[0][0]
    solo, solo_stats = parse(solo_folder, "solo")
    duel, duel_stats = parse(duel_folder, "duel")
    assign(solo, bounds)
    assign(duel, bounds)
    solo_snap = load_snapshots(solo_folder)
    duel_snap = load_snapshots(duel_folder)
    seeds = sorted(s_games.keys() & d_games.keys())
    if len(seeds) != 40:
        raise ValueError("Expected 40 seed-matched SOLO/DUEL games, got %d" % len(seeds))
    results = {}
    fixed_offline = {}
    for scheme in ("pivot", "linear", "bands4"):
        full = fit_fold(solo, solo_snap, bounds, scheme)
        fixed_offline[scheme] = {
            "n_train": full["n_train"],
            "solo_score_mass_center": round(full["solo_weighted_norm"], 7),
            "intercept": full.get("intercept"), "slope": full.get("slope"),
            "pivot_distance": full.get("pivot_distance"),
            "pivot_slope": full.get("pivot_slope"),
            "multipliers_at_distances": {
                str(d): round(factor({"mode": "rail", "distance": d}, full, bounds), 6)
                for d in (30, 55, 100, 150, 200, 250)
            },
        }
        models = {}
        trained = []
        cost_errors = defaultdict(list)
        for fold in range(5):
            held = set(seeds[fold::5])
            train = [r for r in solo if r["seed"] not in held]
            snap_train = [s for s in solo_snap if s["seed"] not in held]
            model = fit_fold(train, snap_train, bounds, scheme)
            trained.append({"fold": fold, "test_seeds": len(held),
                            "n_train": model["n_train"],
                            "solo_ranked_rail_entries": model["solo_rail_ranked_entries"],
                            "training_center": round(model["solo_weighted_norm"], 6),
                            "pivot_distance": model.get("pivot_distance"),
                            "pivot_slope": model.get("pivot_slope"),
                            "slope": model.get("slope"),
                            "intercept": model.get("intercept")})
            for s in held:
                models[s] = model
            for r in duel:
                if r["seed"] not in held or r["mode"] != "rail":
                    continue
                actual = r["real_capital"]
                base = r["capital"]
                cost_errors["raw"].append(abs(base - actual))
                cost_errors["global"].append(abs(base * model["global_median"] - actual))
                cost_errors[scheme].append(abs(base * cost_k(
                    model, r["dist"], r["sub4_band"], physical=True) - actual))
        rank_effects = compare_top5(duel_snap, models, bounds)
        results[scheme] = {
            "fold_training": trained,
            "cost_mae_gbp": {key: round(float(np.mean(v)), 2) for key, v in cost_errors.items()},
            "cost_test_n": len(cost_errors[scheme]),
            "rank_effects": rank_effects,
        }
    # An ex-post DUEL centering is an arithmetic control only; future deployment
    # must use the SOLO-fitted normalizer or a fixed independent calibration.
    original_mass = results["pivot"]["rank_effects"]["mode_mass"]["rail"]["score_mass_before"]
    new_mass = results["pivot"]["rank_effects"]["mode_mass"]["rail"]["score_mass_after"]
    return {
        "bounds": list(bounds), "solo_games": len(s_games), "duel_games": len(d_games),
        "same_40_seeds_across_arms": True, "disjoint_heldout_seed_folds": True,
        "mature_rail_train_total": sum(r["mode"] == "rail" for r in solo),
        "mature_rail_duel_total": sum(r["mode"] == "rail" for r in duel),
        "snapshots_solo": len(solo_snap), "snapshots_duel": len(duel_snap),
        "reference": "score-only RAIL relative to physical-cost distance, SOLO centering; AIR/FLEET/ROAD=1",
        "fixed_offline_models_full_solo": fixed_offline,
        "pivot_duel_expost_rail_center_needed_for_exact_one": round(new_mass / original_mass, 7),
        "schemes": results,
        "warnings": [
            "Historical top-5 only, not the full admissible catalogue",
            "C77 priority of AIR entries is unlogged; strict tier-0 statements require original non-AIR head",
            "K_dec unlogged in top-5; no exact capex-before-K_dec rescoring or budget simulation",
            "Observed constructions are selected and lack counterfactual physical costs",
            "No opcode measurements and no economic A/B replay",
        ],
    }


def selftest():
    rows = [{"mode": "rail", "dist": d, "real_capital": c * (1.0 + d / 100),
             "capital": c, "sub4_band": "d" + str(d)}
            for d in (25, 50, 75, 100, 125, 150, 175, 200) for c in (1000, 2000)]
    model = fit_model(rows, "linear")
    assert abs(model["intercept"] - 1.0) < 1e-8
    assert abs(model["slope"] - .01) < 1e-8
    model["solo_weighted_norm"] = 1.0
    assert factor({"mode": "air"}, model, ()) == 1.0
    assert factor({"mode": "road"}, model, ()) == 1.0
    assert factor({"mode": "fleet"}, model, ()) == 1.0
    print("selftest ok")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--solo")
    p.add_argument("--duel")
    p.add_argument("--out")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        selftest()
        return
    if not all((a.solo, a.duel, a.out)):
        p.error("--solo, --duel and --out are required")
    result = run(a.solo, a.duel)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("evidence", a.out)
    for name, part in result["schemes"].items():
        print(name, "cost_mae", part["cost_mae_gbp"], "mass", part["rank_effects"]["mode_mass"],
              "counts", part["rank_effects"]["counts"])


if __name__ == "__main__":
    main()
