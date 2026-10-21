#!/usr/bin/env python3
"""Offline RAIL profit corrections; SOLO training, disjoint-seed DUEL validation.

Exploratory comparison only: a winning DUEL correction still needs an independent
evaluation before policy adoption. Never reads a DUEL target during fitting.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import random
from statistics import mean, median

import diag_rail_profit_components_20261021 as diag

REPORT = Path(__file__).resolve().parents[1] / "docs/rail_cal_profit_safe_20261021.md"
NAMES = (
    "raw", "global_10", "global_25", "weighted_10", "weighted_25",
    "dist_10", "dist_25", "cargo_dist_10", "roi_10", "add_10",
    "add_dist_10", "add_dist_factor10", "affine_10", "solo_inner_select",
)


def safe_ratio(rows, weight=False):
    """Training-only L1 multiplicative fit; negative actual returns remain valid."""
    pairs = sorted((r["real_prof"] / r["pred_prof"],
                    r["pred_prof"] if weight else 1)
                   for r in rows if r["pred_prof"] > 0)
    if not pairs:
        return 1.0
    threshold = sum(w for _, w in pairs) / 2
    acc = 0
    for ratio, weight_ in pairs:
        acc += weight_
        if acc >= threshold:
            return max(0.25, min(2.0, ratio))
    return 1.0


def med_residual(rows):
    return median([r["real_prof"] - r["pred_prof"] for r in rows]) if rows else 0


def fit(rows):
    """All coefficients fitted exclusively on SOLO, never on DUEL."""
    bydist, bycargo, byroi, byboth = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for r in rows:
        dist = diag.quartile(r["distance"])
        roi = diag.quartile(r["roi_pred"], (35, 50, 70)) if r["roi_pred"] is not None else 0
        bydist[dist].append(r)
        bycargo[r["cargo"]].append(r)
        byboth[(r["cargo"], dist)].append(r)
        byroi[roi].append(r)
    common = safe_ratio(rows)
    common_w = safe_ratio(rows, True)
    per_cargo = {key: (len(v) * safe_ratio(v) + 50 * common) / (len(v) + 50)
                 for key, v in bycargo.items()}
    dist = {key: (len(v) * safe_ratio(v) + 50 * common) / (len(v) + 50)
            for key, v in bydist.items()}
    both = {key: (len(v) * safe_ratio(v) + 50 * dist[key[1]]) / (len(v) + 50)
            for key, v in byboth.items()}
    roi = {key: (len(v) * safe_ratio(v) + 50 * common) / (len(v) + 50)
           for key, v in byroi.items()}
    global_add = med_residual(rows)
    dist_add = {key: (len(v) * med_residual(v) + 50 * global_add) / (len(v) + 50)
                for key, v in bydist.items()}
    xx = sum(r["pred_prof"]**2 for r in rows)
    xy = sum(r["pred_prof"]*r["real_prof"] for r in rows)
    b = max(0.5, min(1.5, xy / xx)) if xx else 1.0
    intercept = max(-20000, min(20000, median([r["real_prof"] - b*r["pred_prof"] for r in rows])))
    return {"global":common, "weighted":common_w, "dist":dist, "cargo_dist":both,
            "roi":roi, "add":global_add, "add_dist":dist_add, "affine":(intercept,b),
            "cargo":per_cargo}


def predict(model, row, name):
    p = row["pred_prof"]
    if name == "raw" or p <= 0:
        return p
    dist = diag.quartile(row["distance"])
    if name == "add_10":
        return p + .10 * max(-20000,min(20000,model["add"]))
    if name in ("add_dist_10", "add_dist_factor10"):
        offset = .10 * max(-20000,min(20000,model["add_dist"].get(dist,model["add"])))
        if name == "add_dist_factor10":
            # Exactly a profit factor k = 1 + offset / p, k in [0.9, 1.1].
            # This is computable from the already evaluated candidate's profit.
            offset=max(-.10*p,min(.10*p,offset))
        return p + offset
    if name == "affine_10":
        a,b = model["affine"]
        return p + .10 * (a + (b-1) * p)
    roi = diag.quartile(row["roi_pred"], (35,50,70)) if row["roi_pred"] is not None else 0
    ratios = {"global_10": (model["global"],.10),
              "global_25": (model["global"],.25),
              "weighted_10": (model["weighted"],.10),
              "weighted_25": (model["weighted"],.25),
              "dist_10": (model["dist"].get(dist, model["global"]),.10),
              "dist_25": (model["dist"].get(dist, model["global"]),.25),
              "cargo_dist_10": (model["cargo_dist"].get((row["cargo"],dist), model["dist"].get(dist,model["global"])),.10),
              "roi_10": (model["roi"].get(roi,model["global"]),.10)}
    if name in ratios:
        ratio, shrink = ratios[name]
        return p * (1 + shrink * (ratio - 1))
    raise ValueError(name)


def inner_choose(solo, held):
    """Choose a single correction on remaining SOLO via 4 disjoint inner folds."""
    names = ("raw", "global_10", "global_25", "weighted_10", "weighted_25", "dist_10", "dist_25", "add_10", "add_dist_10", "affine_10")
    seeds = sorted({r["seed"] for r in solo if r["seed"] not in held})
    assert len(seeds) == 32
    scores = {name:[] for name in names}
    for j in range(4):
        valid = set(seeds[j::4])
        model = fit([r for r in solo if r["seed"] not in valid and r["seed"] not in held])
        for r in solo:
            if r["seed"] in valid:
                for name in names:
                    scores[name].append(abs(predict(model,r,name)-r["real_prof"]))
    result = min(names, key=lambda name: (mean(scores[name]), names.index(name)))
    return result, {name:mean(es) for name,es in scores.items()}


def bootstrap(seed_errs, name, n=4000):
    seeds = sorted(seed_errs["raw"])
    gains = {seed:mean(abs(x) for x in seed_errs["raw"][seed])-mean(abs(x) for x in seed_errs[name][seed]) for seed in seeds}
    rng = random.Random(20261021)
    samples = sorted(mean(gains[seeds[rng.randrange(len(seeds))]] for _ in seeds) for _ in range(n))
    return (sum(g>0 for g in gains.values()),mean(gains.values()),samples[int(.025*n)],samples[int(.975*n)])


def run():
    solo,cs,ss=diag.load_campaign(diag.SOLO)
    duel,cd,ds=diag.load_campaign(diag.DUEL)
    seeds=sorted(ss & ds)
    if len(seeds)!=40 or ss != ds:
        raise AssertionError("Require exactly 40 identical SOLO and DUEL seeds")
    outer=[]
    errs={name:defaultdict(list) for name in NAMES}
    saved_pred={name:{} for name in NAMES}
    for fold in range(5):
        held = set(seeds[fold::5])
        train=[r for r in solo if r["seed"] not in held]
        valid=[r for r in duel if r["seed"] in held]
        assert len({r["seed"] for r in train} & held) == 0
        choice,inner=inner_choose(solo,held)
        model=fit(train)
        fold_meta=(fold+1,len(train),len(valid),choice,inner["raw"],inner[choice])
        for r in valid:
            for name in NAMES:
                p = predict(model,r,choice if name=="solo_inner_select" else name)
                saved_pred[name][(r["seed"],r["line"])]=p
                errs[name][r["seed"]].append(p-r["real_prof"])
        fold_gain={name:mean(abs(r["pred_prof"]-r["real_prof"])-
                   abs(saved_pred[name][(r["seed"],r["line"])]-r["real_prof"]) for r in valid)
                   for name in ("dist_10","cargo_dist_10","add_dist_10","add_dist_factor10","solo_inner_select")}
        outer.append((*fold_meta,fold_gain,[model["dist"].get(q,model["global"]) for q in range(1,5)],
                      [model["add_dist"].get(q,model["add"]) for q in range(1,5)]))
    stats={}
    for name in NAMES:
        all_errors=[e for seed_errors in errs[name].values() for e in seed_errors]
        wins,gain,lo,hi=bootstrap(errs,name)
        rank=[]
        for seed in seeds:
            sr=[r for r in duel if r["seed"]==seed]
            if len(sr)>=4:
                rho=diag.spearman([saved_pred[name][(r["seed"],r["line"])] for r in sr],
                                  [r["real_prof"] for r in sr])
                if rho is not None: rank.append(rho)
        stats[name]=(mean(abs(e) for e in all_errors),mean(all_errors),wins,gain,lo,hi,median(rank))
    return solo,duel,outer,stats


def fmt(x):
    return f"{x:,.0f}".replace(","," ")


def markdown(solo,duel,outer,stats):
    ss=mean(r["pred_prof"]-r["real_prof"] for r in solo)
    dd=mean(r["pred_prof"]-r["real_prof"] for r in duel)
    out=["# RAIL-CAL-1 — essai prudent de correction du profit (21 octobre 2026)","",
         "Exploration **hors ligne** : 40 jeux SOLO (1039 lignes matures) pour ajuster ; 40 jeux DUEL (1032 lignes matures) pour évaluer, un échantillon par ligne (médiane des années âge ≥2). Tous les coefficients s'apprennent exclusivement sur 32 graines SOLO par pli, les 8 graines DUEL correspondantes restent hors apprentissage. Une sélection de modèle entre variantes sur DUEL serait exploratoire, pas une qualification indépendante.","",
         "## Constat principal", "",
         f"Biais prévu−réel en SOLO **{fmt(ss)} £/an**, contre **{fmt(dd)} £/an** en DUEL : transfert de domaine instable. Le constat ne justifie pas une correction multiplicative calibrée sur SOLO.","",
         "Chaque correction de profit garde le coût brut inchangé et utilise seulement `pred_prof`, `cargo`, `distance` ou `roi_pred` (candidats au choix). Les ratios sont bornés à [0,25 ; 2], les corrections additives à 2 000 £/an après pondération, la pente affine à [0,5 ; 1,5] avant un retrait à 10 %. `add_dist_factor10` borne aussi le **facteur de profit** final à [0,9 ; 1,1] : k = 1 + clip(0,1 × résidu SOLO rétréci, −0,1 × profit prévu, +0,1 × profit prévu) / profit prévu, pour profit prévu > 0. La correction `solo_inner_select` est choisie automatiquement par validation SOLO interne sur 4 sous-plis, puis appliquée au DUEL exclu.","",
         "| Modèle | MAE DUEL £/an | Biais £/an | Gain vs brut £/an par ligne | Graines améliorées /40 | Gain moyen /graine [IC95 bootstrap] £ | Spearman médian profit /graine |",
         "|---|---:|---:|---:|---:|---:|---:|"]
    base=stats["raw"][0]
    for name in NAMES:
        mae,bias,wins,gain,lo,hi,rho=stats[name]
        out.append(f"| {name} | {fmt(mae)} | {fmt(bias)} | {fmt(base-mae)} | {wins}/40 | {fmt(gain)} [{fmt(lo)} ; {fmt(hi)}] | {rho:.3f} |")
    out += ["", "## Validation croisée", "", "| Pli | Entraînement SOLO (lignes) | Test DUEL (lignes) | Choix sur SOLO interne | MAE SOLO interne brut | MAE SOLO interne choisi |","|---|---:|---:|---|---:|---:|"]
    for i,tr,te,choice,raw,cal,fold_gain,dist_ratio,dist_add in outer:
        out.append(f"| {i} | {tr} | {te} | {choice} | {fmt(raw)} | {fmt(cal)} |")
    out += ["", "Gains de MAE par pli DUEL (valeurs positives = réduction du MAE) :", "", "| Pli | dist_10 | cargo_dist_10 | add_dist_10 | add_dist_factor10 | Sélection SOLO interne |", "|---|---:|---:|---:|---:|---:|"]
    for i,tr,te,choice,raw,cal,fold_gain,dist_ratio,dist_add in outer:
        out.append(f"| {i} | {fmt(fold_gain['dist_10'])} | {fmt(fold_gain['cargo_dist_10'])} | {fmt(fold_gain['add_dist_10'])} | {fmt(fold_gain['add_dist_factor10'])} | {fmt(fold_gain['solo_inner_select'])} |")
    out += ["", "Paramètres SOLO du modèle simple par quartile, intervalles extrêmes entre plis (ces chiffres ne proviennent jamais de DUEL) :", "", "| Quartile | Ratio SOLO `dist` (min–max) | Additif SOLO `add_dist` £/an (min–max) |", "|---|---:|---:|"]
    for q in range(4):
        ratios=[f[7][q] for f in outer]
        adds=[f[8][q] for f in outer]
        out.append(f"| Q{q+1} | {min(ratios):.3f}–{max(ratios):.3f} | {fmt(min(adds))}–{fmt(max(adds))} |")
    out += ["", "## Interprétation et limites", "",
            "`real_prof` est le profit du véhicule pour l'année passée; `pred_prof` soustrait un amortissement théorique. L'écart ne prouve pas un biais structurel de revenu. Les lignes construites, survécues et âgées de 2 ans sont sélectionnées; le score ne démontre pas l'effet causal d'une modification de politique. `src_prod` est lu au bilan par la sonde conditionnelle `V284_RAIL_GROWTH` et n'est pas stocké dans les objets d'apprentissage ici ; l'employer à la sélection nécessiterait vérifier le champ candidat, son coût API et sa stabilité historique. Ne pas utiliser le `src_prod` post-construction comme prédicteur rétrospectif.","",
            "Le classement est le Spearman des profits annuels sur les mêmes lignes construites au sein de chaque graine (sans calibration du capital). Aucun changement de rang éventuel ne démontre une meilleure sélection contrefactuelle.","",
            "Recommandation : distinguer le candidat **choisi sans lire DUEL**, `solo_inner_select`, des nombreux essais exploratoires. Un gain moyen positif sur des modèles choisis après consultation DUEL n'est pas une qualification. Pour une politique qualifiée, garder le facteur de profit à 1 sans preuve sur un autre échantillon ; un facteur non neutre peut être placé sous drapeau expérimental clairement identifié pour tester le contrat du prompt 4, sans bascule du défaut.","",
            "Reproduire : `python -X utf8 sweeps/demo_rail_cal_profit_safe_20261021.py`. Pas de Docker ni de modification de `ai/OpexAI`."]
    return "\n".join(out)+"\n"


if __name__ == "__main__":
    so,du,folds,stats=run()
    REPORT.write_text(markdown(so,du,folds,stats),encoding="utf-8")
    for key in NAMES:
        print(key, *(fmt(z) if isinstance(z,(int,float)) else z for z in stats[key][:6]))
    print("Report:",REPORT)
