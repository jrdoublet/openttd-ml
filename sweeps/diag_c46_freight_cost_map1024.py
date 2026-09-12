"""Diagnostic de mesure directe du cout de calcul des generateurs fret C46 sur grande carte (1024x1024).

Compare OFF (c46_freight_grid=0) vs ON (c46_freight_grid=1) sur 5 graines x 1 an.
Extrait directement depuis les sauvegardes mensuelles (chunk SIGN) :
1. Le nombre de paires evaluees dans la boucle fret rail (panneau CR|<annee>|<pairsTotal>)
2. Les opcodes consommes par le generateur fret rail (panneau OP|<annee>|<cand_pax>|<cand_freight>)
3. Les opcodes consommes par les categories de candidats (panneaux BC|cand_freight et BC|cand_road)
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
    write_json_atomically,
)

ARMS = (
    "OpexAI[c46_freight_grid=0]",
    "OpexAI[c46_freight_grid=1]",
)
SEEDS = (42, 100, 999, 1234, 5678)
OUT_PATH = ROOT / "results" / "diag_c46_freight_cost_map1024.json"


def keep_with_freight_metrics(row):
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

    # Regrouper par run et prendre la sauvegarde finale (1970-12-01)
    by_run = {}
    for r in rows:
        key = (r["arm"], r["seed"])
        by_run.setdefault(key, []).append(r)

    summary = []
    for (arm, seed), series in sorted(by_run.items()):
        series.sort(key=lambda item: item["date"])
        final = series[-1]
        summary.append({
            "arm": arm,
            "seed": seed,
            "date": final["date"],
            "pairs_total": final["pairs_total"],
            "cand_freight_ops": final["cand_freight_ops"],
            "cand_pax_ops": final["cand_pax_ops"],
            "run_ok": script_failure_reason(final.get("openttd_output")) is None,
        })

    # Statistiques par bras
    arm_stats = {}
    for arm in ARMS:
        recs = [r for r in summary if r["arm"] == arm]
        arm_stats[arm] = {
            "mean_pairs_total": statistics.mean([r["pairs_total"] for r in recs]),
            "mean_cand_freight_ops": statistics.mean([r["cand_freight_ops"] for r in recs]),
        }

    # Comparaisons appariées (OFF vs ON)
    paired = []
    off_recs = {r["seed"]: r for r in summary if r["arm"] == ARMS[0]}
    on_recs = {r["seed"]: r for r in summary if r["arm"] == ARMS[1]}

    pair_deltas = []
    ops_deltas = []
    for s in SEEDS:
        off_r = off_recs[s]
        on_r = on_recs[s]
        pairs_ratio = (off_r["pairs_total"] / on_r["pairs_total"]) if on_r["pairs_total"] > 0 else 0
        ops_ratio = (off_r["cand_freight_ops"] / on_r["cand_freight_ops"]) if on_r["cand_freight_ops"] > 0 else 0
        pair_deltas.append(pairs_ratio)
        ops_deltas.append(ops_ratio)
        paired.append({
            "seed": s,
            "off_pairs": off_r["pairs_total"],
            "on_pairs": on_r["pairs_total"],
            "pairs_reduction_factor": round(pairs_ratio, 2),
            "off_cand_freight_ops": off_r["cand_freight_ops"],
            "on_cand_freight_ops": on_r["cand_freight_ops"],
            "ops_reduction_factor": round(ops_ratio, 2),
        })

    payload = {
        "description": "Mesure directe du cout CPU des generateurs fret sur grande carte 1024x1024 (5 graines x 1 an)",
        "seeds": list(SEEDS),
        "arms": list(ARMS),
        "arm_stats": arm_stats,
        "mean_pairs_reduction_factor": round(statistics.mean(pair_deltas), 2),
        "mean_ops_reduction_factor": round(statistics.mean(ops_deltas), 2),
        "paired": paired,
    }
    write_json_atomically(OUT_PATH, payload)
    print("Ecrit", OUT_PATH)
    print(f"\n--- Resultats de charge CPU fret (moyenne sur {len(SEEDS)} graines) ---")
    print(f"  Paires visitees : OFF={arm_stats[ARMS[0]]['mean_pairs_total']:.0f} vs ON={arm_stats[ARMS[1]]['mean_pairs_total']:.0f} | Reduction: {payload['mean_pairs_reduction_factor']}x")
    print(f"  Opcodes fret    : OFF={arm_stats[ARMS[0]]['mean_cand_freight_ops']:.0f} vs ON={arm_stats[ARMS[1]]['mean_cand_freight_ops']:.0f} | Reduction: {payload['mean_ops_reduction_factor']}x")


if __name__ == "__main__":
    main()
