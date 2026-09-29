#!/usr/bin/env python3
"""C105: realised AIR engine/expansion diagnostic on one losing and one winning seed.

Runs the current default and C105 in the same OpexAI-vs-AAAHogEx duel design.
The result is diagnostic only: year-end savegames are decoded to expose the
realised Opex aircraft engines, build years, per-plane prior-year profit and AIR
services.  The default seeds deliberately bracket the 5x6 result: seed 100 was
the clearest C105 contraction and seed 5678 the clearest expansion.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
import sys

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from openttdlab import bananas_ai_library, local_folder, run_experiments
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg
from diag_c98_vs_aaa_engines import aircraft_rows, air_lines


DEFAULT_SEEDS = (100, 5678)
SETTING = "c105_air_replay_choice_physical_economics"


def keep(row):
    # Windows multiprocessing: import worker dependencies inside the callback
    # instead of relying on globals captured by openttdlab's serializer.
    from diag_c98_vs_aaa_engines import aircraft_rows as _aircraft_rows, air_lines as _air_lines

    date = str(row.get("date", ""))
    # Keep the worker callback self-contained: openttdlab serialises this
    # function for multiprocessing and does not reliably carry module globals
    # such as `re` on this Windows/Python combination.
    if len(date) < 7 or date[4:7] != "-12":
        return ()
    year = int(date[:4])
    chunks = row.get("chunks") or {}
    experiment = row.get("experiment") or {}
    companies = {}
    for owner in (0, 1):
        aircraft = _aircraft_rows(chunks, owner, year)
        companies[str(owner)] = {
            "aircraft": aircraft,
            "lines": _air_lines(chunks, owner, aircraft),
        }
    return ({
        "policy": experiment.get("diag_policy"),
        "seed": experiment.get("seed"),
        "year": year,
        "date": date,
        "companies": companies,
    },)


def _mean(values):
    vals = [float(v) for v in values if isinstance(v, (int, float))]
    return statistics.mean(vals) if vals else None


def _engine_mix(aircraft, full_prior_year=False):
    rows = [r for r in aircraft if not full_prior_year or r.get("full_prior_year")]
    counts = Counter(r.get("engine_label") for r in rows)
    profits = defaultdict(list)
    for row in rows:
        profits[row.get("engine_label")].append(row.get("profit_last_year_gbp"))
    return {
        engine: {
            "count": count,
            "profit_last_year_per_plane_gbp": _mean(profits[engine]),
        }
        for engine, count in counts.most_common()
    }


def _service_mix(lines):
    services = {}
    for line in lines:
        key = line.get("service_key")
        if not key:
            continue
        services[key] = {
            "market_key": line.get("market_key"),
            "vehicles": int(line.get("vehicles") or 0),
            "profit_last_year_gbp": float(line.get("profit_last_year_gbp") or 0.0),
            "full_year_vehicles": int(line.get("full_year_vehicles") or 0),
            "full_year_profit_last_year_gbp": float(line.get("full_year_profit_last_year_gbp") or 0.0),
            "full_year_engines": line.get("full_year_engines") or {},
        }
    return services


def summarize(rows):
    snapshots = {}
    latest = {}
    for row in rows:
        key = (row.get("policy"), row.get("seed"), row.get("year"))
        snapshots[key] = row
        latest_key = (row.get("policy"), row.get("seed"))
        if latest_key not in latest or row.get("date", "") > latest[latest_key].get("date", ""):
            latest[latest_key] = row

    per_seed = {}
    for seed in sorted({r.get("seed") for r in rows if r.get("seed") is not None}):
        seed_out = {}
        for policy in ("reference", "c105"):
            row = latest.get((policy, seed))
            if row is None:
                seed_out[policy] = None
                continue
            aircraft = row["companies"]["0"]["aircraft"]
            full = [r for r in aircraft if r.get("full_prior_year")]
            seed_out[policy] = {
                "date": row.get("date"),
                "aircraft": len(aircraft),
                "full_prior_year_aircraft": len(full),
                "profit_last_year_per_plane_gbp": _mean(r.get("profit_last_year_gbp") for r in full),
                "book_value_per_aircraft": _mean(r.get("book_value") for r in aircraft),
                "build_years": dict(sorted(Counter(r.get("build_year") for r in aircraft).items())),
                "engine_mix_all": _engine_mix(aircraft),
                "engine_mix_full_prior_year": _engine_mix(aircraft, full_prior_year=True),
                "services": _service_mix(row["companies"]["0"]["lines"]),
            }
        per_seed[str(seed)] = seed_out

    yearly = {}
    for (policy, seed, year), row in sorted(snapshots.items()):
        aircraft = row["companies"]["0"]["aircraft"]
        yearly.setdefault(str(seed), {}).setdefault(str(year), {})[policy] = {
            "aircraft": len(aircraft),
            "engines": dict(Counter(r.get("engine_label") for r in aircraft)),
            "build_years": dict(sorted(Counter(r.get("build_year") for r in aircraft).items())),
        }
    return {"per_seed_final": per_seed, "yearly_opex": yearly}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=4)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "results" / "diag_c105_engine_mix_2x4_20260927.json",
    )
    args = parser.parse_args()
    if not 1 <= args.max_workers <= 3:
        parser.error("--max-workers doit etre entre 1 et 3")

    enable_savegame_cleanup()
    opex_dir = str(ROOT / "ai" / "OpexAI")
    aaa_dir = str(ROOT / "ai" / "AAAHogEx-115")
    arms = {
        "reference": local_folder(opex_dir, "OpexAI", ((SETTING, 0),)),
        "c105": local_folder(opex_dir, "OpexAI", ((SETTING, 1),)),
    }
    aaa = local_folder(aaa_dir, "AAAHogEx", ())
    cfg = make_cfg(1970)
    experiments = []
    for policy, opex in arms.items():
        for seed in args.seeds:
            experiments.append({
                "bench_context": "duel",
                "bench_arm": f"c105-engine-mix-{policy}",
                "diag_policy": policy,
                "seed": seed,
                "days": 365 * args.years,
                "openttd_config": cfg,
                "ais": (opex, aaa),
            })

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
        "purpose": "C105 realised engine mix and early AIR expansion: losing vs winning seed",
        "years": args.years,
        "seeds": args.seeds,
        "policies": {"reference": {SETTING: 0}, "c105": {SETTING: 1}},
        "rows": rows,
        "summary": summarize(rows),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    print(f"Sortie: {args.out}")


if __name__ == "__main__":
    main()
