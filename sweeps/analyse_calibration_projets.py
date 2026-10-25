"""Calibration des couts et revenus des projets : predit (modele) contre realise.

Lit les journaux moteur d'une ou plusieurs campagnes `run_c66_reference.py` jouees avec
`decision_log=1` et `--script-debug` (fichiers `<bras>_seed<N>_r<k>.log`, .gz accepte), et
apparie pour OpexAI (compagnie 0) :
- PROJECT_CHOSEN (cout et profit predits au choix) ;
- RAIL_BUILD / AIR_BUILD / ROAD_BUILD / WATER_BUILD (ligne, distance, cout reel, flotte initiale) ;
- LINE_REVENUE (rapport annuel : revenu, profit et exploitation predits et realises, age, flotte).

Une copie .log/.log.gz d'une meme partie ne compte qu'une fois si ses donnees de calibration
sont identiques ; des copies contradictoires interrompent l'analyse avec leurs deux chemins.
Le bras et la repetition restent distincts, meme a graine identique.

Le predit de LINE_REVENUE est le modele BRUT (`line.predicted` = profitAnnual avant C70).
Seules les lignes d'age >= 2 comptent (piege V298 : annee partielle). Le realise est ramene a la
flotte initiale (x n0 / vehs) : sinon le ratio mesure la croissance de la flotte, pas le modele.

Sorties (JSON + resume texte) :
1. cout reel / cout predit par mode (et par tranche de distance pour le rail) ;
2. revenu, exploitation et profit realises / predits par cellule
   mode x classe de cargo x tranche de distance x epoque, par campagne ;
3. validation croisee a deux plis sur les graines : erreur de prediction du revenu
   (|log reel/predit|, mediane) sans correction, avec un facteur par mode (type C70) et avec
   la table par cellule apprise sur l'autre pli, eventuellement sur une autre campagne
   (`--train` / `--test` : apprendre en solo, tester en duel). Les plis couvrent toutes les
   graines de test ; les memes graines sont exclues de l'apprentissage, tous bras et repetitions ;
4. part de la variance residuelle entre parties (ce qu'un apprentissage en cours de partie peut
   corriger) et dans une partie (ce qu'il ne peut pas corriger).

Usage :
  python3 sweeps/analyse_calibration_projets.py --campaign solo=results/calib_solo_40x10_pc_engine \
      --campaign duel=results/calib_duel_40x10_pc_engine --train solo --test duel \
      --out results/calibration_projets.json
  python3 sweeps/analyse_calibration_projets.py --selftest
"""
import argparse
import glob
import gzip
import json
import math
import os
import re
import statistics
import sys
from collections import defaultdict

SECONDARY = {"GOOD", "STEL", "FOOD", "PAPR", "WATR", "BEER", "FZDR", "PLAS", "TOYS", "SWET", "FUEL"}
DIST_BINS = [(0, 80), (80, 160), (160, 250), (250, 10 ** 6)]
ERAS = [(1900, 1973), (1974, 1976), (1977, 3000)]
MIN_CELL = 5

LINE_RE = re.compile(r"\[0\] \[.\] OPEX (\d+)-(\d+)-(\d+) (\S+) (.*)$")
KV_RE = re.compile(r"(\w+)=(\S+)")
SEED_RE = re.compile(r"_seed(\d+)_r(\d+)\.log")


def open_text(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, encoding="utf-8", errors="replace")


def num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def cargo_class(label):
    if label == "PASS":
        return "PASS"
    if label == "MAIL":
        return "MAIL"
    if label in SECONDARY:
        return "SECONDARY"
    return "RAW"


def dist_bin(d):
    if d is None:
        return "?"
    for lo, hi in DIST_BINS:
        if lo <= d < hi:
            return "%d-%s" % (lo, hi if hi < 10 ** 6 else "")
    return "?"


def era(year):
    for lo, hi in ERAS:
        if lo <= year <= hi:
            return "%d-%d" % (max(lo, 1970), min(hi, 1979))
    return "?"


