#!/usr/bin/env python3
"""Test de bandes de distance, cout rail, et score intermodal, sans OpenTTD."""
import argparse
import json
import math
import os
import re
import statistics
from collections import Counter, defaultdict
from glob import glob

import numpy as np

from analyse_calibration_projets import KV_RE, LINE_RE, SEED_RE, open_text
from analyse_roi_predictors_20261021 import parse, med
import analyse_roi_extra_predictors_20261021 as extra


def epoch_bounds(folder):
    allsets = Counter()
    per_seed = {}
    for path in sorted(glob(os.path.join(folder, "reference_seed*_r0.log"))):
        m = SEED_RE.search(os.path.basename(path))
        if not m:
            continue
        seed = int(m.group(1))
        vals = set()
        with open_text(path) as fh:
            for line in fh:
                found = LINE_RE.search(line)
                if not found or found.group(4) != "EPOCH_BOUNDS":
                    continue
                kv = dict(KV_RE.findall(found.group(5)))
                keys = ("roadMin", "roadMax", "roadGen", "railMin",
                        "railAir", "railMax", "airMin", "airMax")
                if not all(k in kv for k in keys):
                    continue
                item = tuple(int(kv[k]) for k in keys)
                vals.add(item)
                allsets[item] += 1
        per_seed[seed] = vals
    if not allsets:
        raise ValueError("Aucune borne EPOCH_BOUNDS capturee")
    return allsets, per_seed


