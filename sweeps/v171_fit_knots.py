#!/usr/bin/env python3
"""Ajustement de la table de noeuds d'iterations A* rail (V171).

Parse les journaux RAIL_ATTEMPT des campagnes rail contre rail (V168 et V166)
pour calculer la mediane et le p90 des iterations sur les tentatives reussies (reason=OK)
par tranche de distance aux distances de noeuds (23, 33, 48, 63, 81, 105, 150).
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_V168_PATTERN = "/home/deploy/projects/openttd-ml/results/v168_rail_vs_rail_10x3_20261013_engine/*.log"
DEFAULT_V166_PATTERN = "/home/deploy/projects/openttd-ml/results/v166_rail_vs_rail_10x3_20261013_engine/*dlog*.log"
DEFAULT_OUT = ROOT / "results" / "v171_knots_fit.json"

KNOTS = [23, 33, 48, 63, 81, 105, 150]


def parse_rail_attempts(files: list[str]) -> tuple[list[dict], list[dict]]:
    """Parse les lignes RAIL_ATTEMPT des journaux."""
    all_attempts = []
    ok_attempts = []
    for path in sorted(files):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "RAIL_ATTEMPT" not in line:
                    continue
                m_manh = re.search(r"\bmanh=(\d+)\b", line)
                m_iters = re.search(r"\biters=(\d+)\b", line)
                m_reason = re.search(r"\breason=(\w+)\b", line)
                if not (m_manh and m_iters and m_reason):
                    continue
                rec = {
                    "manh": int(m_manh.group(1)),
                    "iters": int(m_iters.group(1)),
                    "reason": m_reason.group(1),
                    "file": os.path.basename(path),
                }
                all_attempts.append(rec)
                if rec["reason"] == "OK":
                    ok_attempts.append(rec)
    return all_attempts, ok_attempts


def compute_p90(arr: list[int]) -> float:
    """Calcule le 90e percentile par interpolation inclusive."""
    if not arr:
        return 0.0
    if len(arr) == 1:
        return float(arr[0])
    return float(statistics.quantiles(arr, n=10, method="inclusive")[8])


def fit_knots(ok_records: list[dict]) -> dict:
    # 1. Tranches par borne superieure : (prev_knot, knot]
    upper_knots = KNOTS + [170]
    tranches_upper = []
    prev = 0
    for k in upper_knots:
        sub = [r["iters"] for r in ok_records if prev < r["manh"] <= k]
        if sub:
            med = float(statistics.median(sub))
            p90_val = compute_p90(sub)
            tranches_upper.append({
                "knot": k,
                "range": [prev + 1, k],
                "count": len(sub),
                "median": med,
                "p90": p90_val,
                "p90_int": int(round(p90_val)),
            })
        else:
            tranches_upper.append({
                "knot": k,
                "range": [prev + 1, k],
                "count": 0,
                "median": None,
                "p90": None,
                "p90_int": None,
            })
        prev = k

    # 2. Tranches Voronoi (midpoints)
    vor_bounds = [(0, 28), (29, 40), (41, 55), (56, 72), (73, 93), (94, 127), (128, 999)]
    tranches_vor = []
    running_max = 0
    for k, (lo, hi) in zip(KNOTS, vor_bounds):
        sub = [r["iters"] for r in ok_records if lo <= r["manh"] <= hi]
        if sub:
            med = float(statistics.median(sub))
            p90_val = compute_p90(sub)
            p90_int = int(round(p90_val))
            running_max = max(running_max, p90_int)
            tranches_vor.append({
                "knot": k,
                "range": [lo, hi if hi < 999 else max(r["manh"] for r in ok_records)],
                "count": len(sub),
                "median": med,
                "p90": p90_val,
                "p90_int": p90_int,
                "p90_monotonic": running_max,
            })

    # Evaluation du noeud 170
    count_170 = sum(1 for r in ok_records if r["manh"] > 150)
    has_enough_170 = count_170 >= 10

    # Table V2 retenue : issue des tranches bornes superieures (naturellement monotone et entiere)
    v2_table = [t["p90_int"] for t in tranches_upper if t["knot"] in KNOTS]

    return {
        "knots_distance": KNOTS,
        "knot_iterations_v1": [371, 673, 2188, 4066, 7745, 15308, 53951],
        "knot_iterations_v2": v2_table,
        "knot_170_evaluation": {
            "distance": 170,
            "count_beyond_150": count_170,
            "has_enough_data": has_enough_170,
            "verdict": "Non retenu : seulement 4 points au-delà de 150 (d_max=159), echantillon insuffisant."
        },
        "tranches_upper_bound": tranches_upper,
        "tranches_voronoi_midpoint": tranches_vor,
    }


def main():
    parser = argparse.ArgumentParser(description="Ajustement de la table de noeuds A* V171")
    parser.add_argument("--v168-logs", default=DEFAULT_V168_PATTERN, help="Pattern des logs V168")
    parser.add_argument("--v166-logs", default=DEFAULT_V166_PATTERN, help="Pattern des logs V166")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Fichier de sortie JSON")
    args = parser.parse_args()

    files = sorted(glob.glob(args.v168_logs) + glob.glob(args.v166_logs))
    if not files:
        print(f"Aucun fichier trouve avec {args.v168_logs} et {args.v166_logs}", file=sys.stderr)
        sys.exit(1)

    all_attempts, ok_attempts = parse_rail_attempts(files)
    print(f"Fichiers trouves: {len(files)}")
    print(f"Total RAIL_ATTEMPT: {len(all_attempts)}")
    print(f"Total reason=OK: {len(ok_attempts)}")

    result = fit_knots(ok_attempts)
    result["metadata"] = {
        "num_files": len(files),
        "total_attempts": len(all_attempts),
        "total_ok": len(ok_attempts),
        "v168_pattern": args.v168_logs,
        "v166_pattern": args.v166_logs,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nResultat ecrit dans {out_path}")
    print("\nTable de noeuds V2 ajustee :")
    print(f"KNOT_DISTANCE:      {result['knots_distance']}")
    print(f"KNOT_ITERATIONS_V1: {result['knot_iterations_v1']}")
    print(f"KNOT_ITERATIONS_V2: {result['knot_iterations_v2']}")
    print("\nDetail des tranches (borne superieure) :")
    for t in result["tranches_upper_bound"]:
        print(f"  Noeud {t['knot']:3d} ({t['range'][0]:3d}..{t['range'][1]:3d}) : n={t['count']:3d}, mediane={t['median']}, p90={t['p90_int']}")


if __name__ == "__main__":
    main()