def parse_game(lines):
    """Rend (builds, revenue_rows, cost_rows) pour une partie."""
    chosen = {}
    builds = {}
    revenue = []
    costs = []
    for raw in lines:
        m = LINE_RE.search(raw)
        if not m:
            continue
        y, tag, rest = int(m.group(1)), m.group(4), m.group(5)
        kv = dict(KV_RE.findall(rest))
        if tag == "PROJECT_CHOSEN":
            key = (kv.get("mode"), kv.get("src"), kv.get("dst"))
            chosen[key] = {"cost": num(kv.get("cost")), "profit": num(kv.get("profit")), "year": y}
        elif tag in ("RAIL_BUILD", "AIR_BUILD", "ROAD_BUILD", "WATER_BUILD"):
            mode = tag.split("_")[0].lower()
            line = kv.get("line")
            n0 = num(kv.get("trains") or kv.get("planes") or kv.get("vehicles"), 1.0)
            b = {"mode": mode, "dist": num(kv.get("dist")), "cost": num(kv.get("cost")),
                 "n0": n0 if n0 and n0 > 0 else 1.0, "year": y, "cargo": kv.get("cargo", "PASS")}
            builds[line] = b
            pc = chosen.get((mode, kv.get("src"), kv.get("dst")))
            # AIR_BUILD et WATER_BUILD journalisent le capital du plan (devis exact) : pas un realise.
            if pc and pc["cost"] and b["cost"] and mode in ("rail", "road"):
                costs.append({"mode": mode, "dist": b["dist"], "pred": pc["cost"], "real": b["cost"],
                              "year": y})
        elif tag == "LINE_REVENUE":
            age = num(kv.get("age"), -1)
            if age is None or age < 2:
                continue
            revenue.append({"line": kv.get("line"), "mode": kv.get("mode"), "cargo": kv.get("cargo"),
                            "year": num(kv.get("year")), "pred_rev": num(kv.get("pred_rev")),
                            "real_rev": num(kv.get("real_rev")), "pred_prof": num(kv.get("pred_prof")),
                            "real_prof": num(kv.get("real_prof")), "pred_run": num(kv.get("pred_run")),
                            "real_run": num(kv.get("real_run")), "vehs": num(kv.get("vehs"), 0)})
    return builds, revenue, costs


def load_campaign(path):
    """Charge une fois chaque journal logique ; refuse les copies de donnees contradictoires."""
    games = {}
    sources = {}
    files = sorted(glob.glob(os.path.join(path, "*.log")) + glob.glob(os.path.join(path, "*.log.gz")))
    for f in files:
        name = os.path.basename(f)
        if name.endswith(".gz"):
            name = name[:-3]
        m = SEED_RE.search(name)
        if not m:
            continue
        with open_text(f) as fh:
            builds, revenue, costs = parse_game(fh)
        rows = []
        unmatched = 0
        for r in revenue:
            b = builds.get(r["line"])
            if b is None or not r["vehs"] or r["vehs"] <= 0:
                unmatched += 1
                continue
            scale = b["n0"] / r["vehs"]
            row = dict(r)
            row.update({"dist": b["dist"], "n0": b["n0"], "scale": scale,
                        "cell": "%s|%s|%s|%s" % (r["mode"], cargo_class(r["cargo"]), dist_bin(b["dist"]),
                                                 era(int(r["year"] or 0)))})
            rows.append(row)
        key = (name, int(m.group(1)))
        game = {"rows": rows, "costs": costs, "unmatched": unmatched}
        if key in games:
            if games[key] != game:
                raise ValueError("Journaux de calibration contradictoires : %s et %s" % (sources[key], f))
            continue
        games[key] = game
        sources[key] = f
    return games


def ratio(real, pred, scale=1.0):
    if pred is None or real is None or pred <= 0:
        return None
    value = real * scale / pred
    return value if value > 0 else None


