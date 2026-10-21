#!/usr/bin/env python3
"""Rapport cout / profit par cargo et vrai quartile de distance.

Lit les journaux de calibration OpexAI (compagnie 0), sans relancer de banc.
Les quartiles sont calcules par mode sur les lignes construites uniques des
campagnes reunies, et fixes pour comparer solo et duel. Une observation de cout
est une construction appariee PROJECT_CHOSEN -> RAIL/ROAD_BUILD. Une observation
de profit est une ligne-annee mature (age >= 2), corrigee a la flotte initiale.
Les ratios de profit admettent des profits reels negatifs (pred_prof > 0).

AIR_BUILD et WATER_BUILD ne journalisent pas un cout physique constate :
aucun ratio de cout reel/predit n'est calcule pour ces modes.
"""
import argparse
import bisect
import csv
import json
import math
import os
import statistics
from collections import defaultdict

from analyse_calibration_projets import KV_RE, LINE_RE, SEED_RE, open_text
from glob import glob


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    pos = fraction * (len(values) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def median(values):
    return statistics.median(values) if values else None


def rounded(value, digits=3):
    return round(value, digits) if value is not None and math.isfinite(value) else None


def num(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def parse_logs(folder, arm):
    builds_all = []
    cost_all = []
    profit_all = []
    counts = defaultdict(int)
    games = 0
    for filename in sorted(glob(os.path.join(folder, "*.log")) + glob(os.path.join(folder, "*.log.gz"))):
        match = SEED_RE.search(os.path.basename(filename).replace(".gz", ""))
        if not match:
            continue
        games += 1
        gameid = (arm, match.group(1), match.group(2))
        selected = {}
        built = {}
        rows = []
        with open_text(filename) as lines:
            for raw in lines:
                found = LINE_RE.search(raw)
                if not found:
                    continue
                tag = found.group(4)
                if tag not in ("PROJECT_CHOSEN", "RAIL_BUILD", "ROAD_BUILD", "AIR_BUILD",
                               "WATER_BUILD", "LINE_REVENUE"):
                    continue
                kv = dict(KV_RE.findall(found.group(5)))
                if tag == "PROJECT_CHOSEN":
                    selected[(kv.get("mode"), kv.get("src"), kv.get("dst"))] = kv
                elif tag in ("RAIL_BUILD", "ROAD_BUILD", "AIR_BUILD", "WATER_BUILD"):
                    mode = tag.partition("_")[0].lower()
                    distance = num(kv.get("dist"))
                    line = kv.get("line")
                    n0 = num(kv.get("trains") or kv.get("planes") or kv.get("vehicles"))
                    if line is None or distance is None:
                        counts["build_unusable"] += 1
                        continue
                    b = {"game": gameid, "line": line, "mode": mode,
                         "cargo": kv.get("cargo", "PASS"), "distance": distance,
                         "n0": n0 if n0 is not None and n0 > 0 else 1.0}
                    built[line] = b
                    builds_all.append(b)
                    if mode not in ("rail", "road"):
                        counts["cost_unobservable_" + mode] += 1
                        continue
                    counts["cost_eligible_" + mode] += 1
                    chosen = selected.get((mode, kv.get("src"), kv.get("dst")))
                    expected = num(chosen.get("cost")) if chosen else None
                    actual = num(kv.get("cost"))
                    if expected is None or expected <= 0:
                        counts["cost_no_valid_prediction"] += 1
                    elif actual is None or actual <= 0:
                        counts["cost_nonpositive_actual"] += 1
                    else:
                        cost_all.append({**b, "predicted": expected, "actual": actual,
                                         "ratio": actual / expected})
                else:
                    age = num(kv.get("age"))
                    if age is None or age < 2:
                        continue
                    rows.append(kv)
        for r in rows:
            b = built.get(r.get("line"))
            vehicles = num(r.get("vehs"))
            pred = num(r.get("pred_prof"))
            actual = num(r.get("real_prof"))
            if b is None:
                counts["profit_no_build"] += 1
            elif vehicles is None or vehicles <= 0:
                counts["profit_no_vehicles"] += 1
            elif pred is None or pred <= 0:
                counts["profit_nonpositive_prediction"] += 1
            elif actual is None:
                counts["profit_no_actual"] += 1
            else:
                normalized = actual * b["n0"] / vehicles
                profit_all.append({**b, "cargo": r.get("cargo") or b["cargo"],
                                   "year": num(r.get("year")), "predicted": pred,
                                   "actual": normalized, "ratio": normalized / pred})
        counts["games"] += 1
    return builds_all, cost_all, profit_all, dict(counts)


def describe(records, metric):
    ratios = [x["ratio"] for x in records]
    predicted = [x["predicted"] for x in records]
    actual = [x["actual"] for x in records]
    abs_errs = [abs(x["actual"] - x["predicted"]) for x in records]
    result = {
        "n": len(records),
        "seeds": len(set(x["game"][1] for x in records)),
        "lines": len(set((x["game"], x["line"]) for x in records)),
        "ratio_median": rounded(median(ratios)),
        "ratio_q1": rounded(percentile(ratios, 0.25)),
        "ratio_q3": rounded(percentile(ratios, 0.75)),
        "median_pred": rounded(median(predicted), 1),
        "median_real": rounded(median(actual), 1),
        "median_abs_error": rounded(median(abs_errs), 1),
        "median_relative_abs_error_pct": rounded(median([abs(x-1)*100 for x in ratios]), 1),
        "negative_real": sum(x["actual"] < 0 for x in records),
        "nonpositive_real": sum(x["actual"] <= 0 for x in records),
    }
    if metric == "profit":
        # Summary by line (not year), useful to diagnose long-lived line weighting.
        byline = defaultdict(list)
        for row in records:
            byline[(row["game"], row["line"])].append(row["ratio"])
        result["equal_line_median_ratio"] = rounded(median([median(v) for v in byline.values()]))
    return result


def report(campaigns):
    parsed = {}
    pooled_distances = defaultdict(list)
    for arm, path in campaigns.items():
        builds, costs, profits, counts = parse_logs(path, arm)
        parsed[arm] = (builds, costs, profits, counts)
        for b in builds:
            pooled_distances[b["mode"]].append(b["distance"])
    cuts = {mode: [percentile(ds, f) for f in (0.25, 0.50, 0.75)]
            for mode, ds in sorted(pooled_distances.items())}
    result = {
        "definition": {
            "quartiles": "par mode, construits uniques solo+duel, seuils communs entre bras",
            "cost": "cout de RAIL/ROAD_BUILD / cout de PROJECT_CHOSEN apparie, valeurs strictement positives",
            "profit": "LINE_REVENUE age>=2 : (real_prof * flotte_initiale / vehs) / pred_prof, pred_prof>0",
            "weighting": "ratio median par construction (cout) ou ligne-annee (profit)",
        },
        "distance_cuts": {m: [rounded(v, 3) for v in q] for m, q in cuts.items()},
        "builds": {a: {m: sum(b["mode"] == m for b in v[0]) for m in cuts}
                   for a, v in parsed.items()},
        "counts": {a: v[3] for a, v in parsed.items()},
        "rows": [],
    }
    for arm, (builds, costs, profits, counts) in parsed.items():
        for metric, data in (("cost", costs), ("profit", profits)):
            grouped = defaultdict(list)
            for row in data:
                # Quartile bas inclusif : une distance egale a la borne appartient
                # au quartile inferieur (Q1 <= p25, Q2 <= p50, etc.).
                q = 1 + bisect.bisect_left(cuts[row["mode"]], row["distance"])
                for cargo in ("ALL", row["cargo"]):
                    grouped[(row["mode"], cargo, q)].append(row)
                    grouped[(row["mode"], cargo, 0)].append(row)
            for (mode, cargo, quartile), rows in sorted(grouped.items()):
                result["rows"].append({
                    "arm": arm, "metric": metric, "mode": mode,
                    "cargo": cargo, "quartile": quartile,
                    **describe(rows, metric),
                })
    return result


def fmt(x, digits=2):
    return "-" if x is None else (("%." + str(digits) + "f") % x)


def as_markdown(result):
    out = [
        "# Calibration : cout physique et profit, par cargo et quartile de distance",
        "",
        "## Methode",
        "",
        "* Distances : quartiles **par mode** mesures sur chaque construction unique"
        " des 40 parties solo et 40 duel reunies. Les memes seuils sont utilises dans"
        " chaque bras. Q0 = tous les quartiles ; Q1 a Q4 = quartiles croissants.",
        "* Cout : comparaison du montant inscrit a PROJECT_CHOSEN et du cout inscrit"
        " a RAIL_BUILD / ROAD_BUILD. AIR_BUILD et WATER_BUILD contiennent un devis,"
        " **pas un cout physique mesure**. Les couts reels <= 0 et les predictions"
        " absentes ou <= 0 sont comptes comme exclusions.",
        "* Profit : profit annuel LINE_REVENUE a age >= 2, normalise par le nombre"
        " de vehicules initial (vehs initiaux / vehs actuels) et compare au profit"
        " annuel predit BRUT avant C70. Les profits observes negatifs restent inclus.",
        "* Ratio = reel / predit : 1,00 parfait, 0,50 = moitie du predit,"
        " 1,50 = +50 %. Erreur abs. mediane en £ par construction ou ligne-annee."
        " Les medians de ratio et des montants ne sont pas necessairement leurs quotients.",
        "* Fiabilite : n < 5 tres faible ; n < 20 indicatif. Les observations"
        " ligne-annee d'une meme ligne ne sont pas independantes ; la colonne"
        " 'ratio/ligne' pondere chaque ligne une fois.",
        "",
        "## Seuils des quartiles (distance du moteur)",
        "",
        "| Mode | Q1/Q2 | Q2/Q3 | Q3/Q4 |",
        "|---|---:|---:|---:|",
    ]
    for mode, (a, b, c) in result["distance_cuts"].items():
        out.append(f"| {mode} | {fmt(a, 1)} | {fmt(b, 1)} | {fmt(c, 1)} |")
    for metric, name in (("cost", "Cout de construction"), ("profit", "Profit annuel")):
        out.extend(["", f"## {name}", "",
                    "| Bras | Mode | Cargo | Quartile | n | lignes | ratio med. |"
                    " IQR ratio | err. abs. med. £ | reel <= 0 | ratio/ligne |",
                    "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"])
        for r in result["rows"]:
            if r["metric"] != metric:
                continue
            # Every row useful for audit; an Excel/CSV-friendly extract is also emitted.
            out.append("| {arm} | {mode} | {cargo} | {q} | {n} | {lines} | {ratio} |"
                       " {iqr} | {mae} | {bad} | {eq} |".format(
                           arm=r["arm"], mode=r["mode"], cargo=r["cargo"],
                           q="total" if r["quartile"] == 0 else "Q"+str(r["quartile"]),
                           n=r["n"], lines=r["lines"], ratio=fmt(r["ratio_median"]),
                           iqr=fmt(r["ratio_q1"])+"–"+fmt(r["ratio_q3"]),
                           mae=fmt(r["median_abs_error"], 0), bad=r["nonpositive_real"],
                           eq=fmt(r.get("equal_line_median_ratio")),
                       ))
    out.extend(["", "## Exclusions", "",
                "| Bras | Compteur | n |", "|---|---|---:|"])
    for arm, counts in result["counts"].items():
        for key, n in sorted(counts.items()):
            out.append(f"| {arm} | {key} | {n} |")
    return "\n".join(out)+"\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--campaign", action="append", required=True, help="nom=dossier_engine")
    ap.add_argument("--out-prefix", required=True, help="chemin sans extension .json/.csv/.md")
    args = ap.parse_args()
    campaigns = dict(spec.split("=", 1) for spec in args.campaign)
    result = report(campaigns)
    prefix = args.out_prefix
    os.makedirs(os.path.dirname(prefix) or ".", exist_ok=True)
    with open(prefix + ".json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(prefix + ".csv", "w", encoding="utf-8-sig", newline="") as f:
        fields = list(dict.fromkeys(key for row in result["rows"] for key in row))
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result["rows"])
    with open(prefix + ".md", "w", encoding="utf-8") as f:
        f.write(as_markdown(result))
    for mode, values in result["distance_cuts"].items():
        print(mode, "quartile cuts", values)
    for arm, counts in result["counts"].items():
        print(arm, counts)
    print("rows:", len(result["rows"]), "files:", prefix + ".{json,csv,md}")


if __name__ == "__main__":
    main()
