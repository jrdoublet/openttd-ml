"""ESTIM-1 lot 1 : a priori du facteur de realisation de la RECETTE par mode.

Lit les journaux moteur `decision_log=1` d'une ou plusieurs campagnes (fichiers
`<bras>_seed<N>_r<k>.log`, .gz accepte) et mesure, pour OpexAI (compagnie 0),
le rapport recette realisee / recette predite brute dans les conditions exactes
de l'apprentissage en partie de `estim_unifie` bit 1 :

- annee pleine seulement (age >= 2, piege V298) ;
- flotte egale a la flotte de construction (`vehs == n0`) : aucune normalisation
  lineaire par la flotte ;
- recette realisee = profit + frais courants (`real_rev` de LINE_REVENUE) ;
- recette predite brute : `pred_rev` (= `predRevenue` de la ligne). Pour AIR, la
  realisation C121 adaptative est inactive par defaut (facteur 1) : `pred_rev` est la
  recette du modele physique nette de cannibalisation, tous bras. La cellule
  `air_newpair` isole les paires neuves ; C121_REALIZATION sert de controle.

Agregat : rapport des sommes (comme le moteur). Le poids de l'a priori est estime par
Bayes empirique : variance intra-partie des ratios de ligne / variance inter-parties
des moyennes de partie (en nombre de lignes equivalentes).

Usage :
  python -X utf8 sweeps/estim_unifie_priors.py \
      --campaign duel=results/calibration_pc_20261021/results/calib_duel_40x10_pc_20261021_engine \
      --campaign solo=results/calibration_pc_20261021/results/calib_solo_40x10_pc_20261021_engine \
      --out results/estim_unifie_priors_20261027.json
  python -X utf8 sweeps/estim_unifie_priors.py --selftest
"""
import argparse
import glob
import gzip
import json
import os
import re
import statistics
import sys
from collections import defaultdict

OPEX_RE = re.compile(r"\[0\] \[.\] OPEX (\d+)-(\d+)-(\d+) (\S+) (.*)$")
RAW_RE = re.compile(r"\[0\] \[.\] (C121_BUILD|C121_REALIZATION) (.*)$")
KV_RE = re.compile(r"(\w+)=(\S+)")
SEED_RE = re.compile(r"_seed(\d+)_r(\d+)\.log")
ERAS = [("1970-1973", 1900, 1973), ("1974-1976", 1974, 1976), ("1977-", 1977, 3000)]
MODES = ("rail", "road", "air")


def num(value, default=None):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return v if v == v and abs(v) != float("inf") else default


