"""C69 étape 3 : diagnostic 5x6 apparié, solo et duel contre AAAHogEx, trois bras.

* ``default`` : OpexAI au défaut ;
* ``c70`` : ``c70_mode_calibration=1`` (calibration par mode seule) ;
* ``c70_c69`` : ``c70_mode_calibration=1`` + ``c69_decision_bottleneck=1``.

``c70_c69`` contre ``c70`` isole C69 ; ``c70`` contre ``default`` mesure le coût de C70 seul.
Métriques : solo = profit annuel OpexAI ; duel = profit OpexAI / profit AAAHogEx.
Voir docs/11_goulot_decision.md §10, étape 3. Aucune sonde : les trois bras exécutent le même code.
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
DEFAULT_SEEDS = (100, 12345, 42, 7, 999)
AAAHOGEX_DIR = "AAAHogEx-115"

ARMS = (
    ("default", ()),
    ("c70", (("c70_mode_calibration", 1),)),
    ("c70_c69", (("c70_mode_calibration", 1), ("c69_decision_bottleneck", 1))),
)
PAIRS = (("c70", "default"), ("c70_c69", "c70"), ("c70_c69", "default"))


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


def _metric(row):
    if row["context"] == "solo":
        return row["opex_profit_year"]
    return row["opex_to_aaahogex_profit_ratio"]


def summarize(latest, seeds):
    per_arm = {}
    for context in ("solo", "duel"):
        for arm, _ in ARMS:
            values = [_metric(latest[(context, arm, seed)]) for seed in seeds]
            per_arm[f"{context}:{arm}"] = {"mean": _mean(values), "median": _median(values),
                                           "per_seed": dict(zip(seeds, values))}
    pairs = {}
    for context in ("solo", "duel"):
        for treat, ctrl in PAIRS:
            deltas = []
            for seed in seeds:
                t, c = _metric(latest[(context, treat, seed)]), _metric(latest[(context, ctrl, seed)])
                deltas.append(None if t is None or c is None else t - c)
            clean = [d for d in deltas if d is not None]
            pairs[f"{context}:{treat}-{ctrl}"] = {
                "deltas": dict(zip(seeds, deltas)), "delta_mean": _mean(clean),
                "delta_median": _median(clean), "paired_outcome": _paired_outcome(clean),
            }
    return {"per_arm": per_arm, "pairs": pairs}


def _print_summary(summary, seeds):
    for context, label in (("solo", "profit annuel OpexAI"), ("duel", "profit OpexAI / AAAHogEx")):
        print(f"\n=== {context.upper()} : {label} ===")
        print("seed | " + " | ".join(arm for arm, _ in ARMS))
        for seed in seeds:
            cells = []
            for arm, _ in ARMS:
                value = summary["per_arm"][f"{context}:{arm}"]["per_seed"][seed]
                cells.append("n/a" if value is None else (f"{value:.0f}" if context == "solo" else f"{value:.4f}"))
            print(f"{seed} | " + " | ".join(cells))
        for treat, ctrl in PAIRS:
            pair = summary["pairs"][f"{context}:{treat}-{ctrl}"]
            o = pair["paired_outcome"]
            print(f"{treat} - {ctrl}: moyenne {pair['delta_mean']:+.4f} W/T/L {o['wins']}/{o['ties']}/{o['losses']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_c69_paired_solo_duel_5x6.json")
    args = parser.parse_args()

    enable_savegame_cleanup()
    aaahogex = local_folder(str(ROOT / "ai" / AAAHOGEX_DIR), "AAAHogEx", ())
    cfg = make_cfg(STARTING_YEAR)
    days = 365 * args.years
    experiments = []
    for arm, settings in ARMS:
        opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", settings)
        for seed in args.seeds:
            for context, ais in (("solo", (opex,)), ("duel", (opex, aaahogex))):
                experiments.append({"bench_context": context, "bench_arm": arm, "seed": seed,
                                    "days": days, "openttd_config": cfg, "ais": ais})

    print(f"=== C69 étape 3 : {len(args.seeds)} graines x {args.years} ans, 3 bras, solo + duel ===")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        experiments=experiments, max_workers=args.workers, result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    latest = _latest_by_run(rows)
    expected = 2 * len(ARMS) * len(args.seeds)
    if len(latest) != expected:
        raise RuntimeError(f"runs finaux incomplets: {len(latest)}/{expected}")
    summary = summarize(latest, args.seeds)
    payload = {"openttd_version": OPENTTD_VERSION, "starting_year": STARTING_YEAR,
               "years": args.years, "seeds": args.seeds,
               "arms": {arm: dict(settings) for arm, settings in ARMS},
               "summary": summary, "final_runs": [latest[key] for key in sorted(latest)]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with args.out.with_suffix(".jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    _print_summary(summary, args.seeds)
    print(f"\nJSON:  {args.out}")


if __name__ == "__main__":
    main()
