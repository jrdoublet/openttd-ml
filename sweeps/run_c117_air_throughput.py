#!/usr/bin/env python3
"""C117 : diagnostic solo passif du debit AIR reel."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import importlib
import json
from pathlib import Path
import re
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg
from diag_c117_air_throughput import analyse

DEFAULT_SEEDS = (42, 100, 999, 1234, 5678)
TAG_RE = re.compile(r"C117_AIR_THROUGHPUT\s+(.*)")

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


if not getattr(openttdlab.subprocess.check_output, "_c117_script_debug", False):
    _check_output_with_script_debug._c117_script_debug = True
    openttdlab.subprocess.check_output = _check_output_with_script_debug


def parse_value(value: str):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def parse_fields(text: str):
    fields = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        fields[key] = parse_value(value)
    return fields


def keep(row):
    experiment = row.get("experiment", {})
    seed = experiment.get("seed")
    date_s = str(row.get("date", ""))
    days = int(experiment.get("days", 0) or 0)
    final_date = date(1970, 1, 1) + timedelta(days=days)
    try:
        row_date = date.fromisoformat(date_s[:10])
    except ValueError:
        return ()
    # OpenTTDLab publie des checkpoints mensuels. Pour un run de 2190 jours,
    # l'annee bissextile 1972 place la fin au 1975-12-31 et le dernier
    # checkpoint utile au 1975-12-01. Garder seulement la queue evite de
    # transporter toutes les sorties AILog cumulatives en memoire.
    if row_date < final_date - timedelta(days=31) or row_date > final_date:
        return ()
    output = row.get("output", "") or ""
    events = [parse_fields(fields) for fields in TAG_RE.findall(output)]
    return ({
        "seed": seed,
        "date": date_s,
        "events": events,
        "event_count": len(events),
        "had_script_error": "Script died unexpectedly" in output or "SCRIPT ERROR" in output,
    },)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "results" / "c117_air_throughput_5x6_20260927.json",
    )
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error("--workers doit etre entre 1 et 6")

    enable_savegame_cleanup()
    settings = (
        ("c115_air_c100_capital_replay", 1),
        ("c117_air_throughput_probe", 1),
        ("b9_air_demand_shadow", 1),
    )
    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", settings)
    cfg = make_cfg(1970)
    experiments = [
        {
            "bench_context": "solo",
            "bench_arm": "OpexAI[C115=1,c117_air_throughput_probe=1,b9_air_demand_shadow=1]",
            "seed": seed,
            "days": 365 * args.years,
            "openttd_config": cfg,
            "ais": (opex,),
        }
        for seed in args.seeds
    ]
    processor_module = importlib.import_module("run_c117_air_throughput")
    result_processor = processor_module.keep
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=args.workers,
        result_processor=result_processor,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    checkpoint_rows = list(rows)
    latest_by_seed = {}
    for row in checkpoint_rows:
        seed = row.get("seed")
        if seed is None:
            continue
        previous = latest_by_seed.get(seed)
        if previous is None or row.get("date", "") > previous.get("date", ""):
            latest_by_seed[seed] = row
    rows = [latest_by_seed[seed] for seed in args.seeds if seed in latest_by_seed]
    analysis = analyse(rows)
    observed_seeds = sorted({
        row.get("seed") for row in rows if row.get("seed") is not None
    })
    failed = []
    for seed in args.seeds:
        seed_rows = [row for row in rows if row.get("seed") == seed]
        if not seed_rows:
            failed.append({"seed": seed, "reason": "missing"})
        elif any(row.get("had_script_error") for row in seed_rows):
            failed.append({"seed": seed, "reason": "script_error"})
        elif not any(row.get("event_count", 0) > 0 for row in seed_rows):
            failed.append({"seed": seed, "reason": "no_c117_events"})
    payload = {
        "campaign_id": args.out.stem,
        "purpose": "C117 descriptive/passive AIR demand-to-throughput diagnostic; not causal adoption evidence",
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "workers": args.workers,
        "settings": dict(settings),
        "health": {
            "expected_runs": len(args.seeds),
            "observed_runs": len(observed_seeds),
            "checkpoint_rows": len(checkpoint_rows),
            "failed_runs": failed,
            "all_runs_healthy": len(observed_seeds) == len(args.seeds) and not failed,
        },
        "rows": rows,
        "analysis": analysis,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "health": payload["health"],
        "event_count": analysis["event_count"],
        "analysis_event_count": analysis["analysis_event_count"],
        "line_count": analysis["line_count"],
        "overall": analysis["overall"],
        "ramp": analysis["ramp"],
    }, indent=2))
    print(f"Sortie: {args.out}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