def summarize(values):
    values = [v for v in values if v is not None]
    if not values:
        return {"n": 0}
    out = {"n": len(values), "median": round(statistics.median(values), 4)}
    if len(values) >= 4:
        q = statistics.quantiles(values, n=4)
        out["q1"], out["q3"] = round(q[0], 4), round(q[2], 4)
    pos = [v for v in values if v > 0]
    if pos:
        out["geo"] = round(math.exp(sum(math.log(v) for v in pos) / len(pos)), 4)
    return out


def cells_table(games, metric="rev"):
    by = defaultdict(list)
    for g in games.values():
        for r in g["rows"]:
            by[r["cell"]].append(ratio(r["real_" + metric], r["pred_" + metric], r["scale"]))
    return {k: summarize(v) for k, v in sorted(by.items())}


def factor_tables(games):
    """Facteurs (mediane du ratio de revenu) par mode et par cellule, sur un ensemble de parties."""
    mode = defaultdict(list)
    cell = defaultdict(list)
    for g in games.values():
        for r in g["rows"]:
            x = ratio(r["real_rev"], r["pred_rev"], r["scale"])
            if x is None:
                continue
            mode[r["mode"]].append(x)
            cell[r["cell"]].append(x)
    mf = {k: statistics.median(v) for k, v in mode.items()}
    cf = {k: (statistics.median(v), len(v)) for k, v in cell.items()}
    return mf, cf


def predict_error(games, mf, cf):
    """Mediane de |log(reel/predit corrige)| sans correction, facteur mode, table par cellule."""
    errs = {"raw": [], "mode": [], "cell": []}
    residuals = defaultdict(list)
    for key, g in games.items():
        for r in g["rows"]:
            x = ratio(r["real_rev"], r["pred_rev"], r["scale"])
            if x is None:
                continue
            fm = mf.get(r["mode"], 1.0)
            c = cf.get(r["cell"])
            fc = c[0] if c and c[1] >= MIN_CELL else fm
            errs["raw"].append(abs(math.log(x)))
            errs["mode"].append(abs(math.log(x / fm)))
            errs["cell"].append(abs(math.log(x / fc)))
            residuals[key].append(math.log(x / fc))
    out = {k: round(statistics.median(v), 4) if v else None for k, v in errs.items()}
    out["n"] = len(errs["raw"])
    # Decomposition de la variance du residu : entre parties (corrigeable en partie) / dans une partie.
    allr = [v for vs in residuals.values() for v in vs]
    if len(allr) > 2:
        grand = statistics.mean(allr)
        between = sum(len(vs) * (statistics.mean(vs) - grand) ** 2 for vs in residuals.values() if vs)
        total = sum((v - grand) ** 2 for v in allr)
        out["between_game_share"] = round(between / total, 4) if total > 0 else None
    return out


def cross_validate(train, test):
    """Score chaque graine de test une fois, sans apprendre sur cette graine.

    Les graines presentes seulement dans train restent disponibles dans les deux plis.
    A graines identiques, le decoupage historique est conserve.
    """
    seeds = sorted({s for (_, s) in test})
    folds = [set(seeds[0::2]), set(seeds[1::2])]
    res = []
    for k, fold in enumerate(folds):
        tr = {key: g for key, g in train.items() if key[1] not in fold}
        te = {key: g for key, g in test.items() if key[1] in fold}
        mf, cf = factor_tables(tr)
        e = predict_error(te, mf, cf)
        e["fold"] = k
        res.append(e)
    return res


def cost_summary(games):
    by = defaultdict(list)
    for g in games.values():
        for c in g["costs"]:
            by[c["mode"]].append(c["real"] / c["pred"])
            if c["mode"] == "rail":
                by["rail|" + dist_bin(c["dist"])].append(c["real"] / c["pred"])
    return {k: summarize(v) for k, v in sorted(by.items())}


