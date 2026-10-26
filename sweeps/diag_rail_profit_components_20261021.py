#!/usr/bin/env python3
"""RAIL-PROFIT-1: one mature RAIL line per seed, SOLO -> disjoint DUEL folds.

Read-only: no OpenTTD runs, no game-state modifications. Default report lives in
docs/diag_rail_profit_components_20261021.md. All financial amounts are GBP/year.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from glob import glob
import math
from pathlib import Path
import random
import re
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results/calibration_pc_20261021/results"
SOLO = DATA / "calib_solo_40x10_pc_20261021_engine"
DUEL = DATA / "calib_duel_40x10_pc_20261021_engine"
REPORT = ROOT / "docs/diag_rail_profit_components_20261021.md"
LOG = re.compile(r"\[0\] \[.\] OPEX (\d+)-(\d+)-(\d+) (\S+) (.*)$")
KV = re.compile(r"(\w+)=(\S+)")
SEED = re.compile(r"_seed(\d+)_r(\d+)\.log(?:\.gz)?$")
LINE_ID = re.compile(r"(?:0|[1-9][0-9]*)\Z")
CUTS = (90, 127, 172)
PRIOR = 50
MIN_CELL = 10


def number(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def quartile(value, cuts=CUTS):
    return 1 + sum(value > x for x in cuts)


def mean_or_none(values):
    return mean(values) if values else None


def average_rank(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.] * len(values)
    for start in range(len(order)):
        if start and values[order[start]] == values[order[start - 1]]:
            continue
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        for index in order[start:end]:
            ranks[index] = (start + end - 1) / 2.
    return ranks


def spearman(xs, ys):
    if len(xs) < 4:
        return None
    x, y = average_rank(xs), average_rank(ys)
    mx, my = mean(x), mean(y)
    xx = sum((a - mx)**2 for a in x)
    yy = sum((b - my)**2 for b in y)
    return sum((a-mx)*(b-my) for a, b in zip(x, y)) / math.sqrt(xx*yy) if xx*yy else None


def parse_game(lines, seed):
    """Chronological choice/build join; keep all mature LINE_REVENUE years by line."""
    selected = defaultdict(list)
    builds = {}
    years = defaultdict(dict)
    counts = Counter()
    sequence = 0
    for raw in lines:
        m = LOG.search(raw)
        if not m:
            continue
        tag = m.group(4)
        if tag not in ("PROJECT_CHOSEN", "RAIL_BUILD", "LINE_REVENUE"):
            continue
        kv = dict(KV.findall(m.group(5)))
        sequence += 1
        if tag == "PROJECT_CHOSEN" and kv.get("mode") == "rail":
            key = (kv.get("src"), kv.get("dst"))
            selected[key].append((sequence, kv))
            counts["choices"] += 1
        elif tag == "RAIL_BUILD":
            counts["builds"] += 1
            line = kv.get("line")
            if line is None:
                counts["build_missing_id"] += 1
                continue
            if LINE_ID.fullmatch(line) is None:
                counts["build_invalid_line_id"] += 1
                continue
            candidates = selected.get((kv.get("src"), kv.get("dst")), [])
            same = [x for _, x in candidates if x.get("cargo") == kv.get("cargo")]
            chosen = same[-1] if same else (candidates[-1][1] if candidates else None)
            if chosen is None:
                counts["build_no_choice"] += 1
            elif not same:
                counts["build_choice_cargo_mismatch"] += 1
            n0 = number(kv.get("trains"))
            builds[line] = {
                "seed": seed, "line": line, "cargo": kv.get("cargo", "?"),
                "kind": "PASS" if kv.get("cargo") == "PASS" else "FREIGHT",
                "distance": number(kv.get("dist")), "n0": n0,
                "cost_actual": number(kv.get("cost")),
                "cost_pred": number(chosen.get("cost")) if chosen else None,
                "chosen_profit": number(chosen.get("profit")) if chosen else None,
                "roi_chosen": number(chosen.get("roi")) if chosen else None,
                "matched_choice": bool(chosen), "year_build": int(m.group(1)),
                "wagons": number(kv.get("wagons")),
            }
        elif tag == "LINE_REVENUE" and kv.get("mode") == "rail":
            counts["line_revenue"] += 1
            age = number(kv.get("age"))
            if age is None or age < 2:
                counts["immature"] += 1
                continue
            line = kv.get("line")
            if line is None or LINE_ID.fullmatch(line) is None:
                counts["revenue_invalid_line_id"] += 1
                continue
            if line not in builds:
                counts["revenue_no_build"] += 1
                continue
            yr = number(kv.get("year"))
            vehs = number(kv.get("vehs"))
            if (yr is None or not yr.is_integer() or vehs is None or vehs <= 0
                    or not builds[line]["n0"] or builds[line]["n0"] <= 0):
                counts["revenue_bad_vehicle_or_year"] += 1
                continue
            keys = ("pred_rev", "real_rev", "pred_run", "real_run", "pred_prof", "real_prof")
            vals = {k: number(kv.get(k)) for k in keys}
            if any(x is None for x in vals.values()):
                counts["revenue_missing_component"] += 1
                continue
            scale = builds[line]["n0"] / vehs
            for k in ("real_rev", "real_run", "real_prof"):
                vals[k] *= scale
            vals["scale"] = scale
            vals["vehs"] = vehs
            vals["report_age"] = age
            pred_gap = vals["pred_rev"]-vals["pred_run"]-vals["pred_prof"]
            real_gap = vals["real_rev"]-vals["real_run"]-vals["real_prof"]
            if abs(pred_gap) > 1e-8:
                counts["predicted_gap_nonzero_years"] += 1
            if abs(real_gap) > 1e-8:
                counts["real_accounting_mismatch_years"] += 1
            counts["real_accounting_checked_years"] += 1
            years[line][int(yr)] = vals
            counts["mature_usable_line_years"] += 1
    rows = []
    for line, per_year in years.items():
        b = builds[line]
        sample = list(per_year.values())
        row = dict(b)
        for k in ("pred_rev", "real_rev", "pred_run", "real_run", "pred_prof", "real_prof"):
            row[k] = median([r[k] for r in sample])
        row["years"] = len(sample)
        row["amort_pred"] = row["pred_rev"] - row["pred_run"] - row["pred_prof"]
        row["pred_oper"] = row["pred_rev"]-row["pred_run"]
        row["real_oper"] = row["real_prof"]
        row["pred_net_proxy"] = row["pred_prof"]
        row["real_net_proxy"] = row["real_prof"]-row["amort_pred"]
        row["real_identity_residual"] = row["real_rev"] - row["real_run"] - row["real_prof"]
        row["pred_identity_residual"] = row["amort_pred"]
        row["profit_error"] = row["pred_prof"] - row["real_prof"]
        row["revenue_error"] = row["pred_rev"] - row["real_rev"]
        row["running_error"] = row["pred_run"] - row["real_run"]
        if b["cost_pred"] is not None and b["cost_pred"] > 0:
            row["roi_pred"] = 100 * row["pred_prof"] / b["cost_pred"]
        else:
            row["roi_pred"] = None
        if b["cost_actual"] is not None and b["cost_actual"] > 0:
            row["roi_real"] = 100 * row["real_prof"] / b["cost_actual"]
        else:
            row["roi_real"] = None
        rows.append(row)
    counts["mature_lines"] = len(rows)
    counts["build_no_mature"] = len(set(builds) - set(years))
    counts["mature_without_choice"] = sum(not r["matched_choice"] for r in rows)
    counts["mature_with_costs"] = sum(r["roi_pred"] is not None and r["roi_real"] is not None for r in rows)
    return rows, counts


def load_campaign(path):
    import gzip
    files = sorted([*glob(str(path / "*.log")), *glob(str(path / "*.log.gz"))])
    if not files:
        raise FileNotFoundError(f"No .log/.log.gz in {path}")
    rows, counts, seeds = [], Counter(), set()
    for f in files:
        m = SEED.search(Path(f).name)
        if not m:
            continue
        seed = int(m.group(1))
        if seed in seeds:
            raise ValueError(f"Repeated seed {seed} in {path}")
        seeds.add(seed)
        op = gzip.open if f.endswith(".gz") else open
        with op(f, "rt", encoding="utf-8", errors="replace") as fh:
            rs, ct = parse_game(fh, seed)
        rows.extend(rs)
        counts.update(ct)
    counts["games"] = len(seeds)
    return rows, counts, seeds


def fit(rows, predicted="pred_prof", actual="real_prof"):
    """Median realization ratio; negative realized profits stay in training."""
    train = [r for r in rows if r[predicted] > 0]
    if not train:
        raise ValueError("No positive predicted profit in training")
    ratios = lambda rr: [r[actual] / r[predicted] for r in rr]
    global_k = median(ratios(train))
    cargo = defaultdict(list)
    cargo_distance = defaultdict(list)
    cargo_roi = defaultdict(list)
    for r in train:
        cargo[r["cargo"]].append(r)
        cargo_distance[(r["cargo"], quartile(r["distance"]))].append(r)
        if r["roi_pred"] is not None:
            cargo_roi[(r["cargo"], quartile(r["roi_pred"], (35, 50, 70)))].append(r)

    def shrink(group, prior, threshold=MIN_CELL):
        if len(group) < threshold:
            return prior
        value = (len(group) * median(ratios(group)) + PRIOR * prior) / (len(group) + PRIOR)
        return min(4., max(.05, value))

    global_k = min(4., max(.05, global_k))
    cargo_k = {c: shrink(v, global_k) for c, v in cargo.items()}
    return {
        "global": global_k,
        "cargo": cargo_k,
        "cargo_distance": {key: shrink(v, cargo_k[key[0]]) for key, v in cargo_distance.items()},
        "cargo_roi": {key: shrink(v, cargo_k[key[0]]) for key, v in cargo_roi.items()},
        "train_lines": len(train),
    }


def factor(model, row, name, predicted="pred_prof"):
    if name == "raw" or row[predicted] <= 0:
        return 1.
    if name == "global":
        return model["global"]
    base = model["cargo"].get(row["cargo"], model["global"])
    if name == "cargo":
        return base
    if name == "cargo_distance":
        return model["cargo_distance"].get((row["cargo"], quartile(row["distance"])), base)
    if name == "cargo_roi" and row["roi_pred"] is not None:
        return model["cargo_roi"].get((row["cargo"], quartile(row["roi_pred"], (35, 50, 70))), base)
    return base


def fit_cost(rows):
    pairs = [(r["distance"], r["cost_actual"] / r["cost_pred"]) for r in rows
             if r["distance"] is not None and r["cost_pred"] is not None
             and r["cost_pred"] > 0 and r["cost_actual"] is not None and r["cost_actual"] > 0]
    if len(pairs) < 3:
        raise ValueError("Insufficient matched physical costs")
    xs, ys = zip(*pairs)
    mx, my = mean(xs), mean(ys)
    var = sum((x - mx)**2 for x in xs)
    b = sum((x-mx)*(y-my) for x, y in pairs) / var if var else 0.
    return my-b*mx, b, len(pairs)


def err_stats(rows, key="profit"):
    delta = [r["pred_"+key] - r["real_"+key] for r in rows]
    return {"n": len(rows), "mae": mean_or_none([abs(x) for x in delta]), "bias": mean_or_none(delta),
            "median_bias": median(delta) if delta else None}


def model_stats(rows, predictions, model_name):
    errors = [predictions[(r["seed"],r["line"],model_name)]-r["real_prof"] for r in rows]
    return {"n": len(errors), "mae": mean_or_none([abs(x) for x in errors]),
            "bias": mean_or_none(errors)}


def compare_targets(train, test, common, predicted, actual):
    """Evaluate profit predictors on an explicitly labeled comparable target."""
    methods = ("raw", "global", "cargo", "cargo_distance", "cargo_roi")
    errors = defaultdict(list)
    for fold in range(5):
        held = set(common[fold::5])
        model = fit([r for r in train if r["seed"] not in held], predicted, actual)
        for row in test:
            if row["seed"] not in held:
                continue
            for name in methods:
                e = row[predicted] * factor(model, row, name, predicted) - row[actual]
                errors[name].append((row["seed"], e))
    return {k: {"n":len(errors[k]),"mae":mean(abs(e) for _,e in errors[k]),
                "bias":mean(e for _,e in errors[k])} for k in methods}


def seed_bootstrap(rows, predictions, names, draws=5000):
    """CI of raw minus corrected MAE by independent seed clusters."""
    seed_errors=defaultdict(lambda: defaultdict(list))
    for row in rows:
        key=(row["seed"],row["line"])
        for name in names:
            seed_errors[row["seed"]][name].append(abs(predictions[(*key,name)]-row["real_prof"]))
    seeds=sorted(seed_errors)
    rng=random.Random(20261021)
    result={}
    for name in names:
        gains={s:mean(seed_errors[s]["raw"])-mean(seed_errors[s][name]) for s in seeds}
        samples=[mean(gains[seeds[rng.randrange(len(seeds))]] for _ in seeds) for _ in range(draws)]
        samples.sort()
        result[name]={"wins":sum(gains[s]>0 for s in seeds),"seeds":len(seeds),
                      "mean_per_seed_gain":mean(gains.values()),
                      "bootstrap_ci95":(samples[int(.025*draws)],samples[int(.975*draws)])}
    return result


def quartile_summary(rows, predictions, name, metric):
    usable = [r for r in rows if r["roi_real"] is not None and r["roi_pred"] is not None]
    usable.sort(key=lambda r: (r["roi_pred"] if metric == "pred" else r["roi_real"], r["seed"],r["line"]))
    out = []
    for q in range(4):
        group = usable[q*len(usable)//4:(q+1)*len(usable)//4]
        es = [predictions[(r["seed"], r["line"], name)] - r["real_prof"] for r in group]
        out.append({"n": len(group), "roi_pred": median([r["roi_pred"] for r in group]) if group else None,
                    "roi_real": median([r["roi_real"] for r in group]) if group else None,
                    "mae": mean_or_none([abs(x) for x in es]), "bias": mean_or_none(es)})
    return out


def run(solo, duel):
    train, s_count, s_seeds = load_campaign(solo)
    test, d_count, d_seeds = load_campaign(duel)
    common = sorted(s_seeds & d_seeds)
    if len(common) != 40 or s_seeds != d_seeds:
        raise ValueError(f"Expected 40 matched SOLO/DUEL seeds, got {len(common)}")
    names = ("raw", "global", "cargo", "cargo_distance", "cargo_roi")
    preds = {}
    costs = {}
    fold_info = []
    for fold in range(5):
        held = set(common[fold::5])
        tr = [r for r in train if r["seed"] not in held]
        te = [r for r in test if r["seed"] in held]
        model = fit(tr)
        a, b, cost_n = fit_cost(tr)
        fold_info.append({"fold": fold+1, "seeds": sorted(held), "train_lines":len(tr),
                          "test_lines":len(te), "cost_n": cost_n, "a":a, "b":b})
        for r in te:
            for name in names:
                preds[(r["seed"], r["line"], name)] = r["pred_prof"] * factor(model,r,name)
            costs[(r["seed"],r["line"])] = r["cost_pred"] * (a+b*r["distance"]) if r["cost_pred"] and r["distance"] is not None else None
    stats = {name: model_stats(test,preds,name) for name in names}
    comparable = {
        "operating":compare_targets(train,test,common,"pred_oper","real_oper"),
        "net_proxy":compare_targets(train,test,common,"pred_net_proxy","real_net_proxy")}
    bootstrap=seed_bootstrap(test,preds,names)
    by_cargo = {}
    for cargo in sorted({r["cargo"] for r in test}):
        subset = [r for r in test if r["cargo"] == cargo]
        by_cargo[cargo] = {k: model_stats(subset,preds,k) for k in names}
    by_distance = {}
    for q in range(1,5):
        subset = [r for r in test if quartile(r["distance"]) == q]
        by_distance[f"Q{q}"] = {k: model_stats(subset,preds,k) for k in names}
    roi = {}
    for name in names:
        joined = [r for r in test if r["roi_real"] is not None and r["roi_pred"] is not None
                  and costs[(r["seed"],r["line"])] is not None and costs[(r["seed"],r["line"])] > 0]
        ep, ec = [], []
        per_seed = defaultdict(list)
        for r in joined:
            pk = preds[(r["seed"],r["line"],name)]
            cp = r["cost_pred"]
            pc = costs[(r["seed"],r["line"])]
            if cp is None or cp <= 0:
                continue
            actual = r["roi_real"]
            rp = 100 * pk/cp
            rc = 100 * pk/pc
            ep.append(rp-actual)
            ec.append(rc-actual)
            per_seed[r["seed"]].append((rc,actual))
        rho = [spearman([x for x,y in values],[y for x,y in values]) for values in per_seed.values()]
        rho = [x for x in rho if x is not None]
        roi[name] = {"n":len(ec),"mae_raw_cost": mean_or_none([abs(x) for x in ep]),
                     "mae_cal_cost": mean_or_none([abs(x) for x in ec]),
                     "bias_cal_cost":mean_or_none(ec),"median_spearman":median(rho) if rho else None,
                     "rank_seeds":len(rho)}
    valid_id = [r for r in test if all(r[k] is not None for k in ("pred_rev","real_rev","pred_run","real_run","pred_prof","real_prof"))]
    decomposition = {k: err_stats(valid_id,k) for k in ("rev","run","prof")}
    abs_res = [abs(r["real_identity_residual"]) for r in valid_id]
    amort = [r["amort_pred"] for r in valid_id]
    group_descriptions = {}
    for group, sub in (("PASS",[r for r in test if r["cargo"]=="PASS"]),
                       ("FREIGHT",[r for r in test if r["cargo"]!="PASS"])):
        group_descriptions[group] = {k:err_stats(sub,k) for k in ("rev","run","prof")}
    identity = {"n":len(valid_id), "real_residual_max_abs":max(abs_res) if abs_res else None,
                "predicted_residual_median":median(amort) if amort else None,
                "predicted_residual_negative":sum(x<0 for x in amort),
                "predicted_residual_zero":sum(x==0 for x in amort),
                "normalized_profit_error_decomposition_means":{
                    "profit_bias":decomposition["prof"]["bias"],
                    "rev_minus_run_minus_pred_amort":decomposition["rev"]["bias"]-decomposition["run"]["bias"]-mean(amort)
                }}
    return {"solo":train, "duel":test, "solo_counts":s_count, "duel_counts":d_count,
            "folds":fold_info,"models":stats,"comparable":comparable,"bootstrap":bootstrap,
            "by_cargo":by_cargo,"by_distance":by_distance,
            "roi":roi,"by_roi_pred":{k:quartile_summary(test,preds,k,"pred") for k in names},
            "by_roi_real":{k:quartile_summary(test,preds,k,"real") for k in names},
            "identity":identity,"components":decomposition,"pass_freight":group_descriptions}


def fmt(value, decimals=0):
    return "—" if value is None else f"{value:,.{decimals}f}".replace(",", " ")


def md_table(headers, items):
    return "| " + " | ".join(headers) + " |\n|" + "|".join("---" for _ in headers) + "|\n" + "\n".join("| " + " | ".join(str(c) for c in row) + " |" for row in items) + "\n"


def markdown(out):
    raw, solo, duel = out["models"]["raw"],out["solo_counts"],out["duel_counts"]
    doc = ["# RAIL-PROFIT-1 — composantes du profit des lignes ferroviaires", "",
           "21 octobre 2026. Diagnostic **hors ligne** des 40 parties SOLO et des 40 DUEL de dix ans, à partir des journaux du PC. "
           "Exécuter `python -X utf8 sweeps/diag_rail_profit_components_20261021.py` pour régénérer ce rapport et "
           "`python -X utf8 -m unittest sweeps/test_rail_profit_components_20261021.py` pour les tests synthétiques.", "",
           "## Verdict pour RAIL-CAL-1 prompt 4", "",
           "La table multiplicative cargo × distance précédente, ajustée sur des **lignes-années**, détériorait déjà le profit "
           "DUEL : MAE 13 245 → 14 094 £/an ; biais +1 884 → +7 912 £/an "
           "(`docs/calibration_rail_jointe_20261021.md`, §Contre-vérification). Les modèles ci-dessous évaluent "
           "**chaque ligne mature une seule fois**, avec la médiane des années pleines et le test sur graines exclues de SOLO.", ""]
    doc += [md_table(["Modèle", "N lignes DUEL", "MAE profit £/an", "Biais prédit−réel £/an", "Δ MAE vs brut £/an"],
                     [(name, x["n"],fmt(x["mae"]),fmt(x["bias"]),fmt(x["mae"]-raw["mae"]))
                      for name,x in out["models"].items()]), ""]
    best = min(out["models"],key=lambda n:out["models"][n]["mae"])
    doc += [f"**Meilleur MAE sur DUEL : {best}**, gain = {fmt(raw['mae']-out['models'][best]['mae'])} £/an par ligne "
            "(descriptif hors graines, conditionné aux lignes historiquement construites). "
            + ("Aucun correcteur de profit évalué ne réduit la MAE : **pas qualifié** pour le prompt 4."
               if best=="raw" else "Réduction observée à interpréter avec les biais, le classement et la robustesse ci-dessous avant activation."), "",
            md_table(["Correction", "Graines avec gain / 40", "Gain MAE moyen par graine £", "IC95 bootstrap du gain £"],
                     [(name,f"{x['wins']}/{x['seeds']}",fmt(x['mean_per_seed_gain']),
                       f"[{fmt(x['bootstrap_ci95'][0])} ; {fmt(x['bootstrap_ci95'][1])}]")
                      for name,x in out['bootstrap'].items() if name!='raw']), ""]
    doc += ["## Comparaison comptablement homogène (les mêmes plis)", "",
            "Deux cibles supplémentaires évitent de comparer directement le profit prévu net d'amortissement "
            "au profit de véhicules mesuré sans amortissement explicite : **exploitation** : "
            "`pred_rev − pred_run` versus `real_prof = real_rev − real_run` ; **net proxy** : "
            "`pred_prof` versus `real_prof − amort_pred`. Le second est une **hypothèse de "
            "dépréciation identique au budget théorique**, pas une mesure du net réalisé.", ""]
    for label in ("operating","net_proxy"):
        doc += [f"**{label}**", "",
                md_table(["Modèle", "N lignes", "MAE homogène £/an", "Biais £/an", "Δ MAE vs brut £"],
                         [(name,x['n'],fmt(x['mae']),fmt(x['bias']),
                           fmt(x['mae']-out['comparable'][label]['raw']['mae']))
                          for name,x in out['comparable'][label].items()]), ""]
    doc += ["## Couverture, appariements et sélection", "",
            md_table(["Observation", "SOLO", "DUEL"],[(n,solo[n],duel[n]) for n in
            ("games","choices","builds","build_no_choice","build_choice_cargo_mismatch","build_no_mature",
             "mature_lines","mature_without_choice","mature_usable_line_years","revenue_no_build",
             "revenue_bad_vehicle_or_year","revenue_missing_component","mature_with_costs",
             "real_accounting_checked_years","real_accounting_mismatch_years","predicted_gap_nonzero_years")]), "",
            "Appariement chronologique : dernier `PROJECT_CHOSEN` de même paire (src,dst) et cargo antérieur "
            "à `RAIL_BUILD`, puis `line` vers `LINE_REVENUE` (compagnie 0 seulement). Si le cargo diffère, le "
            "cas est identifié ; les projets abandonnés ne fournissent aucun profit contrefactuel. Un rapport "
            "décalé après la construction ou une ligne détruite avant deux ans créent un biais de survie. "
            "Les lignes choisies ne constituent pas un échantillon aléatoire du portefeuille.", ""]
    idn=out["identity"]
    doc += ["## Comptabilité et attribution (DUEL, une ligne mature)", "",
            "Le code `task_report.nut:247-262,431-435,523` calcule `real_prof` avec "
            "`AIVehicle.GetProfitLastYear`, mais `real_run` est la **somme des coûts de fonctionnement "
            "courants** `GetRunningCost`, et `real_rev` est **construit** comme `real_prof + real_run`. "
            "Ce revenu n'est donc **pas un poste de recettes observé indépendamment pour l'année passée**. "
            "Le code `economy.nut:395-397,455-463` prédit `pred_prof = pred_rev − pred_run − amortAnnual`. "
            "L'amortissement réel n'est pas enregistré et ne peut pas être déduit par différence. "
            "L'égalité réalisée est une identité de construction, pas une vérification indépendante du moteur.", "",
            f"Contrôle : résidu réalisé **exactement nul pour chacune des {duel['real_accounting_checked_years']} "
            f"lignes-années DUEL** (`real_accounting_mismatch_years=0`). La prise de médianes "
            f"séparées par ligne peut casser cette identité (résidu maximal "
            f"{fmt(idn['real_residual_max_abs'],2)} £/an sur les seules médianes). "
            f"Résidu prédit `pred_rev−pred_run−pred_prof` "
            f"médian **{fmt(idn['predicted_residual_median'])} £/an** (négatifs : "
            f"{idn['predicted_residual_negative']}, nuls : {idn['predicted_residual_zero']}). "
            "Ce dernier est un **amortissement prévu**, sans observation correspondante au réel.", "",
            md_table(["Grandeur", "N lignes", "MAE £/an", "Biais prédit−réel £/an"],
                     [(key,out['components'][key]['n'],fmt(out['components'][key]['mae']),
                       fmt(out['components'][key]['bias'])) for key in ('rev','run','prof')]), "",
            "Décomposition algébrique des **moyennes** (en £/an, médianes annuelles par ligne) : "
            f"biais profit = {fmt(idn['normalized_profit_error_decomposition_means']['profit_bias'],2)} ; "
            f"biais revenu − biais fonctionnement − amortissement prévu = "
            f"{fmt(idn['normalized_profit_error_decomposition_means']['rev_minus_run_minus_pred_amort'],2)}. "
            "Les médianes prises séparément peuvent briser légèrement l'identité quand les différentes "
            "composantes varient d'une année à l'autre. Les biais de revenu/charges ne constituent donc "
            "**pas une attribution causale** du profit.", ""]
    doc += [md_table(["Type", "MAE revenu", "Biais revenu", "MAE courant", "Biais courant", "MAE profit", "Biais profit"],
                     [(kind,*[fmt(x) for comp in ('rev','run','prof') for x in
                            (s[comp]['mae'],s[comp]['bias'])]) for kind,s in out['pass_freight'].items()]), ""]
    doc += ["## Erreur de profit par cargo et par distance (DUEL)", "",
            md_table(["Cargo", "N", "Brut MAE", "Global MAE", "Cargo MAE", "Cargo×distance MAE", "Cargo×ROI MAE"],
                     [(c,v['raw']['n'],*[fmt(v[n]['mae']) for n in out['models']]) for c,v in out['by_cargo'].items()]), "",
            md_table(["Bande tuiles", "N", "Brut MAE", "Cargo MAE", "Cargo×distance MAE"],
                     [(q,v['raw']['n'],fmt(v['raw']['mae']),fmt(v['cargo']['mae']),fmt(v['cargo_distance']['mae']))
                      for q,v in out['by_distance'].items()]), "",
            "Les bornes de distance sont fixées avant mesure : ≤90, 91–127, 128–172, ≥173. "
            "Les facteurs sont médians sur **une ligne** et rétrécis vers le cargo (poids 50, "
            "minimum 10 lignes), puis limités à [0,05 ; 4]. Le signal supplémentaire testé est "
            "le quartile de ROI prédit (≤35, ≤50, ≤70, >70 %) ; aucun champ de revenu réalisé "
            "n'entre dans les prédicteurs. Un `pred_prof` nul ou négatif reste inchangé ; profit "
            "réalisé négatif conservé dans entraînement, MAE et biais.", ""]
    for kind,title in (("by_roi_pred","ROI **prédit**"),("by_roi_real","ROI **réalisé**")):
        doc += ["## Quartiles selon " + title, "",
                md_table(["Quartile","N", "ROI prévu médian %", "ROI réalisé médian %", "MAE profit brut £", "MAE meilleur £", "Biais meilleur £"],
                         [(f"Q{i+1}",x['n'],fmt(x['roi_pred'],1),fmt(x['roi_real'],1),
                           fmt(out[kind]['raw'][i]['mae']),fmt(x['mae']),fmt(x['bias']))
                          for i,x in enumerate(out[kind][best])]), "",
                "Ces quartiles sont recalculés sur les mêmes lignes DUEL à coût physique positif ; "
                "quartiler sur le réalisé sélectionne mécaniquement les extrêmes et amplifie la "
                "régression vers la moyenne.", ""]
    doc += ["## ROI financier : devis et profit sont des modèles distincts", "",
            "Coût : OLS `(coût final RAIL_BUILD / devis PROJECT_CHOSEN) ~ a+b·distance` appris "
            "**sur constructions SOLO des quatre autres plis**, utilisé sur les lignes DUEL appariées ; "
            "si aucun devis n'est apparié, la ligne reste dans les métriques de profit mais sort du ROI.", "",
            md_table(["Profit", "N ROI", "MAE ROI / devis brut (points)", "MAE ROI / devis recalé", "Biais ROI recalé", "Spearman médian / graine"],
                     [(name,v['n'],fmt(v['mae_raw_cost'],2),fmt(v['mae_cal_cost'],2),fmt(v['bias_cal_cost'],2),
                       fmt(v['median_spearman'],3)) for name,v in out['roi'].items()]), "",
            "La correction de capital ne peut justifier, à elle seule, le correcteur de **profit** : "
            "comparer séparément ses MAE et biais à ceux du coût seul (ligne `raw` sur devis recalé). "
            "Spearman est calculé au sein de chaque graine avec rangs moyens en cas d'égalité, "
            "puis médiané sur les 40 graines. Les cinq plis DUEL de huit graines n'ont "
            "aucune graine d'entraînement SOLO commune.", "",
            "## Signal à mesurer ensuite (hypothèses, pas des résultats)", "",
            "D'abord instrumenter sous `decision_log` déjà existant, à une cadence limitée "
            "(un événement par construction puis un bilan annuel), la **demande captable au choix**, "
            "la production industrielle, `predCarried`, la capacité et les trains/wagons envisagés, "
            "les temps aller-retour et les notes de gare prévues. S'ils sont déjà présents dans "
            "l'objet candidat, leur lecture et concaténation coûtent O(1) par projet dans la "
            "branche de diagnostic ; ne pas faire d'appel API pour recalculer. Mesurer ensuite "
            "au bilan la charge/capacité, la production transportée, la note des gares et la "
            "présence concurrente : données dynamiques qui **ne sont pas connues au choix** ; "
            "O(1) appels par ligne et par an, jamais par candidat. Proscrire scans de carte, "
            "recherche de trajet ou listes de véhicules par candidat. Les opcodes exacts "
            "restent à profiler avant toute activation.", "",
            "**Limites** : seules les lignes survivantes jusqu'à âge ≥2 ont un profit mesuré ; "
            "médianes de 2 à 8 années pleines ; variation du nombre de trains normalisée par `n0/vehs` "
            "(approximation linéaire, pas reconstruction contrefactuelle de la flotte de départ). "
            "Une première/deuxième campagne SOLO et DUEL sur la même graine ne constitue pas "
            "une répétition indépendante. `GetRunningCost` est une charge annualisée courante, "
            "pas une comptabilité annuelle, et `real_rev` est calculée par solde. "
            "La notation `roi` dans PROJECT_CHOSEN est en millièmes ; ici ROI annualisé est "
            "`100·profit/capital`, avec deux versions de capital. Pas de preuve directe "
            "d'amortissement historique réel ni de causalité de l'effet du concurrent.", "",
            "## Reproductibilité : plis et tailles", "",
            md_table(["Pli", "Graines DUEL tenues à l'écart", "Lignes entraînement SOLO", "Lignes test DUEL", "Constructions coût entraînement"],
                     [(f['fold'], ", ".join(map(str,f['seeds'])),f['train_lines'],f['test_lines'],f['cost_n'])
                      for f in out['folds']])]
    return "\n".join(doc) + "\n"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solo",type=Path,default=SOLO)
    parser.add_argument("--duel",type=Path,default=DUEL)
    parser.add_argument("--out",type=Path,default=REPORT)
    args=parser.parse_args()
    result=run(args.solo,args.duel)
    args.out.write_text(markdown(result),encoding="utf-8")
    for name,v in result['models'].items():
        print(f"{name}: n={v['n']}, MAE={v['mae']:.1f}, biais={v['bias']:.1f} GBP/year")
    print('report:',args.out)


if __name__=='__main__':
    main()
