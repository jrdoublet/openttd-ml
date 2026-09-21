"""Banc officiel apparie C46 sur grande carte 1024x1024 : grille spatiale
dirigee pour le fret (`c46_freight_grid`), OFF vs ON.

Le bras ON utilise OpexDirectedSpatialGrid pour filtrer les puits de fret
dans le voisinage de Moore 3x3, supprimant le balayage cartesien global inconditionnel
O(sources x sinks) (jusqu'a 1,4 million de paires sur 1024^2) au profit d'une
complexite dependante de la densite locale des voisinages O(sinks + sum q_s log q_s).

Le banc mesure l'impact macroscopique et la viabilite sur 20 graines x 10 ans.

⚠️ PAS de decision_log=1 ni de -d script=4 : a 20 graines x 10 ans x 2 bras,
le volume d'AILog ferait exploser le disque.
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
    make_cfg,
    paired_comparisons,
    summarise,
    write_json_atomically,
)
import bench_v2

ARMS = (
    "OpexAI[c46_freight_grid=0]",
    "OpexAI[c46_freight_grid=1]",
)
MAP_SIZE = 10  # 2^10 = 1024x1024


def keep_with_freight_telemetry(row):
    """Enrichit keep(row) des metriques directes de cout de generation fret extraites de SIGN."""
    chunks = row.get("chunks", {})
    signs = [s.get("name", "") for s in (chunks.get("SIGN") or {}).values()]
    cand_freight_ops = 0
    pairs_total = 0
    for s in signs:
        if s.startswith("OP|"):
            parts = s.split("|")
            if len(parts) >= 4:
                try:
                    cand_freight_ops = int(parts[3])
                except ValueError:
                    pass
        elif s.startswith("CR|"):
            parts = s.split("|")
            if len(parts) >= 3:
                try:
                    pairs_total = int(parts[2])
                except ValueError:
                    pass
    base = bench_v2.keep(row)[0]
    base["cand_freight_ops"] = cand_freight_ops
    base["pairs_total"] = pairs_total
    return (base,)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--map-size", type=int, default=MAP_SIZE)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=3)
    args = parser.parse_args()
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds doivent etre non vides ; --max-workers doit etre 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    out = args.out or ROOT / "results" / f"bench_c46_freight_grid_{args.years}y_{len(args.seeds)}seeds_map1024.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    built = build_arms(list(ARMS))
    cfg = make_cfg(1970, map_size=args.map_size)
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep_with_freight_telemetry,
        experiments=experiments(built, args.seeds, args.years, 1, 1970, map_size=args.map_size),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows, expected_last_year=1970 + args.years - 1)
    for record in summary:
        record.pop("openttd_output", "")
    failed = [record for record in summary if not record["run_ok"]]
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": args.years,
        "map_size": args.map_size,
        "seeds": args.seeds,
        "arms": list(ARMS),
        "openttd_config": cfg,
        "design": "paired OFF/ON on 1024x1024; no decision_log (savegame-chunk metrics only)",
        "success_metrics": list(SUCCESS_METRICS),
        "summary": summary,
        "failed_runs": [
            {"arm": record["arm"], "seed": record["seed"], "failure_reason": record["failure_reason"]}
            for record in failed
        ],
        "failed_run_count": len(failed),
        "arm_statistics": arm_statistics(summary, list(ARMS)),
        "paired_comparisons": paired_comparisons(summary, list(ARMS)),
    }
    write_json_atomically(out, payload)
    print("ecrit", out)
    print("failed runs:", len(failed))
    for comp in payload.get("paired_comparisons", []):
        pair_name = f"{comp['arm_a']} vs {comp['arm_b']}"
        print(f"\n--- Comparaison appariee : {pair_name} ---")
        for metric, stats in comp["metrics"].items():
            wins = stats.get("arm_a_beats_arm_b", 0)
            n = stats.get("n", 0)
            mean_delta = stats.get("mean_difference", 0)
            pct = stats.get("mean_difference_percent", 0)
            print(f"  {metric:<25}: delta={mean_delta:+12.1f} ({pct:+6.2f}%) | wins={wins}/{n}")
    if failed:
        raise SystemExit(f"banc invalide: {len(failed)} run(s) avec une erreur fatale NoAI")


if __name__ == "__main__":
    main()