def analyse(campaigns, train=None, test=None):
    out = {"campaigns": {}}
    for name, games in campaigns.items():
        out["campaigns"][name] = {
            "games": len(games),
            "line_years": sum(len(g["rows"]) for g in games.values()),
            "unmatched": sum(g["unmatched"] for g in games.values()),
            "cost": cost_summary(games),
            "revenue_cells": cells_table(games, "rev"),
            "running_cells": cells_table(games, "run"),
            "profit_cells": cells_table(games, "prof"),
            "cv_same_campaign": cross_validate(games, games),
        }
    if train and test and train in campaigns and test in campaigns:
        out["cv_train_%s_test_%s" % (train, test)] = cross_validate(campaigns[train], campaigns[test])
    return out


def print_report(out):
    for name, c in out["campaigns"].items():
        print("== %s : %d parties, %d lignes-annees (age >= 2), %d non appariees"
              % (name, c["games"], c["line_years"], c["unmatched"]))
        print("  cout reel / predit :", json.dumps(c["cost"]))
        print("  revenu reel / predit par cellule (n >= %d) :" % MIN_CELL)
        for k, v in c["revenue_cells"].items():
            if v.get("n", 0) >= MIN_CELL:
                print("    %-36s n=%4d med=%.3f q1=%s q3=%s" % (k, v["n"], v["median"], v.get("q1"), v.get("q3")))
        for e in c["cv_same_campaign"]:
            print("  pli %d : |log| med brut=%s mode=%s cellule=%s ; part entre parties=%s"
                  % (e["fold"], e["raw"], e["mode"], e["cell"], e.get("between_game_share")))
    for k, v in out.items():
        if k.startswith("cv_train_"):
            for e in v:
                print("%s pli %d : brut=%s mode=%s cellule=%s ; part entre parties=%s"
                      % (k, e["fold"], e["raw"], e["mode"], e["cell"], e.get("between_game_share")))


def selftest():
    log = [
        "[0] [I] OPEX 1971-1-1 PROJECT_CHOSEN rank=0 mode=rail kind=freight cargo=COAL src=1 dst=2 dist=100 cost=1000 profit=500 roi=500",
        "[0] [I] OPEX 1971-2-1 RAIL_BUILD line=3 src=1 dst=2 cargo=COAL dist=100 pred_profit=500 cost=1500 trains=2 wagons=6",
        "[0] [I] OPEX 1974-1-1 LINE_REVENUE line=3 mode=rail kind=freight cargo=COAL year=1974 age=3 pred_rev=800 real_rev=1200 pred_prof=500 real_prof=700 pred_run=300 real_run=500 vehs=4 low_ratio=0",
        "[0] [I] OPEX 1972-1-1 LINE_REVENUE line=3 mode=rail kind=freight cargo=COAL year=1972 age=1 pred_rev=800 real_rev=1 pred_prof=500 real_prof=1 pred_run=300 real_run=1 vehs=2 low_ratio=0",
        "[1] [I] OPEX 1974-1-1 LINE_REVENUE line=3 mode=rail kind=freight cargo=COAL year=1974 age=3 pred_rev=1 real_rev=1 vehs=1",
    ]
    builds, revenue, costs = parse_game(log)
    assert builds["3"]["n0"] == 2.0 and builds["3"]["dist"] == 100.0
    assert len(revenue) == 1, revenue  # age 1 et compagnie 1 ecartes
    assert costs == [{"mode": "rail", "dist": 100.0, "pred": 1000.0, "real": 1500.0, "year": 1971}]
    # revenu par vehicule initial : 1200 * 2/4 / 800 = 0.75
    assert abs(ratio(1200.0, 800.0, 2.0 / 4.0) - 0.75) < 1e-9
    assert cargo_class("GOOD") == "SECONDARY" and cargo_class("COAL") == "RAW"
    assert dist_bin(160) == "160-250" and dist_bin(300) == "250-" and era(1975) == "1974-1976"
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaign", action="append", default=[], help="nom=dossier_engine (repetable)")
    ap.add_argument("--train")
    ap.add_argument("--test")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    if not a.campaign:
        ap.error("au moins une --campaign nom=dossier")
    campaigns = {}
    for spec in a.campaign:
        name, _, path = spec.partition("=")
        campaigns[name] = load_campaign(path)
    out = analyse(campaigns, a.train, a.test)
    print_report(out)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
