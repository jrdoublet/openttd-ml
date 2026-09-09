"""Banc officiel apparié C41.47 : libération immédiate de `_railSearch` sur blocage trésorerie
seul (`c41_rail_cash_release`), OFF vs ON (voir docs/04_arbitrage_rail_search.md §C41.47). Le
diagnostic 5×6 était NUL (14/14 constructions identiques, délai mixte) — ce banc est le seul
moyen tranché par le contrat de conclure. Vingt graines sur dix ans, trois CPU au plus.

⚠️ PAS de `decision_log=1` ni de `-d script=4` ici, contrairement aux diagnostics 5×6 : à 20
graines × 10 ans × 2 bras, le volume d'AILog fait exploser le checkpoint (13 Go en ~6 min lors
d'un premier essai, disque tombé à 873 Mo libres avant d'être tué). Les métriques du verdict
(company_value, performance_history, profit, profit_year, median_station_rating) viennent du
chunk PLYR de la sauvegarde, pas d'AILog -- ce banc n'en a pas besoin. `c41_event_counts` reste
tenté par précaution (comme `bench_c41_10_junction_repair_10y_20seeds.py`) mais sera
probablement vide sans le flag de debug ; ce n'est pas le verdict.
"""
import argparse
import re
from pathlib import Path
import sys

from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    SEEDS,
    SUCCESS_METRICS,
    arm_statistics,
    build_arms,
    enable_savegame_cleanup,
    experiments,
    keep,
    make_cfg,
    paired_comparisons,
    summarise,
    write_json_atomically,
)
import bench_v2

ARMS = (
    "OpexAI[c41_rail_cash_release=0]",
    "OpexAI[c41_rail_cash_release=1]",
)
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ (RAIL_BUILD|RAIL_EXPAND|C41_RAIL_CASH_RELEASE)")


def c41_event_counts(output):
    counts = {}
    for event in EVENT_RE.findall(output or ""):
        counts[event] = counts.get(event, 0) + 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds doivent etre non vides ; --max-workers doit etre 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    out = args.out or ROOT / "results" / f"bench_c41_47_rail_cash_release_{args.years}y_{len(args.seeds)}seeds.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    built = build_arms(list(ARMS))
    cfg = make_cfg(1970)
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep,
        experiments=experiments(built, args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)
    for record in summary:
        record["c41_event_counts"] = c41_event_counts(record.pop("openttd_output", ""))
    failed = [record for record in summary if not record["run_ok"]]
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "arms": list(ARMS),
        "openttd_config": cfg,
        "design": "paired OFF/ON; no decision_log (savegame-chunk metrics only, see module docstring)",
        "success_metrics": list(SUCCESS_METRICS),
        "summary": summary,
        "failed_runs": [
            {"arm": record["arm"], "seed": record["seed"], "failure_reason": record["failure_reason"]}
            for record in failed
        ],
        "statistics": arm_statistics(summary, list(ARMS)),
        "paired_comparisons": paired_comparisons(summary, list(ARMS)),
    }
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    for comparison in payload["paired_comparisons"]:
        print(comparison["arm_a"], "vs", comparison["arm_b"])
        for metric, values in comparison["metrics"].items():
            print(metric, "d%=", values["mean_difference_percent"], "wins=", values["arm_a_beats_arm_b"], "/", values["n"])
    if failed:
        raise SystemExit(f"banc invalide: {len(failed)} echec(s) NoAI")


if __name__ == "__main__":
    main()