def open_text(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def era_of(year):
    for name, lo, hi in ERAS:
        if lo <= year <= hi:
            return name
    return "other"


def parse_game(lines):
    """Rend (samples, c121) : echantillons de recette et moyennes C121 par bras."""
    builds = {}
    arms = {}
    samples = []
    c121 = []
    for raw in lines:
        m = RAW_RE.search(raw)
        if m:
            kv = dict(KV_RE.findall(m.group(2)))
            if m.group(1) == "C121_BUILD":
                arms[kv.get("line")] = kv.get("arm")
            else:
                n = int(num(kv.get("lines"), 0))
                f = num(kv.get("factor"))
                if kv.get("phase") == "annual" and n >= 2 and f is not None:
                    c121.append({"year": int(num(kv.get("year"), 0)), "arm": kv.get("arm"),
                                 "n": n, "mean": (f * (n + 1) - 1.0) / n})
            continue
        m = OPEX_RE.search(raw)
        if not m:
            continue
        tag, rest = m.group(4), m.group(5)
        kv = dict(KV_RE.findall(rest))
        if tag in ("RAIL_BUILD", "AIR_BUILD", "ROAD_BUILD"):
            n0 = num(kv.get("trains") or kv.get("planes") or kv.get("vehicles"))
            if n0 and n0 > 0:
                builds[kv.get("line")] = {"mode": tag.split("_")[0].lower(), "n0": n0}
        elif tag == "LINE_REVENUE":
            age = num(kv.get("age"), -1)
            line = kv.get("line")
            b = builds.get(line)
            pred = num(kv.get("pred_rev"))
            real = num(kv.get("real_rev"))
            vehs = num(kv.get("vehs"), 0)
            mode = kv.get("mode")
            if age < 2 or b is None or mode not in MODES or b["mode"] != mode:
                continue
            if pred is None or pred <= 0 or real is None:
                continue
            samples.append({"line": line, "mode": mode, "arm": arms.get(line, "-"),
                            "year": int(num(kv.get("year"), 0)), "age": int(age),
                            "pred": pred, "real": max(real, 0.0), "vehs": vehs, "n0": b["n0"]})
    return samples, c121


def load_campaign(path):
    files = sorted(glob.glob(os.path.join(path, "*.log")) + glob.glob(os.path.join(path, "*.log.gz")))
    games = {}
    for f in files:
        m = SEED_RE.search(os.path.basename(f).replace(".gz", ""))
        key = os.path.basename(f).split(".log")[0] if not m else "seed%s_r%s" % m.groups()
        if key in games:
            continue
        with open_text(f) as fh:
            games[key] = parse_game(fh)
    return games


def eligible(sample, cell):
    if sample["mode"] != cell.split("_")[0]:
        return False
    if cell == "air_newpair" and sample["arm"] != "newpair":
        return False
    return sample["vehs"] == sample["n0"]


def cell_stats(games, cell, era=None, age=None):
    real = pred = 0.0
    ratios = []
    per_game = []
    lines = set()
    for gkey, (samples, _c) in games.items():
        g_ratios = []
        for s in samples:
            if not eligible(s, cell):
                continue
            if era is not None and era_of(s["year"] - 1) != era:
                continue
            if age is not None and (s["age"] if age != "3+" else min(s["age"], 3)) != (age if age != "3+" else 3):
                continue
            real += s["real"]
            pred += s["pred"]
            r = s["real"] / s["pred"]
            ratios.append(r)
            g_ratios.append(r)
            lines.add((gkey, s["line"]))
        if g_ratios:
            per_game.append(g_ratios)
    if not ratios:
        return {"n": 0}
    out = {"n": len(ratios), "lines": len(lines), "games": len(per_game),
           "ratio_of_sums": round(real / pred, 4), "median": round(statistics.median(ratios), 4),
           "mean": round(statistics.fmean(ratios), 4)}
    out.update(prior_weight(per_game))
    return out


def prior_weight(per_game):
    """Poids de l'a priori en lignes equivalentes : sigma2_intra / tau2_inter."""
    multi = [g for g in per_game if len(g) >= 2]
    if len(multi) < 3:
        return {}
    within = statistics.fmean(statistics.variance(g) for g in multi)
    means = [statistics.fmean(g) for g in per_game]
    sizes = [len(g) for g in per_game]
    if len(means) < 3:
        return {}
    between_raw = statistics.variance(means)
    noise = statistics.fmean(within / n for n in sizes)
    tau2 = between_raw - noise
    out = {"sigma2_within": round(within, 4), "var_game_means": round(between_raw, 4),
           "tau2_between": round(tau2, 4)}
    if tau2 > 0:
        out["prior_weight_lines"] = round(within / tau2, 2)
    return out


def c121_arms(games):
    acc = defaultdict(lambda: [0.0, 0])
    acc_early = defaultdict(lambda: [0.0, 0])
    for _g, (_s, c121) in games.items():
        for row in c121:
            acc[row["arm"]][0] += row["mean"] * row["n"]
            acc[row["arm"]][1] += row["n"]
            if row["year"] <= 1974:
                acc_early[row["arm"]][0] += row["mean"] * row["n"]
                acc_early[row["arm"]][1] += row["n"]
    res = {}
    for arm, (s, n) in acc.items():
        e = acc_early.get(arm, [0.0, 0])
        res[arm] = {"weighted_mean": round(s / n, 4) if n else None, "samples": n,
                    "weighted_mean_le1974": round(e[0] / e[1], 4) if e[1] else None,
                    "samples_le1974": e[1]}
    return res


def analyse(campaigns):
    out = {}
    for name, games in campaigns.items():
        res = {"games": len(games), "cells": {}, "c121_arms_mean_of_ratios": c121_arms(games)}
        for cell in ("rail", "road", "air", "air_newpair"):
            row = {"all": cell_stats(games, cell)}
            for era, _lo, _hi in ERAS:
                row[era] = cell_stats(games, cell, era=era)
            row["age2"] = cell_stats(games, cell, age=2)
            row["age3+"] = cell_stats(games, cell, age="3+")
            res["cells"][cell] = row
        stable = defaultdict(lambda: [0, 0])
        for _g, (samples, _c) in games.items():
            for s in samples:
                key = s["mode"] if s["mode"] != "air" else "air_" + s["arm"]
                stable[key][1] += 1
                if s["vehs"] == s["n0"]:
                    stable[key][0] += 1
        res["stable_fleet_share"] = {k: {"stable": v[0], "all": v[1]} for k, v in sorted(stable.items())}
        out[name] = res
    return out


def selftest():
    lines = [
        "[0] [I] C121_BUILD line=3 arm=newpair engine=1",
        "[0] [I] OPEX 1970-3-1 AIR_BUILD line=3 planes=1 cost=5",
        "[0] [I] OPEX 1970-4-1 RAIL_BUILD line=4 trains=1 cost=5",
        "[0] [I] OPEX 1972-1-6 LINE_REVENUE line=3 mode=air year=1972 age=2 pred_rev=1000 real_rev=500 vehs=1",
        "[0] [I] OPEX 1973-1-6 LINE_REVENUE line=3 mode=air year=1973 age=3 pred_rev=1000 real_rev=400 vehs=2",
        "[0] [I] OPEX 1972-1-6 LINE_REVENUE line=4 mode=rail year=1972 age=2 pred_rev=200 real_rev=300 vehs=1",
        "[0] [I] OPEX 1971-1-6 LINE_REVENUE line=4 mode=rail year=1971 age=1 pred_rev=200 real_rev=50 vehs=1",
        "[0] [I] C121_REALIZATION phase=annual year=1973 arm=hubsite lines=3 factor=0.5",
    ]
    samples, c121 = parse_game(lines)
    assert len(samples) == 3, samples
    games = {"g": (samples, c121)}
    air = cell_stats(games, "air_newpair")
    assert air["n"] == 1 and air["ratio_of_sums"] == 0.5, air
    assert cell_stats(games, "air")["n"] == 1
    rail = cell_stats(games, "rail")
    assert rail["n"] == 1 and rail["ratio_of_sums"] == 1.5, rail
    assert abs(c121[0]["mean"] - (0.5 * 4 - 1) / 3) < 1e-9
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaign", action="append", default=[], help="nom=dossier de journaux")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return 0
    if not args.campaign:
        ap.error("--campaign requis")
    campaigns = {}
    for spec in args.campaign:
        name, path = spec.split("=", 1)
        campaigns[name] = load_campaign(path)
    out = analyse(campaigns)
    text = json.dumps(out, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