def groups_for_distance(d, b):
    road_min, road_max, road_gen, rail_min, rail_air, rail_max, air_min, air_max = b
    if d < road_min:
        primary = "below_road"
    elif d <= road_max:
        primary = "road"
    elif d < rail_air:
        primary = "rail"
    elif d <= rail_max:
        primary = "air_rail"
    elif d <= air_max:
        primary = "air"
    else:
        primary = "long"
    # Extra seuils sans API : intervalle rail (roadMax..railAir) divise
    # en deux ou quatre ; air court indexe sur railMax +/- 1/8 du rail span.
    half = max(1, (road_max + rail_air) // 2)
    q1 = road_max + (rail_air-road_max)//4
    q2 = road_max + (rail_air-road_max)//2
    q3 = road_max + (3*(rail_air-road_max))//4
    offset = max(1, (rail_air-road_max)//8)
    if d < rail_air:
        semi = "below_%d" % half if d < half else "to_%d" % rail_air
        sub4 = "r1" if d<=q1 else ("r2" if d<=q2 else ("r3" if d<=q3 else "r4"))
    else:
        semi = "overlap" if d <= rail_max else "air"
        sub4 = ("a1" if d < rail_air+offset else
                ("a2" if d < rail_air+2*offset else
                 ("a3" if d < rail_air+3*offset else "a4")))
    return primary, primary+"_"+semi, primary+"_"+sub4, (
        {"rail_quarter_points": [q1,q2,q3],
         "air_offset": offset}
    )


def assign(rows, b, map_side=256):
    for row in rows:
        # AIR_BUILD.dist = flightDistance (OpexFlightDistance), while
        # OpexAirPairInBand tests Manhattan between TOWN CENTRES.
        # Recover centre-Manhattan on the known 256x256 bench without new APIs.
        d = row["dist"]
        if row["mode"] == "air" and row.get("src_tile") is not None and row.get("dst_tile") is not None:
            src, dst = int(row["src_tile"]), int(row["dst_tile"])
            d = abs(src % map_side - dst % map_side) + abs(src // map_side - dst // map_side)
        row["band_dist"] = d
        primary, half, fourth, _ = groups_for_distance(d,b)
        row["cascade_band"] = primary
        row["sub2_band"] = half
        row["sub4_band"] = fourth


def fit_models(solo, duel):
    b = {
        "roi_only": ("roi","roi2"),
        "simple": ("roi","roi2","cargo","subtype","capital"),
        "simple_plus_linear_distance": ("roi","roi2","cargo","subtype","capital","dist"),
        "simple_plus_cascade": ("roi","roi2","cargo","subtype","capital","cascade_band"),
        "simple_plus_sub2": ("roi","roi2","cargo","subtype","capital","sub2_band"),
        "simple_plus_sub4": ("roi","roi2","cargo","subtype","capital","sub4_band"),
        "base_existing": extra.BASE,
        "baseline_plus_cascade": extra.BASE+("cascade_band",),
        "baseline_plus_sub2": extra.BASE+("sub2_band",),
        "baseline_plus_sub4": extra.BASE+("sub4_band",),
    }
    original = dict(extra.MODELS)
    categories = set(extra.CATEGORICAL)
    try:
        extra.MODELS.clear()
        extra.MODELS.update(b)
        extra.CATEGORICAL.update({"cascade_band","sub2_band","sub4_band"})
        duel_fit = extra.cross_validate(duel)
        solo_test = extra.cross_validate(duel, source=solo)
    finally:
        extra.MODELS.clear()
        extra.MODELS.update(original)
        extra.CATEGORICAL.clear()
        extra.CATEGORICAL.update(categories)
    return {"duel_cv": duel_fit, "solo_to_duel": solo_test}


def cost_cv(solo, duel):
    """Prix RAIL evalues sur cout reel de chaque ligne mature."""
    out = {}
    for mode in ("rail","road"):
        tr = [r for r in solo if r["mode"]==mode]
        te = [r for r in duel if r["mode"]==mode]
        folds = sorted(set(r["seed"] for r in te))
        schemes = ["none","global","linear_distance","cargo","cascade_band",
                   "sub2_band","sub4_band","cargo_sub4"]
        errors = defaultdict(list)
        estimates = defaultdict(list)
        by_seed_errors = defaultdict(lambda: defaultdict(list))
        for k in range(5):
            held = set(folds[k::5])
            train = [r for r in tr if r["seed"] not in held]
            test = [r for r in te if r["seed"] in held]
            global_k = med([r["real_capital"]/r["capital"] for r in train])
            dx=np.array([r["dist"] for r in train])
            actual_k=np.array([r["real_capital"]/r["capital"] for r in train])
            linear_coef=np.polyfit(dx,actual_k,1) if len(train)>5 and dx.std()>1e-8 else [0.,global_k]
            for scheme in schemes:
                groups = defaultdict(list)
                for r in train:
                    key = (r["cargo"],r["sub4_band"]) if scheme=="cargo_sub4" else (
                        getattr_placeholder(r, scheme))
                    groups[key].append(r["real_capital"]/r["capital"])
                for r in test:
                    key = (r["cargo"],r["sub4_band"]) if scheme=="cargo_sub4" else (
                        getattr_placeholder(r, scheme))
                    values = groups.get(key, [])
                    if scheme=="none":
                        multiplier = 1.
                    elif scheme=="global":
                        multiplier = global_k
                    elif scheme=="linear_distance":
                        multiplier = max(.5,min(2.5,linear_coef[0]*r["dist"]+linear_coef[1]))
                    else:
                        # Shrink sparse groups toward global, no free rare buckets.
                        prior = 20. if scheme!="cargo_sub4" else 40.
                        weight = len(values)/(len(values)+prior)
                        multiplier = global_k*(1-weight) + (med(values) if values else global_k)*weight
                    pred = r["capital"]*multiplier
                    errors[scheme].append(abs(pred-r["real_capital"]))
                    estimates[scheme].append((pred,r["real_capital"]))
                    by_seed_errors[scheme][r["seed"]].append(abs(pred-r["real_capital"]))
        out[mode] = {}
        for scheme in schemes:
            pairs = estimates[scheme]
            common_seeds = sorted(set(by_seed_errors["global"]) & set(by_seed_errors[scheme]))
            improvements = np.array([
                np.mean(by_seed_errors["global"][seed]) -
                np.mean(by_seed_errors[scheme][seed])
                for seed in common_seeds
            ])
            rng=np.random.default_rng(20261021)
            draws=rng.integers(0,len(improvements),size=(2000,len(improvements)))
            low, high=np.percentile(improvements[draws].mean(axis=1),[2.5,97.5])
            out[mode][scheme] = {
                "n": len(pairs),
                "mae_cost_gbp": round(float(np.mean(errors[scheme])),1),
                "median_abs_cost_gbp": round(float(np.median(errors[scheme])),1),
                "median_abs_pct_actual": round(float(np.median([
                    100*abs(pred-real)/real for pred,real in pairs])),2),
                "per_seed_mean_mae_gain_vs_global_gbp":round(float(improvements.mean()),1),
                "per_seed_mean_gain_ci95_gbp":[round(float(low),1),round(float(high),1)],
                "seed_wins":int((improvements>0).sum()),
                "seeds":len(common_seeds),
            }
    return out


def getattr_placeholder(r, scheme):
    if scheme in ("none","global","linear_distance"): return "-"
    return r[scheme]


def factor_table(solo, scheme="sub4_band"):
    """Score-only shadow RAIL capital correction; AIR/ROAD kept exactly neutral."""
    modes = sorted(set(r["mode"] for r in solo))
    factors = {}
    for mode in modes:
        rows = [r for r in solo if r["mode"]==mode]
        if mode!="rail":
            factors[(mode,"__fallback__")] = 1.
            continue
        global_m = med([r["real_capital"]/r["capital"] for r in rows])
        groups = defaultdict(list)
        for r in rows:
            groups[r[scheme]].append(r["real_capital"]/r["capital"])
        for key, vals in groups.items():
            # Inverse of physical cost adjustment relative to the mode average.
            # Multipliers are SHADOW; relative adjustment capped +/-25%.
            w = len(vals)/(len(vals)+60.)
            center = w*med(vals) + (1.-w)*global_m
            rel = global_m/center if global_m and center>0 else 1.
            factors[(mode,key)] = max(.75,min(1.25,rel))
        factors[(mode,"__fallback__")] = 1.
    return factors


def linear_cost_params(solo):
    rows = [r for r in solo if r["mode"] == "rail"]
    d = np.array([r["dist"] for r in rows])
    ratios = np.array([r["real_capital"] / r["capital"] for r in rows])
    slope, intercept = np.polyfit(d, ratios, 1)
    return {
        "slope_per_tile": float(slope),
        "intercept": float(intercept),
        "global_median_cost_ratio": float(med(ratios.tolist())),
        "n_train": len(rows),
    }


def top5_counterfactual(folder, b, factors, linear_cost=None):
    """Score change in published top-5 snapshots only, NOT actual investments."""
    per_mode = defaultdict(list)
    snapshots = []
    count = Counter()
    for path in sorted(glob(os.path.join(folder, "reference_seed*_r0.log"))):
        entries = []
        with open_text(path) as fh:
            for line in fh:
                found=LINE_RE.search(line)
                if not found or found.group(4)!="PORTFOLIO_RANK":
                    continue
                kv = dict(KV_RE.findall(found.group(5)))
                try:
                    idx=int(kv["rank"])
                    mode=kv["mode"]
                    dist=float(kv["dist"])
                    score=float(kv["rank_score"])
                except (ValueError,KeyError):
                    continue
                if idx==0 and entries:
                    snapshots.append(entries)
                    entries=[]
                primary, semi, fourth,_=groups_for_distance(dist,b)
                group=fourth
                family="air" if mode=="fleet" else mode
                # Fleet: use common correction only (no made-up distance feature).
                raw=(factors.get((family,group),factors.get((family,"__fallback__"),1.))
                     if mode!="fleet" else 1.)
                uncentered_ratio = 1.
                if family=="rail" and linear_cost is not None:
                    predicted_cost=max(.5,min(2.5,
                        linear_cost["intercept"]+linear_cost["slope_per_tile"]*dist))
                    uncentered_ratio=1./predicted_cost
                    raw=max(.75,min(1.25,
                        linear_cost["global_median_cost_ratio"]/predicted_cost))
                item={"mode":mode,"family":family,"dist":dist,"score":score,
                      "raw":raw,"rank":idx,"group":group,
                      "uncentered_ratio":uncentered_ratio}
                entries.append(item)
                if family in ("air","rail","road"):
                    per_mode[family].append(item)
        if entries: snapshots.append(entries)
    # Normalize per mode by WEIGHTED contribution to published score mass.
    means={}
    for mode, rows in per_mode.items():
        denom=sum(max(0.,r["score"]) for r in rows)
        means[mode] = (sum(max(0.,r["score"])*r["raw"] for r in rows)/denom) if denom>0 else 1.
    for mode, rows in per_mode.items():
        for r in rows:
            r["factor"] = .8*r["raw"]/means[mode]
        total=sum(r["score"] for r in rows)
        count["score_"+mode] = len(rows)
    rank_flips=0
    mixed=0
    winner_changes=Counter()
    conditional_flip=0
    for rows in snapshots:
        valid=[r for r in rows if r["family"] in ("air","rail","road")]
        if len(valid)<2 or len(set(r["family"] for r in valid))<2:
            continue
        mixed+=1
        # Historic first list element is not necessarily best numeric score
        # because C77 priority tier outranks economics. Count only raw-score
        # inversions in this snapshot, labelled as potential.
        prev=max(valid,key=lambda r:r["score"])
        new=max(valid,key=lambda r:r["score"]*r.get("factor",.8))
        if prev is not new:
            rank_flips+=1
            winner_changes[(prev["family"],new["family"])]+=1
    coverage={}
    for mode,rows in per_mode.items():
        s=sum(max(0.,r["score"]) for r in rows)
        coverage[mode] = {
            "ranked_entries":len(rows),
            "weighted_mean_raw_factor":round(means[mode],5),
            "raw_cost_roi_factor_if_denominator_were_capital":round(
                sum(max(0.,r["score"])*r["uncentered_ratio"] for r in rows)/s,5),
            "weighted_mean_new_multiplier":round(
                sum(max(0.,r["score"])*r["factor"] for r in rows)/s,5),
            "median_multiplier":round(med([r["factor"] for r in rows]),5),
            "min_multiplier":round(min(r["factor"] for r in rows),5),
            "max_multiplier":round(max(r["factor"] for r in rows),5),
        }
    return {
        "score_mass_by_family": coverage,
        "snapshots":len(snapshots),
        "multi_family_snapshots":mixed,
        "potential_numeric_leader_changes":rank_flips,
        "transitions":{a+"->"+b:v for (a,b),v in winner_changes.items()},
        "limitations":"top5 logs only; C77 priority tiers, fleet exemptions and off-catalog candidates prevent claim of true selection flips; no economics run",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--solo",required=True)
    ap.add_argument("--duel",required=True)
    ap.add_argument("--out-prefix",required=True)
    a=ap.parse_args()
    solo_bounds,solo_games=epoch_bounds(a.solo)
    duel_bounds,duel_games=epoch_bounds(a.duel)
    all_bounds=solo_bounds+duel_bounds
    b=all_bounds.most_common(1)[0][0]
    if len(all_bounds)!=1:
        raise ValueError("Bornes variables : evaluer a l'instant de chaque choix !")
    solo,sc=parse(a.solo,"solo")
    duel,dc=parse(a.duel,"duel")
    assign(solo,b)
    assign(duel,b)
    cv=fit_models(solo,duel)
    cost=cost_cv(solo,duel)
    factor=factor_table(solo)
    scores=top5_counterfactual(a.duel,b,factor)
    linear=linear_cost_params(solo)
    scores_linear=top5_counterfactual(a.duel,b,factor,linear_cost=linear)
    counts={}
    for arm,rows in (("solo",solo),("duel",duel)):
        counts[arm]={}
        for mode in ("air","rail","road"):
            subset=[r for r in rows if r["mode"]==mode]
            counts[arm][mode]={
                "n":len(subset),
                "cascade":dict(Counter(r["cascade_band"] for r in subset)),
                "sub4":dict(Counter(r["sub4_band"] for r in subset)),
            }
    out={"bounds":dict(zip(("roadMin","roadMax","roadGen","railMin",
                            "railAir","railMax","airMin","airMax"),b)),
         "unique_bounds":len(all_bounds),
         "logged_bounds_events":sum(all_bounds.values()),
         "seen_games":len(solo_games)+len(duel_games),
         "subdivision":groups_for_distance(150,b)[-1],
         "counts":counts,"cv":cv,"cost":cost,"linear_cost_model":linear,
         "top5_shadow_discrete":scores,"top5_shadow_linear":scores_linear,
        "shadow_relative_cost_factor_train_by_band":{
             mode+"|"+group:round(x,5) for (mode,group),x in factor.items()},
         "qualification":"shadow only, no AI modifications, no measured opcode overhead"}
    os.makedirs(os.path.dirname(a.out_prefix) or ".",exist_ok=True)
    with open(a.out_prefix+".json","w",encoding="utf8") as f:
        json.dump(out,f,indent=2,ensure_ascii=False)
    for arm,counts in out["counts"].items():print(arm,counts)
    for key,result in cv.items():
        print("\n",key)
        for mode,models in result.items():
            for name,vals in models.items():
                if name=="base_existing" or name.startswith("baseline_plus") or name=="simple":
                    print(mode,name,"MAE",vals["mae_roi_points"],
                          "gain",vals["gain_mae_per_seed_vs_baseline"],"CI",vals["gain_ci95"])
    print("cost",cost)
    print("linear_cost",linear)
    print("score_shadow_discrete",scores)
    print("score_shadow_linear",scores_linear)


if __name__=="__main__":
    main()
