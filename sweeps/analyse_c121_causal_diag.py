#!/usr/bin/env python3
"""Resume compact des couts et du cold-start d'un diagnostic causal C121."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def _stats(values):
    values = [float(v) for v in values if isinstance(v, (int, float)) and v >= 0]
    if not values:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def analyse(payload):
    rows = payload.get("rows", [])
    builds = [b for row in rows for b in row.get("c121_builds", [])]
    per_engine = []
    for build in builds:
        total = build.get("causal_eval_ops_total")
        count = build.get("causal_engine_evals")
        if isinstance(total, (int, float)) and total >= 0 and isinstance(count, (int, float)) and count > 0:
            per_engine.append(total / count)
    summary = {
        "runs": len(rows),
        "builds": len(builds),
        "project_prepare_ops": _stats([b.get("demand_ops") for b in builds]),
        "project_prepare_ticks": _stats([b.get("demand_ticks") for b in builds]),
        "engine_scan_ops": _stats([b.get("causal_scan_ops") for b in builds]),
        "engine_scan_ticks": _stats([b.get("causal_scan_ticks") for b in builds]),
        "engines_evaluated": _stats([b.get("causal_engine_evals") for b in builds]),
        "engine_eval_ops_total": _stats([b.get("causal_eval_ops_total") for b in builds]),
        "engine_eval_ops_per_engine": _stats(per_engine),
        "choice_mail_known": sum(1 for b in builds if b.get("causal_choice_mail_known") == 1),
        "postbuild_mail_known": sum(1 for b in builds if b.get("postbuild_mail_known") == 1),
        "cold_start_to_known": sum(
            1 for b in builds
            if b.get("causal_choice_mail_known") == 0 and b.get("postbuild_mail_known") == 1
        ),
        "build_rows": [{
            key: b.get(key) for key in (
                "arm", "engine", "pax_cap", "mail_cap",
                "demand_ops", "demand_ticks",
                "causal_scan_ops", "causal_scan_ticks",
                "causal_engine_evals", "causal_engine_known",
                "causal_eval_ops_total", "causal_choice_mail_known",
                "postbuild_mail_known",
            )
        } for b in builds],
        "run_metrics": [{
            key: row.get(key) for key in (
                "seed", "date", "profit_year", "company_value",
                "primary_vehicles", "air_vehicles", "airports", "had_script_error",
            )
        } for row in rows],
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    summary = analyse(payload)
    if args.out:
        args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
