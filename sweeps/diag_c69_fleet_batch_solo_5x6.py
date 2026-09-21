"""C69 Annexe B contrat 2 : diagnostic 5x6 apparié en solo pur, quatre bras.

* ``default`` : OpexAI au défaut () ;
* ``fleet`` : ``c69_fleet_demand_batch=1`` ;
* ``c70_c69`` : ``c70_mode_calibration=1`` + ``c69_decision_bottleneck=1`` ;
* ``c70_c69_fleet`` : les trois à 1.

Paires : fleet-default, c70_c69_fleet-c70_c69, c70_c69-default.
Métrique primaire : profit annuel OpexAI (profit_year).
Métriques secondaires : valeur d'entreprise (company_value, PLYR) et nombre de véhicules (VEHS).
Exécution en solo seulement (le duel n'est pas déterministe, cf. docs/11_goulot_decision.md §16.1).
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
from physical_counters import decode_vehicles  # noqa: E402


STARTING_YEAR = 1970
DEFAULT_YEARS = 6
DEFAULT_SEEDS = (100, 12345, 42, 7, 999)

ARMS = (
    ("default", ()),
    ("fleet", (("c69_fleet_demand_batch", 1),)),
    ("c70_c69", (("c70_mode_calibration", 1), ("c69_decision_bottleneck", 1))),
    ("c70_c69_fleet", (("c70_mode_calibration", 1), ("c69_decision_bottleneck", 1), ("c69_fleet_demand_batch", 1))),
)
PAIRS = (
    ("fleet", "default"),
    ("c70_c69_fleet", "c70_c69"),
    ("c70_c69", "default"),
)


def _player(chunks, owner):
    players = chunks.get("PLYR") or {}
    return players.get(owner) or players.get(str(owner)) or {}


def _profit_year(chunks, owner):
    player = _player(chunks, owner)
    closed = player.get("old_economy") or []
    value = year_profit(closed) if closed else 0
    return value if value is not None else 0


def _company_value(chunks, owner):
    player = _player(chunks, owner)
    closed = player.get("old_economy") or []
    last_closed = closed[0] if closed else {}
    value = last_closed.get("company_value")
    return value if value is not None else 0


def _vehicle_count(chunks, owner):
    vehs = chunks.get("VEHS")
    if not vehs:
        return None
    dec = decode_vehicles(vehs, target_owner=owner)
    return dec["primary_vehicles_count"] if dec.get("chunk_valid") else None


def keep(row):
    """Conserver uniquement les métriques nécessaires, avec le tuple canonique."""
    chunks = row.get("chunks", {})
    context = row["experiment"]["bench_context"]
    opex_profit = _profit_year(chunks, 0)
    opex_company_value = _company_value(chunks, 0)
    opex_vehicles = _vehicle_count(chunks, 0)
    return ({
        "context": context,
        "arm": row["experiment"]["bench_arm"],
        "seed": row["experiment"]["seed"],
        "date": str(row.get("date", "")),
        "opex_profit_year": opex_profit,
        "opex_company_value": opex_company_value,
        "opex_vehicles": opex_vehicles,
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
    metric_fields = {
        "profit_year": "opex_profit_year",
        "company_value": "opex_company_value",
        "vehicles": "opex_vehicles",
    }
    by_metric = {}
    for label, field in metric_fields.items():
        per_arm = {}
        for arm, _ in ARMS:
            values = [latest[("solo", arm, seed)][field] for seed in seeds]
            per_arm[f"solo:{arm}"] = {
                "mean": _mean(values),
                "median": _median(values),
                "per_seed": dict(zip(seeds, values)),
            }
        pairs = {}
        for treat, ctrl in PAIRS:
            deltas = []
            for seed in seeds:
                t = latest[("solo", treat, seed)][field]
                c = latest[("solo", ctrl, seed)][field]
                deltas.append(None if t is None or c is None else t - c)
            clean = [d for d in deltas if d is not None]
            pairs[f"solo:{treat}-{ctrl}"] = {
                "deltas": dict(zip(seeds, deltas)),
                "delta_mean": _mean(clean),
                "delta_median": _median(clean),
                "paired_outcome": _paired_outcome(clean),
            }
        by_metric[label] = {"per_arm": per_arm, "pairs": pairs}

    return {
        "per_arm": by_metric["profit_year"]["per_arm"],
        "pairs": by_metric["profit_year"]["pairs"],
        "by_metric": by_metric,
    }


def _print_summary(summary, seeds):
    metric_labels = [
        ("profit_year", "profit annuel OpexAI (£/an)", "{:,.0f}"),
        ("company_value", "valeur d'entreprise OpexAI (£)", "{:,.0f}"),
        ("vehicles", "nombre de véhicules OpexAI", "{:.1f}"),
    ]
    for m_key, title, fmt in metric_labels:
        data = summary["by_metric"][m_key]
        print(f"\n=== SOLO : {title} ===")
        print("seed | " + " | ".join(arm for arm, _ in ARMS))
        for seed in seeds:
            cells = []
            for arm, _ in ARMS:
                value = data["per_arm"][f"solo:{arm}"]["per_seed"][seed]
                cells.append("n/a" if value is None else f"{value:.0f}")
            print(f"{seed} | " + " | ".join(cells))
        for treat, ctrl in PAIRS:
            pair = data["pairs"][f"solo:{treat}-{ctrl}"]
            o = pair["paired_outcome"]
            dm = pair["delta_mean"]
            dm_str = "n/a" if dm is None else f"{dm:+.1f}"
            print(f"{treat} - {ctrl}: delta moyen {dm_str} | W/T/L {o['wins']}/{o['ties']}/{o['losses']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_c69_fleet_batch_solo_5x6.json")
    args = parser.parse_args()

    enable_savegame_cleanup()
    cfg = make_cfg(STARTING_YEAR)
    days = 365 * args.years
    experiments = []
    for arm, settings in ARMS:
        opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", settings)
        for seed in args.seeds:
            experiments.append({
                "bench_context": "solo",
                "bench_arm": arm,
                "seed": seed,
                "days": days,
                "openttd_config": cfg,
                "ais": (opex,),
            })

    print(f"=== C69 Annexe B contrat 2 : {len(args.seeds)} graines x {args.years} ans, 4 bras, SOLO SEULEMENT ===")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        experiments=experiments, max_workers=args.workers, result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    latest = _latest_by_run(rows)
    expected = len(ARMS) * len(args.seeds)
    if len(latest) != expected:
        raise RuntimeError(f"runs finaux incomplets: {len(latest)}/{expected}")
    summary = summarize(latest, args.seeds)
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "starting_year": STARTING_YEAR,
        "years": args.years,
        "seeds": args.seeds,
        "arms": {arm: dict(settings) for arm, settings in ARMS},
        "summary": summary,
        "final_runs": [latest[key] for key in sorted(latest)],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with args.out.with_suffix(".jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    _print_summary(summary, args.seeds)
    print(f"\nJSON:  {args.out}")


if __name__ == "__main__":
    main()
