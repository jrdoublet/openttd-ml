#!/usr/bin/env python3
"""AIR-PELOTON-1 : agrégat des journaux moteur de la sonde AIR_PELOTON.

La sonde (``probes.nut``, ``OpexAirPelotonOnDepart`` / ``OpexAirPelotonFlushYear``)
n'écrit que sous DECISION_LOG (``probes`` & 508, par exemple 256) et seulement si le
journal script atteint les journaux moteur (``-d script=4``). Deux lignes :

* ``AIR_PELOTON_DEP line= stop=A|B station= veh= load= cap= load_pm= gap= planes= run=``
  à chaque départ détecté par l'échantillonnage C117 (cadence 2 jours) ; ``gap`` =
  jours depuis le départ précédent d'un AUTRE avion de la même ligne depuis la même
  gare (-1 = non défini) ; ``load_pm`` en pour mille de la capacité passagers.
* ``AIR_PELOTON line= year= planes= ... gap_med= gap_min= gap_cv= load_med=
  load_first= load_second= n_first= n_second=`` une fois par ligne et par an.

Hypothèse testée : les avions d'une même ligne se suivent, le second part presque
vide. Le lecteur produit la distribution des intervalles, la charge par rang dans
un peloton (rang 1 = départ après un intervalle normal, rang 2+ = départs suivant
un intervalle court < médiane/4 de la ligne), la corrélation intervalle ↔ charge et
le tout par nombre d'avions de la ligne. Mesure descriptive, non causale.

Usage : ``python3 sweeps/diag_air_peloton.py results/<campagne> [--out rapport.json]``
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

EVENT = re.compile(r"OPEX (\d{4})-(\d{1,2})-(\d{1,2}) (AIR_PELOTON(?:_DEP)?) (.*)")
FIELDS = re.compile(r"(\w+)=([^ ]+)")
GAP_BINS = ((0, 1), (2, 3), (4, 7), (8, 15), (16, 31), (32, 63), (64, None))
SHORT_DIVISOR = 4


def parse_fields(text: str) -> dict:
    out = {}
    for key, raw in FIELDS.findall(text):
        if key in ("stop",):
            out[key] = raw
            continue
        try:
            out[key] = int(raw)
        except ValueError:
            try:
                out[key] = float(raw)
            except ValueError:
                out[key] = raw
    return out


def open_log(path: Path):
    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def iter_log_files(paths):
    for p in paths:
        p = Path(p)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and (f.name.endswith(".log") or f.name.endswith(".log.gz")):
                    yield f
        elif p.is_file():
            yield p


def parse_log_lines(lines, source="<mem>"):
    """Retourne (departs, syntheses) d'un journal, dans l'ordre du fichier."""
    departs = []
    summaries = []
    for raw in lines:
        m = EVENT.search(raw)
        if not m:
            continue
        year, month, day, kind, rest = m.groups()
        row = parse_fields(rest)
        row["source"] = source
        row["date"] = (int(year), int(month), int(day))
        if kind == "AIR_PELOTON_DEP":
            if "line" in row and "load_pm" in row and "gap" in row:
                departs.append(row)
        else:
            if "line" in row and "departs" in row:
                summaries.append(row)
    return departs, summaries


def stats(values):
    vals = sorted(float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(v))
    if not vals:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None}

    def pct(p):
        if len(vals) == 1:
            return vals[0]
        x = (len(vals) - 1) * p
        lo, hi = int(math.floor(x)), int(math.ceil(x))
        return vals[lo] if lo == hi else vals[lo] * (hi - x) + vals[hi] * (x - lo)

    return {
        "n": len(vals),
        "mean": round(statistics.mean(vals), 3),
        "median": round(statistics.median(vals), 3),
        "p25": round(pct(0.25), 3),
        "p75": round(pct(0.75), 3),
    }


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return round(sxy / math.sqrt(sxx * syy), 4)


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def spearman(xs, ys):
    if len(xs) < 3:
        return None
    return pearson(ranks(xs), ranks(ys))


def gap_bin(gap):
    for lo, hi in GAP_BINS:
        if gap >= lo and (hi is None or gap <= hi):
            return f"{lo}-{hi}" if hi is not None else f">={lo}"
    return "?"


def planes_bucket(planes):
    if not isinstance(planes, int) or planes <= 0:
        return "?"
    return str(planes) if planes < 5 else "5+"


def annotate_ranks(departs):
    """Ajoute ``short``, ``line_gap_med`` et ``rank`` à chaque départ.

    Médiane d'intervalle par (source, ligne) sur les intervalles définis ; rang
    par (source, ligne, gare) : 1 après un intervalle >= médiane/4, +1 après
    chaque intervalle court consécutif ; None si l'intervalle est indéfini.
    """
    per_line = defaultdict(list)
    for d in departs:
        if d["gap"] >= 0:
            per_line[(d["source"], d["line"])].append(d["gap"])
    medians = {k: statistics.median(v) for k, v in per_line.items() if v}
    last_rank = {}
    for d in departs:
        med = medians.get((d["source"], d["line"]))
        d["line_gap_med"] = med
        key = (d["source"], d["line"], d.get("stop"))
        if d["gap"] < 0 or med is None:
            d["short"] = None
            d["rank"] = None
            last_rank.pop(key, None)
            continue
        short = d["gap"] * SHORT_DIVISOR < med
        d["short"] = short
        if short and last_rank.get(key) is not None:
            d["rank"] = last_rank[key] + 1
        else:
            d["rank"] = 2 if short else 1
        last_rank[key] = d["rank"]
    return departs


def summarize(departs, summaries):
    annotate_ranks(departs)
    valid = [d for d in departs if d["load_pm"] >= 0]
    with_gap = [d for d in valid if d["gap"] >= 0]

    gap_hist = defaultdict(lambda: {"n": 0, "loads": []})
    for d in with_gap:
        b = gap_hist[gap_bin(d["gap"])]
        b["n"] += 1
        b["loads"].append(d["load_pm"])
    gap_distribution = {}
    for lo, hi in GAP_BINS:
        label = gap_bin(lo)
        if label in gap_hist:
            v = gap_hist[label]
            gap_distribution[label] = {"n": v["n"], "load_pm": stats(v["loads"])}

    by_rank = defaultdict(list)
    for d in with_gap:
        if d["rank"] is None:
            continue
        by_rank["1" if d["rank"] == 1 else ("2" if d["rank"] == 2 else "3+")].append(d["load_pm"])

    def corr_block(rows):
        xs = [float(d["gap"]) for d in rows]
        ys = [float(d["load_pm"]) for d in rows]
        short = [d["load_pm"] for d in rows if d["short"]]
        long_ = [d["load_pm"] for d in rows if d["short"] is False
                 and d["line_gap_med"] is not None and d["gap"] >= d["line_gap_med"]]
        return {
            "n": len(rows),
            "pearson_gap_load": pearson(xs, ys),
            "spearman_gap_load": spearman(xs, ys),
            "load_short_gap": stats(short),
            "load_long_gap": stats(long_),
            "short_share": round(len(short) / len(rows), 4) if rows else None,
        }

    by_planes = defaultdict(list)
    for d in with_gap:
        by_planes[planes_bucket(d.get("planes"))].append(d)
    planes_block = {}
    for k in sorted(by_planes):
        rows = by_planes[k]
        ranks_k = defaultdict(list)
        for d in rows:
            if d["rank"] is not None:
                ranks_k["1" if d["rank"] == 1 else ("2" if d["rank"] == 2 else "3+")].append(d["load_pm"])
        planes_block[k] = {
            "gap": stats([d["gap"] for d in rows]),
            "load_by_rank": {r: stats(v) for r, v in sorted(ranks_k.items())},
            **corr_block(rows),
        }

    summ_planes = defaultdict(list)
    for s in summaries:
        summ_planes[planes_bucket(s.get("planes"))].append(s)
    summary_block = {}
    for k in sorted(summ_planes):
        rows = summ_planes[k]
        pairs = [s for s in rows if s.get("load_first", -1) >= 0 and s.get("load_second", -1) >= 0]
        summary_block[k] = {
            "line_years": len(rows),
            "departs": sum(s.get("departs", 0) for s in rows),
            "gap_med": stats([s["gap_med"] for s in rows if s.get("gap_med", -1) >= 0]),
            "gap_cv": stats([s["gap_cv"] for s in rows if s.get("gap_cv", -1) >= 0]),
            "load_med": stats([s["load_med"] for s in rows if s.get("load_med", -1) >= 0]),
            "load_first": stats([s["load_first"] for s in pairs]),
            "load_second": stats([s["load_second"] for s in pairs]),
            "line_years_with_both": len(pairs),
            "second_below_first": sum(1 for s in pairs if s["load_second"] < s["load_first"]),
        }

    return {
        "files": len({d["source"] for d in departs} | {s["source"] for s in summaries}),
        "departs": len(departs),
        "departs_with_load": len(valid),
        "departs_with_gap": len(with_gap),
        "summaries": len(summaries),
        "load_pm_all": stats([d["load_pm"] for d in valid]),
        "gap_days": stats([d["gap"] for d in with_gap]),
        "gap_distribution": gap_distribution,
        "load_by_rank": {r: stats(v) for r, v in sorted(by_rank.items())},
        "correlation": corr_block(with_gap),
        "by_planes": planes_block,
        "annual_by_planes": summary_block,
        "notes": [
            "load_pm = pour mille de la capacite passagers, lu au premier echantillon C117 apres le depart",
            "rang 2+ = depart suivant un intervalle < mediane/4 de la ligne (meme gare)",
            "mesure descriptive, non causale ; AAAHogEx non mesurable depuis OpexAI",
        ],
    }


def analyze_paths(paths):
    departs, summaries = [], []
    for f in iter_log_files(paths):
        with open_log(f) as fh:
            d, s = parse_log_lines(fh, source=str(f))
        departs.extend(d)
        summaries.extend(s)
    return summarize(departs, summaries)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+", help="journaux .log/.log.gz ou dossiers")
    ap.add_argument("--out", help="fichier JSON de sortie (defaut : stdout)")
    args = ap.parse_args(argv)
    report = analyze_paths(args.paths)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    if report["departs"] == 0 and report["summaries"] == 0:
        print("aucune ligne AIR_PELOTON : DECISION_LOG et -d script=4 actifs ?", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
