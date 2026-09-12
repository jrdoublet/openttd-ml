"""Diagnostic de mesure directe du cout CPU du generateur fret rail C46 sur grande carte (1024x1024).

Compare OFF (c46_freight_grid=0) vs ON (c46_freight_grid=1) sur 5 graines x 1 an.
Extrait directement depuis les sauvegardes mensuelles (chunk SIGN) :
1. Le nombre de paires evaluees dans la passe rail (panneau CR|<annee>|<pairsTotal>),
   qui englobe le socle pax (~180 paires identiques aux deux bras) et les paires fret.
2. Les opcodes consommes specifiquement par le generateur fret rail OpexFreightCandidates
   (panneau OP|<annee>|<cand_pax>|<cand_freight>, categorie cand_freight du budget).

Note : Le generateur routier (OpexRoadFreightCandidates) releve du budget cand_road
et fait l'objet d'une boucle distincte.
"""
import argparse
from pathlib import Path
import statistics
import sys

from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    build_arms,
    enable_savegame_cleanup,
    experiments,
    make_cfg,
    script_failure_reason,
    summarise,
    write_json_atomically,
)

ARMS = (
    "OpexAI[c46_freight_grid=0]",
    "OpexAI[c46_freight_grid=1]",
)
SEEDS = (42, 100, 999, 1234, 5678)
OUT_PATH = ROOT / "results" / "diag_c46_freight_cost_map1024.json"


def keep_with_freight_metrics(row):
    """Extrait les metriques de paires et d'opcodes de generateur depuis les panneaux."""
    chunks = row.get("chunks", {})
    signs = [s.get("name", "") for s in (chunks.get("SIGN") or {}).values()]

    cand_freight_ops = 0
    cand_pax_ops = 0
    pairs_total = 0

    for s in signs:
        if s.startswith("OP|"):
            parts = s.split("|")
            if len(parts) >= 4:
                try:
                    cand_pax_ops = int(parts[2])
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

    return ({
        "arm": row["experiment"]["bench_run"][0],
        "seed": row["experiment"]["bench_run"][1],
        "date": str(row.get("date")),
        "cand_freight_ops": cand_freight_ops,
        "cand_pax_ops": cand_pax_ops,
        "pairs_total": pairs_total,
        "openttd_output": row.get("output"),
    },)


def main():
    enable_savegame_cleanup()
    arms = build_arms(list(ARMS))
    exps = experiments(arms, list(SEEDS), 1, 1, 1970, map_size=10)

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=3,
        result_processor=keep_with_freight_metrics,
        experiments=exps,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    # Regroupement et verification de validite calendaire et NoAI
    by_run = {}
    for r in rows:
        key = (r["arm"], r["seed"])
        by_run.setdefault(key, []).append(r)

    summary = []
    for (arm, seed), series in sorted(by_run.items()):
        series.sort(key=lambda item: item["date"])
        final = series[-1]
        reason = script_failure_reason(final.get("openttd_output"))
        is_ok = (reason is None) and (final["date"] == "1971-01-01")
        summary.append({
            "arm": arm,
            "seed": seed,
            "final_date": final["date"],
            "pairs_total": final["pairs_total"],
            "cand_freight_ops": final["cand_freight_ops"],
            "cand_pax_ops": final["cand_pax_ops"],
            "run_ok": is_ok,
            "failure_reason": reason,
        })

    failed = [r for r in summary if not r["run_ok"]]
    if failed:
        raise SystemExit(f"Diagnostic invalide: {len(failed)} run(s) en echec NoAI ou tronques.")

    # Statistiques par bras (calculees strictement sur runs valides)
    arm_stats = {}
    for arm in ARMS:
        recs = [r for r in summary if r["arm"] == arm and r["run_ok"]]
        arm_stats[arm] = {
            "mean_pairs_total": statistics.mean([r["pairs_total"] for r in recs]),
            "mean_cand_freight_ops": statistics.mean([r["cand_freight_ops"] for r in recs]),
        }

    # Comparaisons appariees (OFF vs ON)
    paired = []
    off_recs = {r["seed"]: r for r in summary if r["arm"] == ARMS[0]}
    on_recs = {r["seed"]: r for r in summary if r["arm"] == ARMS[1]}

    pair_ratios = []
    ops_ratios = []
    for s in SEEDS:
        off_r = off_recs[s]
        on_r = on_recs[s]
        pairs_ratio = (off_r["pairs_total"] / on_r["pairs_total"]) if on_r["pairs_total"] > 0 else 0
        ops_ratio = (off_r["cand_freight_ops"] / on_r["cand_freight_ops"]) if on_r["cand_freight_ops"] > 0 else 0
        pair_ratios.append(pairs_ratio)
        ops_ratios.append(ops_ratio)
        paired.append({
            "seed": s,
            "off_pairs_total": off_r["pairs_total"],
            "on_pairs_total": on_r["pairs_total"],
            "pairs_reduction_factor": round(pairs_ratio, 2),
            "off_cand_freight_ops": off_r["cand_freight_ops"],
            "on_cand_freight_ops": on_r["cand_freight_ops"],
            "ops_reduction_factor": round(ops_ratio, 2),
        })

    payload = {
        "description": "Mesure directe du cout CPU du generateur fret rail OpexFreightCandidates sur carte 1024x1024 (5 graines x 1 an)",
        "methodology": (
            "cand_freight_ops mesure le budget opcodes consomme par le generateur fret rail (panneau OP). "
            "pairs_total mesure les paires evaluees dans la passe rail (panneau CR), englobant le socle "
            "pax (identique aux deux bras grace a OpexSpatialGrid) et les paires fret. "
            "Le generateur routier (cand_road) est separe."
        ),
        "total_runs": len(summary),
        "failed_runs": len(failed),
        "all_runs_ok": len(failed) == 0,
        "seeds": list(SEEDS),
        "arms": list(ARMS),
        "arm_stats": arm_stats,
        "mean_pairs_reduction_factor": round(statistics.mean(pair_ratios), 2),
        "mean_ops_reduction_factor": round(statistics.mean(ops_ratios), 2),
        "summary": summary,
        "paired": paired,
    }
    write_json_atomically(OUT_PATH, payload)
    print("Ecrit", OUT_PATH)
    print(f"\n--- Charge CPU fret rail mesuree ({len(summary)}/{len(summary)} runs sains, 5 graines) ---")
    print(f"  Paires evaluees : OFF={arm_stats[ARMS[0]]['mean_pairs_total']:.0f} vs ON={arm_stats[ARMS[1]]['mean_pairs_total']:.0f} | Facteur reduction : {payload['mean_pairs_reduction_factor']}x")
    print(f"  Opcodes fret    : OFF={arm_stats[ARMS[0]]['mean_cand_freight_ops']:.0f} vs ON={arm_stats[ARMS[1]]['mean_cand_freight_ops']:.0f} | Facteur reduction : {payload['mean_ops_reduction_factor']}x")


if __name__ == "__main__":
    main()
