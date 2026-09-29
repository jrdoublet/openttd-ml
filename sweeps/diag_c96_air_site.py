#!/usr/bin/env python3
"""C96 : diagnostic court du meilleur placement AIR parmi quelques sites valides.

Capture ``C96_SITE`` via ``-d script=4``. Le diagnostic active uniquement
``c96_air_site_catchment=1`` ; il ne modifie ni la demande V93 ni C68.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

DEFAULT_SEEDS = (42, 100, 999)
TAG_RE = re.compile(r"C96_SITE\s+(.*)")

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug


def parse_fields(text: str) -> dict:
    fields = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        try:
            fields[key] = int(value)
        except ValueError:
            fields[key] = value
    return fields


def keep(row):
    seed = row.get("experiment", {}).get("seed")
    events = []
    for fields_s in TAG_RE.findall(row.get("output", "") or ""):
        event = parse_fields(fields_s)
        event["seed"] = seed
        events.append(event)
    if not events:
        return ()
    return ({"seed": seed, "date": str(row.get("date", "")), "events": events},)


def _stats(values):
    values = [value for value in values if isinstance(value, (int, float))]
    if not values:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 6),
        "median": round(statistics.median(values), 6),
        "min": min(values),
        "max": max(values),
    }


def summarize(rows):
    unique = {}
    for row in rows:
        for event in row.get("events", []):
            key = (
                event.get("seed"), event.get("town"), event.get("first"), event.get("best"),
                event.get("first_score"), event.get("best_score"), event.get("valid"),
                event.get("first_ring"), event.get("best_ring"), event.get("probes"),
            )
            unique[key] = event
    events = list(unique.values())
    changed = [event for event in events if event.get("best") != event.get("first")]
    positive = [event for event in events if event.get("gain", 0) > 0]
    farther = [event for event in events
               if event.get("best_dist", 0) > event.get("first_dist", 0)]
    closer = [event for event in events
              if event.get("best_dist", 0) < event.get("first_dist", 0)]
    return {
        "events": len(events),
        "changed_anchor": len(changed),
        "changed_anchor_pct": round(100.0 * len(changed) / len(events), 3) if events else None,
        "positive_gain": len(positive),
        "positive_gain_pct": round(100.0 * len(positive) / len(events), 3) if events else None,
        "best_farther": len(farther),
        "best_closer": len(closer),
        "first_score": _stats([event.get("first_score") for event in events]),
        "best_score": _stats([event.get("best_score") for event in events]),
        "score_gain": _stats([event.get("gain") for event in events]),
        "first_distance": _stats([event.get("first_dist") for event in events]),
        "best_distance": _stats([event.get("best_dist") for event in events]),
        "valid_sites_examined": _stats([event.get("valid") for event in events]),
        "physical_probes": _stats([event.get("probes") for event in events]),
        "ring_delta": _stats([
            event.get("best_ring") - event.get("first_ring")
            for event in events
            if isinstance(event.get("best_ring"), int) and isinstance(event.get("first_ring"), int)
        ]),
        "by_seed": {
            str(seed): sum(1 for event in events if event.get("seed") == seed)
            for seed in sorted({event.get("seed") for event in events if isinstance(event.get("seed"), int)})
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results" / "diag_c96_air_site_3x3.json")
    args = parser.parse_args()

    enable_savegame_cleanup()
    opex = local_folder(
        str(ROOT / "ai" / "OpexAI"), "OpexAI", (("c96_air_site_catchment", 1),)
    )
    cfg = make_cfg(1970)
    experiments = [
        {
            "bench_context": "solo",
            "bench_arm": "OpexAI[c96_air_site_catchment=1]",
            "seed": seed,
            "days": 365 * args.years,
            "openttd_config": cfg,
            "ais": (opex,),
        }
        for seed in args.seeds
    ]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=args.max_workers,
        result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    payload = {
        "purpose": "C96 mechanism-only site selection diagnostic; not adoption evidence",
        "years": args.years,
        "seeds": args.seeds,
        "settings": {"c96_air_site_catchment": 1},
        "rows": rows,
        "summary": summarize(rows),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    print(f"Sortie: {args.out}")


if __name__ == "__main__":
    main()
