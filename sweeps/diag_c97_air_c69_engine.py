#!/usr/bin/env python3
"""C97 : diagnostic passif du choix moteur AIR par argmax direct moteur x n."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

DEFAULT_SEEDS = (42, 100, 999)
TAG_RE = re.compile(r"C97_ENGINE\s+(.*)")

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


def parse_value(value: str):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def parse_fields(text: str) -> dict:
    fields = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        fields[key] = parse_value(value)
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


def stats(values):
    values = [float(v) for v in values if isinstance(v, (int, float))]
    if not values:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 6),
        "median": round(statistics.median(values), 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
    }


def pct(n, d):
    return round(100.0 * n / d, 3) if d else None


def unique_events(rows):
    unique = {}
    for row in rows:
        for event in row.get("events", []):
            key = (
                event.get("seed"), event.get("route"), event.get("src"), event.get("dst"),
                event.get("airport_type"), event.get("default_engine"), event.get("c97_engine"),
                event.get("c97_n"), event.get("K_dec"), event.get("default_P"), event.get("c97_P"),
                event.get("default_C"), event.get("c97_C"),
            )
            unique[key] = event
    return list(unique.values())


def kdec_buckets(events):
    buckets = defaultdict(list)
    for event in events:
        k = event.get("K_dec")
        c = event.get("default_C")
        if not isinstance(k, (int, float)) or not isinstance(c, (int, float)) or c <= 0:
            label = "unknown"
        else:
            ratio = k / c
            if ratio <= 0:
                label = "K=0"
            elif ratio < 0.5:
                label = "0<K<0.5C"
            elif ratio < 1.0:
                label = "0.5C<=K<C"
            elif ratio < 2.0:
                label = "C<=K<2C"
            else:
                label = "K>=2C"
        buckets[label].append(event)
    return {
        label: {
            "events": len(group),
            "disagree": sum(1 for e in group if e.get("disagree") == 1),
            "disagree_pct": pct(sum(1 for e in group if e.get("disagree") == 1), len(group)),
            "c97_n": dict(sorted(Counter(str(e.get("c97_n")) for e in group).items())),
        }
        for label, group in sorted(buckets.items())
    }


def summarize(rows):
    events = unique_events(rows)
    disagree = [e for e in events if e.get("disagree") == 1]
    replacements = Counter(
        f"{e.get('default_name', e.get('default_engine'))}->{e.get('c97_name', e.get('c97_engine'))}"
        for e in disagree
    )
    smaller = [e for e in disagree if e.get("c97_capacity", 0) < e.get("default_capacity", 0)]
    larger = [e for e in disagree if e.get("c97_capacity", 0) > e.get("default_capacity", 0)]
    cheaper = [e for e in disagree if e.get("c97_price", 0) < e.get("default_price", 0)]
    dearer = [e for e in disagree if e.get("c97_price", 0) > e.get("default_price", 0)]
    pp_deltas = []
    for e in disagree:
        dn = e.get("default_n", 1)
        cn = e.get("c97_n", 0)
        dp = e.get("default_P")
        cp = e.get("c97_P")
        if isinstance(dn, (int, float)) and dn > 0 and isinstance(cn, (int, float)) and cn > 0 \
                and isinstance(dp, (int, float)) and isinstance(cp, (int, float)):
            pp_deltas.append(cp / cn - dp / dn)
    return {
        "events": len(events),
        "disagree": len(disagree),
        "disagree_pct": pct(len(disagree), len(events)),
        "c97_n_distribution": dict(sorted(Counter(str(e.get("c97_n")) for e in events).items())),
        "c97_n_distribution_disagree": dict(sorted(Counter(str(e.get("c97_n")) for e in disagree).items())),
        "engine_replacements": dict(replacements.most_common()),
        "predicted_profit_delta": stats([e.get("c97_P", 0) - e.get("default_P", 0) for e in disagree]),
        "calibrated_profit_delta": stats([e.get("c97_P_cal", 0) - e.get("default_P_cal", 0) for e in disagree]),
        "portfolio_capital_delta": stats([e.get("c97_C", 0) - e.get("default_C", 0) for e in disagree]),
        "c69_score_delta": stats([e.get("c97_score", 0) - e.get("default_score", 0) for e in disagree]),
        "predicted_profit_per_plane_delta": stats(pp_deltas),
        "profit_per_plane_higher": sum(1 for d in pp_deltas if d > 0),
        "profit_per_plane_higher_pct": pct(sum(1 for d in pp_deltas if d > 0), len(pp_deltas)),
        "smaller_capacity": len(smaller),
        "smaller_capacity_pct": pct(len(smaller), len(disagree)),
        "larger_capacity": len(larger),
        "larger_capacity_pct": pct(len(larger), len(disagree)),
        "cheaper": len(cheaper),
        "cheaper_pct": pct(len(cheaper), len(disagree)),
        "dearer": len(dearer),
        "dearer_pct": pct(len(dearer), len(disagree)),
        "K_dec": stats([e.get("K_dec") for e in events]),
        "by_K_dec_vs_default_C": kdec_buckets(events),
        "by_seed": {
            str(seed): {
                "events": sum(1 for e in events if e.get("seed") == seed),
                "disagree": sum(1 for e in disagree if e.get("seed") == seed),
            }
            for seed in sorted({e.get("seed") for e in events if isinstance(e.get("seed"), int)})
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results" / "diag_c97_air_c69_engine_3x3.json")
    args = parser.parse_args()
    if args.max_workers < 1 or args.max_workers > 10:
        parser.error("--max-workers doit etre entre 1 et 10")

    enable_savegame_cleanup()
    opex = local_folder(
        str(ROOT / "ai" / "OpexAI"), "OpexAI", (("c97_air_c69_engine_probe", 1),)
    )
    cfg = make_cfg(1970)
    experiments = [
        {
            "bench_context": "solo",
            "bench_arm": "OpexAI[c97_air_c69_engine_probe=1]",
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
    summary = summarize(rows)
    payload = {
        "purpose": "C97 passive engine x fleet-depth exposure diagnostic; not adoption evidence",
        "years": args.years,
        "seeds": args.seeds,
        "settings": {"c97_air_c69_engine_probe": 1},
        "rows": rows,
        "summary": summary,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Sortie: {args.out}")


if __name__ == "__main__":
    main()
