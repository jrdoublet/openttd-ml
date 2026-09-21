"""5x6 apparié AIR equipment=1 contre la baseline, en solo et contre AAAHogEx.

Deux lectures sont produites sur exactement les mêmes graines :

* ``solo`` : OpexAI est seul sur la carte. Métrique primaire = profit annuel OpexAI.
* ``duel`` : OpexAI et AAAHogEx jouent dans la même partie. Métrique primaire =
  profit annuel OpexAI / profit annuel AAAHogEx.

Le bras ``baseline`` fige explicitement C68 (route_plane_selection=1,
best_equipment=0, capital_frontier=0). Le bras ``equipment1`` ne change que
``air_best_equipment`` à 1. Ainsi le diagnostic reste interprétable si les
defaults de info.nut évoluent plus tard.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys

from openttdlab import bananas_ai_library, local_folder, run_experiments


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (  # noqa: E402
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    enable_savegame_cleanup,
    make_cfg,
    year_profit,
)


STARTING_YEAR = 1970
DEFAULT_YEARS = 6
DEFAULT_SEEDS = (42, 100, 999, 1234, 5678)
AAAHOGEX_DIR = "AAAHogEx-115"

BASELINE_SETTINGS = (
    ("air_route_plane_selection", 1),
    ("air_best_equipment", 0),
    ("air_capital_frontier", 0),
    ("air_capital_frontier_probe", 0),
)
EQUIPMENT1_SETTINGS = (
    ("air_route_plane_selection", 1),
    ("air_best_equipment", 1),
    ("air_capital_frontier", 0),
    ("air_capital_frontier_probe", 0),
)


def _player(chunks, owner):
    players = chunks.get("PLYR") or {}
    return players.get(owner) or players.get(str(owner)) or {}


def _profit_year(chunks, owner):
    player = _player(chunks, owner)
    closed = player.get("old_economy") or []
    value = year_profit(closed) if closed else 0
    return value if value is not None else 0


def keep(row):
    """Conserver uniquement les métriques nécessaires, avec le tuple canonique."""
    chunks = row.get("chunks", {})
    context = row["experiment"]["bench_context"]
    opex_profit = _profit_year(chunks, 0)
    aaa_profit = _profit_year(chunks, 1) if context == "duel" else None
    ratio = None
    if aaa_profit not in (None, 0):
        ratio = opex_profit / aaa_profit
    return ({
        "context": context,
        "arm": row["experiment"]["bench_arm"],
        "seed": row["experiment"]["seed"],
        "date": str(row.get("date", "")),
        "opex_profit_year": opex_profit,
        "aaahogex_profit_year": aaa_profit,
        "opex_to_aaahogex_profit_ratio": ratio,
    },)


def _latest_by_run(rows):
    latest = {}
    for row in rows:
        key = (row["context"], row["arm"], row["seed"])
        previous = latest.get(key)
        if previous is None or row["date"] > previous["date"]:
            latest[key] = row
    return latest


def _mean(values):
    values = [value for value in values if value is not None]
    return statistics.mean(values) if values else None


def _median(values):
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def _paired_outcome(differences):
    return {
        "wins": sum(value > 0 for value in differences),
        "ties": sum(value == 0 for value in differences),
        "losses": sum(value < 0 for value in differences),
    }


def summarize(latest, seeds):
    solo_rows = []
    duel_rows = []

    for seed in seeds:
        solo_base = latest[("solo", "baseline", seed)]
        solo_eq = latest[("solo", "equipment1", seed)]
        base_profit = solo_base["opex_profit_year"]
        eq_profit = solo_eq["opex_profit_year"]
        solo_rows.append({
            "seed": seed,
            "baseline_profit": base_profit,
            "equipment1_profit": eq_profit,
            "paired_profit_delta": eq_profit - base_profit,
            "paired_profit_ratio": (eq_profit / base_profit) if base_profit != 0 else None,
        })

        duel_base = latest[("duel", "baseline", seed)]
        duel_eq = latest[("duel", "equipment1", seed)]
        base_ratio = duel_base["opex_to_aaahogex_profit_ratio"]
        eq_ratio = duel_eq["opex_to_aaahogex_profit_ratio"]
        duel_rows.append({
            "seed": seed,
            "baseline_opex_profit": duel_base["opex_profit_year"],
            "baseline_aaahogex_profit": duel_base["aaahogex_profit_year"],
            "baseline_profit_ratio": base_ratio,
            "equipment1_opex_profit": duel_eq["opex_profit_year"],
            "equipment1_aaahogex_profit": duel_eq["aaahogex_profit_year"],
            "equipment1_profit_ratio": eq_ratio,
            "paired_ratio_delta": (
                eq_ratio - base_ratio if eq_ratio is not None and base_ratio is not None else None
            ),
            "paired_ratio_ratio": (
                eq_ratio / base_ratio
                if eq_ratio is not None and base_ratio not in (None, 0)
                else None
            ),
        })

    solo_deltas = [row["paired_profit_delta"] for row in solo_rows]
    duel_deltas = [row["paired_ratio_delta"] for row in duel_rows if row["paired_ratio_delta"] is not None]

    return {
        "solo": {
            "metric": "opex_profit_year",
            "per_seed": solo_rows,
            "baseline_mean": _mean([row["baseline_profit"] for row in solo_rows]),
            "equipment1_mean": _mean([row["equipment1_profit"] for row in solo_rows]),
            "baseline_median": _median([row["baseline_profit"] for row in solo_rows]),
            "equipment1_median": _median([row["equipment1_profit"] for row in solo_rows]),
            "paired_delta_mean": _mean(solo_deltas),
            "paired_delta_median": _median(solo_deltas),
            "paired_outcome": _paired_outcome(solo_deltas),
        },
        "duel": {
            "metric": "opex_profit_year / aaahogex_profit_year",
            "per_seed": duel_rows,
            "baseline_ratio_mean": _mean([row["baseline_profit_ratio"] for row in duel_rows]),
            "equipment1_ratio_mean": _mean([row["equipment1_profit_ratio"] for row in duel_rows]),
            "baseline_ratio_median": _median([row["baseline_profit_ratio"] for row in duel_rows]),
            "equipment1_ratio_median": _median([row["equipment1_profit_ratio"] for row in duel_rows]),
            "paired_ratio_delta_mean": _mean(duel_deltas),
            "paired_ratio_delta_median": _median(duel_deltas),
            "paired_outcome": _paired_outcome(duel_deltas),
            "baseline_opex_profit_mean": _mean([row["baseline_opex_profit"] for row in duel_rows]),
            "baseline_aaahogex_profit_mean": _mean([row["baseline_aaahogex_profit"] for row in duel_rows]),
            "equipment1_opex_profit_mean": _mean([row["equipment1_opex_profit"] for row in duel_rows]),
            "equipment1_aaahogex_profit_mean": _mean([row["equipment1_aaahogex_profit"] for row in duel_rows]),
        },
    }


def _print_summary(summary):
    print("\n=== SOLO : métrique = profit annuel OpexAI ===")
    print("seed | baseline | equipment=1 | delta | ratio")
    for row in summary["solo"]["per_seed"]:
        ratio = row["paired_profit_ratio"]
        ratio_text = "n/a" if ratio is None else f"{ratio:.4f}"
        print(
            f"{row['seed']:>4} | {row['baseline_profit']:>10.0f} | "
            f"{row['equipment1_profit']:>11.0f} | {row['paired_profit_delta']:>+10.0f} | {ratio_text}"
        )
    solo = summary["solo"]
    print(
        "mean | "
        f"{solo['baseline_mean']:.1f} -> {solo['equipment1_mean']:.1f} "
        f"delta={solo['paired_delta_mean']:+.1f} "
        f"W/T/L={solo['paired_outcome']['wins']}/{solo['paired_outcome']['ties']}/{solo['paired_outcome']['losses']}"
    )

    print("\n=== DUEL PARTAGÉ : métrique = profit OpexAI / profit AAAHogEx ===")
    print("seed | base Opex | base AAA | base ratio | eq1 Opex | eq1 AAA | eq1 ratio | delta ratio")
    for row in summary["duel"]["per_seed"]:
        base_ratio = row["baseline_profit_ratio"]
        eq_ratio = row["equipment1_profit_ratio"]
        delta = row["paired_ratio_delta"]
        print(
            f"{row['seed']:>4} | {row['baseline_opex_profit']:>9.0f} | {row['baseline_aaahogex_profit']:>8.0f} | "
            f"{('n/a' if base_ratio is None else f'{base_ratio:.4f}'):>10} | "
            f"{row['equipment1_opex_profit']:>8.0f} | {row['equipment1_aaahogex_profit']:>7.0f} | "
            f"{('n/a' if eq_ratio is None else f'{eq_ratio:.4f}'):>9} | "
            f"{('n/a' if delta is None else f'{delta:+.4f}'):>11}"
        )
    duel = summary["duel"]
    print(
        "mean ratio | "
        f"{duel['baseline_ratio_mean']:.4f} -> {duel['equipment1_ratio_mean']:.4f} "
        f"delta={duel['paired_ratio_delta_mean']:+.4f} "
        f"W/T/L={duel['paired_outcome']['wins']}/{duel['paired_outcome']['ties']}/{duel['paired_outcome']['losses']}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results" / "diag_air_equipment_paired_solo_duel_5x6.json",
    )
    args = parser.parse_args()

    enable_savegame_cleanup()

    opex_baseline = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", BASELINE_SETTINGS)
    opex_equipment1 = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", EQUIPMENT1_SETTINGS)
    aaahogex = local_folder(str(ROOT / "ai" / AAAHOGEX_DIR), "AAAHogEx", ())
    cfg = make_cfg(STARTING_YEAR)
    days = 365 * args.years

    experiments = []
    for arm, opex in (("baseline", opex_baseline), ("equipment1", opex_equipment1)):
        for seed in args.seeds:
            experiments.append({
                "bench_context": "solo",
                "bench_arm": arm,
                "seed": seed,
                "days": days,
                "openttd_config": cfg,
                "ais": (opex,),
            })
            experiments.append({
                "bench_context": "duel",
                "bench_arm": arm,
                "seed": seed,
                "days": days,
                "openttd_config": cfg,
                "ais": (opex, aaahogex),
            })

    print(
        f"=== AIR equipment=1 vs baseline : {len(args.seeds)} graines x {args.years} ans, "
        "solo + duel AAAHogEx ==="
    )
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=args.workers,
        result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    latest = _latest_by_run(rows)
    expected = 2 * 2 * len(args.seeds)
    if len(latest) != expected:
        raise RuntimeError(f"runs finaux incomplets: {len(latest)}/{expected}")

    summary = summarize(latest, args.seeds)
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "starting_year": STARTING_YEAR,
        "years": args.years,
        "seeds": args.seeds,
        "baseline_settings": dict(BASELINE_SETTINGS),
        "equipment1_settings": dict(EQUIPMENT1_SETTINGS),
        "contexts": {
            "solo": {"ais": ["OpexAI"], "primary_metric": "opex_profit_year"},
            "duel": {
                "ais": ["OpexAI", "AAAHogEx"],
                "primary_metric": "opex_profit_year / aaahogex_profit_year",
            },
        },
        "summary": summary,
        "final_runs": [latest[key] for key in sorted(latest)],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    jsonl_path = args.out.with_suffix(".jsonl")
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")

    _print_summary(summary)
    print(f"\nJSON:  {args.out}")
    print(f"JSONL: {jsonl_path}")


if __name__ == "__main__":
    main()
