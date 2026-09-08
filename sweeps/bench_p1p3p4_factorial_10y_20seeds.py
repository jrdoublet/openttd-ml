"""Banc factoriel 2^3 : P1 (capital_calibration) x P3 (event_catalog_invalidate) x
P4 (abandon_memory_transient_guard), sur le meme dossier ai/OpexAI (docs/taches.md, C38).

Objet : le banc conjoint P1--P5 (docs/bench_pstar_10y_20seeds.json, 2026-09-08) a mesure
+9,62% de valeur (15/20) et +7,92% de profit annuel (16/20) pour le paquet complet contre
HEAD pre-P1--P5, mais ne permet pas d'attribuer le gain a P1, P3 ou P4 separement -- piege
deja identifie dans ce projet (revue 2026-09-06 etape 1, item 2). P4 n'etait pas un reglage
au moment du banc P-star (fonction inconditionnelle) ; il est expose ici derriere
`abandon_memory_transient_guard` (2026-09-08) uniquement pour permettre ce factoriel sans
dupliquer d'arbre Git -- 1 reproduit exactement le comportement livre.

Les 8 arms sont tous issus du meme dossier ai/OpexAI (aucun git archive necessaire) :
    OpexAI[capital_calibration=A,event_catalog_invalidate=B,abandon_memory_transient_guard=C]
pour A, B, C dans {0, 1}. L'arm (1,1,1) doit reproduire bit-a-bit `OpexAI` seul (verifie au
smoke le 2026-09-08 : seed 42/100, 1 an, valeurs identiques).

paired_comparisons() calcule les 28 paires (C(8,2)) ; les effets principaux et interactions
se lisent en moyennant les paires qui ne different que par le facteur d'interet.
"""
import sys
from pathlib import Path

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

YEARS = 10
OUT = ROOT / "docs" / "bench_p1p3p4_factorial_10y_20seeds.json"
LOAD_FAILURE_MARKER = "Unable to load the script."

FACTOR_NAMES = ("capital_calibration", "event_catalog_invalidate", "abandon_memory_transient_guard")


def arm_name(cc, eci, amtg):
    return f"OpexAI[capital_calibration={cc},event_catalog_invalidate={eci},abandon_memory_transient_guard={amtg}]"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = OUT.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()

    arm_names = [
        arm_name(cc, eci, amtg)
        for cc in (0, 1)
        for eci in (0, 1)
        for amtg in (0, 1)
    ]
    arms = build_arms(arm_names)

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=3,
        result_processor=keep,
        experiments=experiments(arms, list(SEEDS), YEARS, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)
    failed = [record for record in summary if not record["run_ok"]
              or LOAD_FAILURE_MARKER in (record.get("openttd_output") or "")]
    payload = {
        "purpose": "Isolate P1/P3/P4 main effects and interactions (2^3 factorial) on the same "
                   "ai/OpexAI folder, following the P1-P5 joint bench (docs/bench_pstar_10y_20seeds.json)",
        "factors": list(FACTOR_NAMES),
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "years": YEARS,
        "starting_year": 1970,
        "seeds": list(SEEDS),
        "arms": arm_names,
        "repeats": 1,
        "openttd_config": make_cfg(1970),
        "success_metrics": list(SUCCESS_METRICS),
        "paired_reading": "mean(A(seed) - B(seed)) per pair; main effect of a factor = mean "
                           "over the 4 matched pairs that flip only that factor",
        "checkpoint": str(bench_v2.CHECKPOINT_PATH),
        "summary": summary,
        "failed_runs": [
            {"arm": r["arm"], "seed": r["seed"], "failure_reason": r["failure_reason"]}
            for r in failed
        ],
        "statistics": arm_statistics(summary, arm_names),
        "paired_comparisons": paired_comparisons(summary, arm_names),
    }
    write_json_atomically(OUT, payload)
    print("failed", len(failed), "out", OUT, flush=True)
    if failed:
        raise SystemExit(f"banc invalide: {len(failed)} erreur(s) fatale(s) NoAI")


if __name__ == "__main__":
    main()
