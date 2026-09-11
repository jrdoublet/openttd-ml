"""Banc officiel apparie C55 : relaxation de la regle d'origine du FRET ROUTIER
(`c55_freight_origin_relax`), OFF vs ON.

Le bras ON remplace la proximite geometrique (`OpexOriginServed` en OU, rayon
ORIGIN_SEPARATION = 3, toutes lignes tous cargos confondus) par le couple
« ET geometrique + identite exacte meme cargo » :

    rejet si (OriginServed(src) ET OriginServed(dst)) OU busy(cargo, src) OU busy(cargo, dst)

`busy(cargo, tile)` implique `OriginServed(tile, true)` (distance 0 < 3), donc
**le bras ON ne rejette que des candidats que OFF rejetait deja** : il ne peut
qu'ajouter des candidats fret, jamais en retirer. L'etape 1 (C55, 2026-09-11) a
mesure que 86,1 % des rejets n'ont qu'UNE extremite servie et que 100 % de ces
recuperables sont du fret (`one_served_pax = 0`, 5 graines x 5 ans).

⚠️ PAS de `decision_log=1` ni de `-d script=4` : a 20 graines x 10 ans x 2 bras,
le volume d'AILog fait exploser le checkpoint (13 Go observes lors d'un essai
anterieur, disque tombe a 873 Mo libres). Les metriques du verdict viennent du
chunk PLYR de la sauvegarde, pas d'AILog.
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

ARMS = (
    "OpexAI[c55_freight_origin_relax=0]",
    "OpexAI[c55_freight_origin_relax=1]",
)


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

    out = args.out or ROOT / "results" / f"bench_c55_freight_origin_relax_{args.years}y_{len(args.seeds)}seeds.json"
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
        record.pop("openttd_output", "")
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
            print(metric, "d%=", values["mean_difference_percent"],
                  "wins=", values["arm_a_beats_arm_b"], "/", values["n"])
    if failed:
        raise SystemExit(f"banc invalide: {len(failed)} echec(s) NoAI")


if __name__ == "__main__":
    main()
