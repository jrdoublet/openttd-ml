"""Banc apparie generique : deux bras nommes en ligne de commande, meme protocole que bench_v2.

Ecrit pour les corrections qu'aucun banc officiel ne peut trancher, ou l'on veut prouver une
NON-REGRESSION plutot qu'un gain : deux bras qui ne different que par un reglage, sur les memes
graines, et dont on attend des metriques IDENTIQUES. Sert aussi de banc apparie ordinaire.

⚠️ PAS de `decision_log=1` ni de `-d script=4` : a 20 graines x 10 ans x 2 bras, le volume d'AILog
fait exploser le checkpoint (13 Go observes lors d'un essai anterieur). Les metriques du verdict
viennent du chunk PLYR de la sauvegarde.
"""
import argparse
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", nargs="+", required=True,
                        help="Deux variantes ou plus, p. ex. 'OpexAI[x=0]' 'OpexAI[x=1]'")
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds doivent etre non vides ; --max-workers doit etre 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")
    if len(set(args.arms)) != len(args.arms) or len(args.arms) < 2:
        parser.error("--arms doit contenir au moins deux bras distincts")

    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    built = build_arms(list(args.arms))
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
        record.pop("openttd_output", "")
    failed = [record for record in summary if not record["run_ok"]]
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "arms": list(args.arms),
        "openttd_config": cfg,
        "design": "paired arms named on the command line; no decision_log",
        "success_metrics": list(SUCCESS_METRICS),
        "summary": summary,
        "failed_runs": [
            {"arm": record["arm"], "seed": record["seed"], "failure_reason": record["failure_reason"]}
            for record in failed
        ],
        "statistics": arm_statistics(summary, list(args.arms)),
        "paired_comparisons": paired_comparisons(summary, list(args.arms)),
    }
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    for comparison in payload["paired_comparisons"]:
        print(comparison["arm_a"], "vs", comparison["arm_b"])
        for metric, values in comparison["metrics"].items():
            print(metric, "d%=", values["mean_difference_percent"],
                  "wins=", values["arm_a_beats_arm_b"], "/", values["n"])
    if failed:
        raise SystemExit(f"banc invalide: {len(failed)} echec(s) NoAI")


if __name__ == "__main__":
    main()
