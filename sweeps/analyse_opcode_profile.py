#!/usr/bin/env python3
"""Analyse du profil d'opcodes (diag_opcode_profile.py) : agregats annuels par poste.

Lit les journaux `<arm>_<seed>.log` (sortie -d script=4) et rend, par bras et par annee, la
moyenne par graine des postes suivants :
- LOOP_OPS (probe_loop_ops) : boucle principale, budget annuel (ticks IA x 10 000), reliquat
  perdu au Sleep(1) ;
- C39_PASS_CLOCK (probe_scheduler) : taches de file, intentions reactives, travailleurs ;
- SCHED_IDLE (probe_scheduler) : couples (tache, raison, travail) ;
- PROJECTS_COST, AIR_LIGHT, CATALOG_COST_SLICE, SELECTION_LIGHT (catalog_cost_probe).
Les ops suivent OpexOpsMeasureEnd : un tick traverse vaut 10 000, y compris un tick d'attente
d'une commande de construction ; `tk` permet de le reperer.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

OPS_PER_TICK = 10000
START_YEAR = 1970
LINE = re.compile(r"\[script:\d\] \[0\] \[I\] (.*)$")
DATE = re.compile(r"^OPEX (\d{4})-(\d+)-(\d+) (\S+) ?(.*)$")
KV = re.compile(r"(\w+)=(\S+)")


def _num(value):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def parse_log(path: Path):
    out = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    # out[year][section][key] = value
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            m = LINE.search(raw)
            if not m:
                continue
            text = m.group(1)
            if text.startswith("LOOP_OPS "):
                f = {k: _num(v) for k, v in KV.findall(text)}
                year = f["y"]
                post = f["post"]
                if post == "_year":
                    out[year]["loop"]["_ticks"] += f["tk"]
                    continue
                for field in ("n", "ops", "tk"):
                    out[year]["loop"][f"{post}.{field}"] += f[field]
                out[year]["loop"][f"{post}.max"] = max(out[year]["loop"][f"{post}.max"], f["max"])
                continue
            d = DATE.match(text)
            if not d:
                continue
            year, kind, rest = int(d.group(1)), d.group(4), d.group(5)
            f = {k: _num(v) for k, v in KV.findall(rest)}
            if kind == "C39_PASS_CLOCK" and f.get("phase") == "annual":
                # Publie par la tache report au debut de l'annee suivante : year=Y couvre Y-1
                # (la toute premiere publication, debut 1970, couvre quelques jours de 1970).
                y = f["year"] - 1 if f["year"] > START_YEAR else START_YEAR
                key = str(f["key"])
                for field in ("passes", "ops", "ticks", "slice_ops", "slice_ticks"):
                    out[y]["clock"][f"{key}.{field}"] += f[field]
                # Cout de la tache seule, tranche A* rail retiree (ops et ticks).
                task = key.split("|")[0] if key.endswith("slice") else key
                out[y]["task"][f"{task}.ops"] += f["ops"] - f["slice_ops"]
                out[y]["task"][f"{task}.ticks"] += f["ticks"] - f["slice_ticks"]
                out[y]["task"][f"{task}.passes"] += f["passes"]
                out[y]["task"]["_rail_slice.ops"] += f["slice_ops"]
                out[y]["task"]["_rail_slice.ticks"] += f["slice_ticks"]
            elif kind == "SCHED_IDLE":
                key = f"{f['t']}|{f['r']}|w{f['w']}"
                out[year]["idle"][f"{key}.n"] += 1
                out[year]["idle"][f"{key}.ops"] += f["op"]
                out[year]["idle"][f"{key}.tk"] += f["tk"]
            elif kind == "PROJECTS_COST":
                out[year]["projects"]["n"] += 1
                out[year]["projects"]["build_ops"] += f["build_ops"]
                out[year]["projects"]["fleet_ops"] += f["fleet_ops"]
                out[year]["projects"]["regen_ops"] += f["regen_ops"]
                out[year]["projects"][f"regen_ops.{f['regen']}"] += f["regen_ops"]
                out[year]["projects"][f"regen_n.{f['regen']}"] += 1
            elif kind == "AIR_LIGHT" and f.get("edge") == "exit":
                out[year]["air"]["n"] += 1
                out[year]["air"]["ops"] += f["ops"]
                for k, v in f.items():
                    if k.endswith("_ops") and isinstance(v, (int, float)):
                        out[year]["air"][k] += v
            elif kind == "CATALOG_COST_SLICE":
                out[year]["catslice"]["n"] += 1
                out[year]["catslice"]["slice_ops"] += f.get("slice_ops", 0)
                out[year]["catslice"]["evaluated_plans"] += f.get("evaluated_plans", 0)
                out[year]["catslice"]["hits"] += f.get("hits", 0)
                out[year]["catslice"]["recalculated"] += f.get("recalculated", 0)
            elif kind == "SELECTION_LIGHT":
                out[year]["selection"]["n"] += 1
                out[year]["selection"]["ops"] += f["ops"]
                out[year]["selection"][f"ops.{f.get('path')}"] += f["ops"]
                out[year]["selection"]["considered"] += f.get("considered", 0)
    return out


def merge(per_seed):
    """Moyenne par graine : somme puis division par le nombre de graines presentes."""
    total = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    seeds_per_year = defaultdict(int)
    for data in per_seed:
        for year, sections in data.items():
            seeds_per_year[year] += 1
            for section, values in sections.items():
                for key, value in values.items():
                    if key.endswith(".max"):
                        total[year][section][key] = max(total[year][section][key], value)
                    else:
                        total[year][section][key] += value
    for year, sections in total.items():
        n = seeds_per_year[year]
        for values in sections.values():
            for key in list(values):
                if not key.endswith(".max"):
                    values[key] /= n
    return total, dict(seeds_per_year)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("artifacts", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    arms = defaultdict(list)
    for log in sorted(args.artifacts.glob("*.log")):
        arm, seed = log.stem.rsplit("_", 1)
        arms[arm].append((int(seed), parse_log(log)))
    report = {}
    for arm, items in arms.items():
        total, seeds = merge([data for _, data in items])
        report[arm] = {"seeds": [s for s, _ in items], "seeds_per_year": seeds,
                       "years": {str(y): {sec: dict(v) for sec, v in secs.items()}
                                 for y, secs in sorted(total.items())}}
    args.out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"JSON: {args.out}")


if __name__ == "__main__":
    sys.exit(main())
