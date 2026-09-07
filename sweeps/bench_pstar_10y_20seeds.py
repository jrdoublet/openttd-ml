"""Banc apparié P1--P5 : arbre Git témoin contre répertoire de travail courant.

Le témoin est fourni par --control-dir, normalement un ``git archive HEAD``.
Ce choix est nécessaire car P4 modifie le code du constructeur et ne peut pas
être éteint par un réglage d'OpenTTD.
"""
import argparse
import json
import sys
from pathlib import Path

from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    SEEDS,
    SUCCESS_METRICS,
    arm_statistics,
    enable_savegame_cleanup,
    experiments,
    keep,
    make_cfg,
    paired_comparisons,
    summarise,
    write_json_atomically,
)
import bench_v2

CONTROL_ARM = "OpexAI[HEAD_before_P1_P5]"
TREATMENT_ARM = "OpexAI[P1_P5]"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-dir", type=Path, required=True)
    parser.add_argument("--control-revision", required=True)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path,
                        default=Path("docs/bench_pstar_10y_20seeds.json"))
    args = parser.parse_args()
    control_ai = args.control_dir / "ai" / "OpexAI"
    current_ai = ROOT / "ai" / "OpexAI"
    if not control_ai.is_dir():
        parser.error(f"AI témoin introuvable : {control_ai}")
    if args.years <= 0 or args.max_workers <= 0:
        parser.error("--years et --max-workers doivent être strictement positifs")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit contenir aucun doublon")

    args.out = ROOT / args.out if not args.out.is_absolute() else args.out
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    arms = {
        CONTROL_ARM: local_folder(str(control_ai), "OpexAI", ()),
        TREATMENT_ARM: local_folder(str(current_ai), "OpexAI", ()),
    }
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep,
        experiments=experiments(arms, args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)
    failed = [record for record in summary if not record["run_ok"]]
    arm_names = list(arms)
    payload = {
        "purpose": "P1-P5 against the Git HEAD immediately before their implementation",
        "control_revision": args.control_revision,
        "control_source": str(args.control_dir),
        "treatment_source": str(current_ai),
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "starting_year": 1970,
        "seeds": args.seeds,
        "arms": arm_names,
        "repeats": 1,
        "openttd_config": make_cfg(1970),
        "success_metrics": list(SUCCESS_METRICS),
        "paired_reading": "mean(P1-P5(seed) - HEAD(seed))",
        "checkpoint": str(bench_v2.CHECKPOINT_PATH),
        "summary": summary,
        "failed_runs": [
            {"arm": r["arm"], "seed": r["seed"], "failure_reason": r["failure_reason"]}
            for r in failed
        ],
        "statistics": arm_statistics(summary, arm_names),
        "paired_comparisons": paired_comparisons(summary, arm_names),
    }
    write_json_atomically(args.out, payload)
    print("failed", len(failed), "out", args.out, flush=True)
    for comparison in payload["paired_comparisons"]:
        for metric, values in comparison["metrics"].items():
            print(metric, "delta_pct=", values["mean_difference_percent"],
                  "wins=", values["arm_a_beats_arm_b"], "/", values["n"], flush=True)
    if failed:
        raise SystemExit(f"banc invalide: {len(failed)} erreur(s) fatale(s) NoAI")


if __name__ == "__main__":
    main()
