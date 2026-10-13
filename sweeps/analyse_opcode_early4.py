#!/usr/bin/env python3
"""Diagnostic de la charge 1970-1973 à partir des journaux du duel C66.3.

Ne modifie ni les sources de l'IA ni les bundles. Les différentes familles de
sondes sont volontairement NON additionnées entre elles : C39, AIR_LIGHT et
SCHED_IDLE recouvrent la ventilation LOOP_OPS.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import statistics

LINE = re.compile(r"\[script:\d+\] \[0\] \[I\] (.*)$")
AAA_LINE = re.compile(r"\[script:\d+\] \[1\] \[I\] (\d{4})-\d+-\d+ "
                      r"([A-Za-z][A-Za-z0-9_]*) (\d+)\[days\] (\d+)\[ticks\] "
                      r"(\d+)\[ops\] (\d+)\[times\]")
KV = re.compile(r"([\w]+)=([^\s]+)")
DATE = re.compile(r"^OPEX (\d{4})-\d+-\d+ (\S+)\s*(.*)$")
TOP = {
    "events", "save_projection", "station_flux", "c117_sample", "c117_skip",
    "orchestrator", "catalog_continuation", "catalog_continuation_check",
    "rail_throughput", "c67_hook",
}
YEARS = tuple(range(1970, 1974))


def number(value):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def fields(text):
    return {k: number(v) for k, v in KV.findall(text)}


def accumulate(table, year, name, value):
    if year in YEARS:
        table[year][name] += value


def read_log(path):
    families = {name: defaultdict(lambda: defaultdict(float)) for name in
                ("loop", "task", "c39", "air", "catalog", "catalog_slice",
                 "projects", "selection", "aaa_partial",
                 "idle", "slack", "opportunity", "admission")}
    loop = families["loop"]
    counts = defaultdict(int)
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            m = LINE.search(raw)
            if not m:
                aaa = AAA_LINE.search(raw)
                if aaa is not None:
                    year, name, days, ticks, ops, times = aaa.groups()
                    # Composants AAAHogEx ponctuels et parfois imbriques :
                    # aucune somme ne constitue un budget annuel AAA.
                    accumulate(families["aaa_partial"], int(year),
                               name + ".ops", int(ops))
                    accumulate(families["aaa_partial"], int(year),
                               name + ".times", int(times))
                continue
            text = m.group(1)
            if text.startswith("LOOP_OPS "):
                f = fields(text)
                y, post = f.get("y"), f.get("post")
                if y not in YEARS or post is None:
                    continue
                if post == "_year":
                    counts[y] += 1
                    accumulate(loop, y, "ticks", f["tk"])
                else:
                    accumulate(loop, y, post + ".ops", f["ops"])
                    accumulate(loop, y, post + ".n", f["n"])
                    accumulate(loop, y, post + ".ticks", f["tk"])
                continue
            d = DATE.match(text)
            if not d:
                continue
            year, kind, rest = int(d.group(1)), d.group(2), d.group(3)
            f = fields(rest)
            if kind == "C39_PASS_CLOCK" and f.get("phase") == "annual":
                # Émission au report de l'année suivante, sauf premier report 1970.
                y = max(1970, f["year"] - 1)
                key = f["key"]
                for field in ("passes", "ops", "ticks", "slice_ops", "slice_ticks"):
                    accumulate(families["c39"], y, key + "." + field, f.get(field, 0))
                if key.startswith("reactive|") or key.startswith("worker|"):
                    dest = key
                    op = f["ops"]
                else:
                    dest = "task|" + key.split("|")[0]
                    op = f["ops"] - f.get("slice_ops", 0)
                    # tranche A* imbriquee dans une passe (worker C80 OU
                    # chemin historique), ne pas l'appeler « worker ».
                    accumulate(families["task"], y, "rail_astar_slice.ops",
                               f.get("slice_ops", 0))
                accumulate(families["task"], y, dest + ".ops", op)
                accumulate(families["task"], y, dest + ".passes", f.get("passes", 0))
            elif kind == "AIR_LIGHT" and f.get("edge") == "exit":
                accumulate(families["air"], year, "runs", 1)
                accumulate(families["air"], year, "total.ops", f.get("ops", 0))
                for key, value in f.items():
                    if key.endswith("_ops") and isinstance(value, (int, float)):
                        accumulate(families["air"], year, key, value)
            elif kind == "CATALOG_COST":
                accumulate(families["catalog"], year, "runs", 1)
                accumulate(families["catalog"], year, "path." + str(f.get("path")) + ".runs", 1)
                # total_ops est une somme de postes disjoints du catalogue
                # mais les postes C121 plus fins et AIR_LIGHT les recouvrent.
                for key, value in f.items():
                    if key.endswith("_ops") and isinstance(value, (int, float)):
                        accumulate(families["catalog"], year, key, value)
            elif kind == "CATALOG_COST_SLICE":
                accumulate(families["catalog_slice"], year, "runs", 1)
                for key, value in f.items():
                    if isinstance(value, (int, float)):
                        accumulate(families["catalog_slice"], year, key, value)
            elif kind == "PROJECTS_COST":
                accumulate(families["projects"], year, "runs", 1)
                for key in ("build_ops", "fleet_ops", "regen_ops"):
                    accumulate(families["projects"], year, key, f.get(key, 0))
                accumulate(families["projects"], year, "regen." + str(f.get("regen")) + ".ops",
                           f.get("regen_ops", 0))
            elif kind == "SELECTION_LIGHT":
                accumulate(families["selection"], year, "runs", 1)
                accumulate(families["selection"], year, str(f.get("path")) + ".ops",
                           f.get("ops", 0))
                accumulate(families["selection"], year, "total.ops", f.get("ops", 0))
            elif kind == "SCHED_IDLE":
                key = str(f.get("t")) + "|" + str(f.get("r")) + "|w" + str(f.get("w"))
                accumulate(families["idle"], year, key + ".calls", 1)
                accumulate(families["idle"], year, key + ".ops", f.get("op", 0))
            elif kind == "C41_SLACK_LEDGER" and "year" in f:
                y = max(1970, f["year"] - 1)
                key = str(f.get("task"))
                for field in ("calls", "ops", "slack_ops_available", "slack_ops_used",
                              "slack_ops_left"):
                    accumulate(families["slack"], y, key + "." + field, f.get(field, 0))
            elif kind == "C41_OPPORTUNITY_LEDGER" and "year" in f:
                y = max(1970, f["year"] - 1)
                key = str(f.get("layer"))
                for field in ("observations", "stale_days_sum", "slack_ops_left"):
                    accumulate(families["opportunity"], y, key + "." + field, f.get(field, 0))
            elif kind == "C41_ADMISSION_LEDGER" and "year" in f:
                y = max(1970, f["year"] - 1)
                key = str(f.get("layer"))
                for field in ("checks", "fits"):
                    accumulate(families["admission"], y, key + "." + field, f.get(field, 0))
    result = {k: {str(y): dict(records) for y, records in table.items()}
              for k, table in families.items()}
    for year in YEARS:
        raw = loop[year]
        total = sum(value for key, value in raw.items()
                    if key.endswith(".ops") and key.split(".")[0] in TOP)
        raw["top_executed.ops"] = total
        raw["top_unexplained.ops"] = (
            raw.get("ticks", 0) * 10000 - total - raw.get("sleep_left.ops", 0)
        )
    result["loop"] = {str(y): dict(table) for y, table in loop.items()}
    result["coverage"] = {str(y): counts[y] for y in YEARS}
    return result


def average(samples):
    names = ("loop", "task", "c39", "air", "catalog", "catalog_slice",
             "projects", "selection", "aaa_partial", "idle", "slack",
             "opportunity", "admission")
    report = {}
    for name in names:
        report[name] = {}
        for year in YEARS:
            keys = set().union(*(sample[name].get(str(year), {}).keys() for sample in samples))
            report[name][str(year)] = {
                key: round(statistics.mean(s[name].get(str(year), {}).get(key, 0)
                                           for s in samples), 3)
                for key in sorted(keys)
            }
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("engine", type=Path, help="Répertoire *_engine des journaux C66.3")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--label", default="diagnostic")
    p.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    args = p.parse_args()
    samples = {}
    for seed in args.seeds:
        hits = list(args.engine.glob(f"*seed{seed}_r0.log"))
        if len(hits) != 1:
            p.error(f"seed={seed}: attendu un seul journal, trouvé {len(hits)}")
        samples[str(seed)] = read_log(hits[0])
        coverage = samples[str(seed)]["coverage"]
        if any(coverage[str(year)] != 1 for year in YEARS):
            p.error(f"LOOP_OPS incomplet seed={seed} : {coverage}")
    mean = average(list(samples.values()))
    result = {"label": args.label, "engine": args.engine.as_posix(),
              "seeds": args.seeds, "years": YEARS, "mean": mean, "by_seed": samples,
              "notes": [
                  "Budget brut = LOOP_OPS._year.ticks*10000 ; sleep_left n'est pas une dépense.",
                  "top_executed exclut tg_* (sous-mesures imbriquées et compteurs).",
                  "C39, AIR_LIGHT, PROJECTS_COST, SELECTION_LIGHT, SCHED_IDLE ne s'additionnent PAS à LOOP_OPS.",
                  "AAAHogEx PerformanceCounter = sous-postes partiels, imbriques, non additionnables en budget global.",
                  "C39 est décalé au précédent exercice comptable avec report initial de 1970.",
                  "C39 et SCHED_IDLE ne sont pas une preuve de rentabilité, ni de capacité worker disponible.",
              ]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    for year in YEARS:
        r = mean["loop"][str(year)]
        print(f"{args.label} {year}: ticks={r.get('ticks', 0):,.0f} "
              f"budget={r.get('ticks', 0)*10000/1e6:.3f}M "
              f"top={r.get('top_executed.ops', 0)/1e6:.3f}M "
              f"sleep_left={r.get('sleep_left.ops', 0)/1e6:.3f}M "
              f"unexplained={r.get('top_unexplained.ops', 0)/1e6:.3f}M")
    print(args.out)


if __name__ == "__main__":
    main()
