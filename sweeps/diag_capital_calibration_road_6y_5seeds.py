"""Effet apparie de l'extension de capital_calibration a la route (route x1,21, en plus du
rail x1,7 deja en place), diagnostic avant banc officiel (docs/taches.md, 2026-09-08).

Deux arms : capital_calibration=0 (aucune correction, aucun mode) contre
capital_calibration=1 (defaut, rail x1,7 + route x1,21 desormais). N'isole pas la
contribution marginale de la route seule (le rail etait deja corrige avant ce commit) --
mesure l'effet du paquet complet capital_calibration=1 tel qu'il existe maintenant.
"""
import sys
from pathlib import Path

from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    SUCCESS_METRICS,
    arm_statistics,
    build_arms,
    enable_savegame_cleanup,
    experiments,
    keep,
    paired_comparisons,
    summarise,
    write_json_atomically,
)
import bench_v2

YEARS = 6
SEEDS = (1, 42, 73, 100, 2026)
OUT = ROOT / "results" / "diag_capital_calibration_road_6y_5seeds.json"

ARM_NAMES = ("OpexAI[capital_calibration=0]", "OpexAI[capital_calibration=1]")


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = OUT.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()

    arms = build_arms(ARM_NAMES)

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=3,
        result_processor=keep,
        experiments=experiments(arms, SEEDS, YEARS, 1),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    summary = summarise(rows)
    result = {
        "arms": ARM_NAMES,
        "seeds": SEEDS,
        "years": YEARS,
        "statistics": arm_statistics(summary, ARM_NAMES),
        "paired": paired_comparisons(summary, ARM_NAMES),
        "summary": summary,
    }
    write_json_atomically(OUT, result)

    import json
    print(json.dumps({"statistics": result["statistics"], "paired": result["paired"]}, indent=2))


if __name__ == "__main__":
    main()
