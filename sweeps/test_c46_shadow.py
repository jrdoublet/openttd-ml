"""Test et rapport des executions shadow de C46.

Verifie l'equivalence stricte entre la grille spatiale dirigee et le parcours
cartesien historique sous c46_freight_grid_shadow=1.
Execute :
1. graine 42 sur carte 256x256 (1 an)
2. graine 100 sur carte 256x256 (2 ans)
3. graine 42 sur carte 1024x1024 (1 an)
"""
import json
from pathlib import Path
import sys

from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    build_arms,
    enable_savegame_cleanup,
    make_cfg,
    script_failure_reason,
    year_profit,
    write_json_atomically,
)

OUT_PATH = ROOT / "results" / "test_c46_shadow.json"


def keep_shadow(row):
    chunks = row.get("chunks", {})
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    return ({
        "arm": row["experiment"]["bench_run"][0],
        "seed": row["experiment"]["bench_run"][1],
        "test_name": row["experiment"]["bench_run"][2],
        "date": str(row.get("date")),
        "company_value": last_closed.get("company_value", 0),
        "profit_year": year_profit(closed) if closed else 0,
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "openttd_output": row.get("output"),
    },)


def main():
    enable_savegame_cleanup()
    arms = build_arms(["OpexAI[c46_freight_grid=1,c46_freight_grid_shadow=1]"])
    arm_obj = arms["OpexAI[c46_freight_grid=1,c46_freight_grid_shadow=1]"]

    # 3 experiences bien distinctes
    exps = [
        {
            "seed": 42,
            "days": 365,
            "openttd_config": make_cfg(1970, map_size=8),
            "ais": (arm_obj,),
            "bench_run": ["OpexAI[c46_freight_grid=1,c46_freight_grid_shadow=1]", 42, "seed42_map256_1y"],
        },
        {
            "seed": 100,
            "days": 365 * 2,
            "openttd_config": make_cfg(1970, map_size=8),
            "ais": (arm_obj,),
            "bench_run": ["OpexAI[c46_freight_grid=1,c46_freight_grid_shadow=1]", 100, "seed100_map256_2y"],
        },
        {
            "seed": 42,
            "days": 365,
            "openttd_config": make_cfg(1970, map_size=10),
            "ais": (arm_obj,),
            "bench_run": ["OpexAI[c46_freight_grid=1,c46_freight_grid_shadow=1]", 42, "seed42_map1024_1y"],
        },
    ]

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=3,
        result_processor=keep_shadow,
        experiments=exps,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    # Regrouper par run et prendre l'etat final
    by_run = {}
    for r in rows:
        key = (r["arm"], r["seed"], r["test_name"])
        by_run.setdefault(key, []).append(r)

    summary = []
    for (arm, seed, test_name), series in sorted(by_run.items(), key=lambda x: x[0][2]):
        series.sort(key=lambda item: item["date"])
        final = series[-1]
        summary.append({
            "test_name": test_name,
            "arm": arm,
            "seed": seed,
            "final_date": final["date"],
            "company_value": final["company_value"],
            "profit_year": final["profit_year"],
            "n_vehicles": final["n_vehicles"],
            "n_stations": final["n_stations"],
            "run_ok": script_failure_reason(final.get("openttd_output")) is None,
        })

    failed = [record for record in summary if not record["run_ok"]]
    payload = {
        "description": "Validation shadow C46 (c46_freight_grid_shadow=1) sur cartes 256x256 et 1024x1024",
        "total_runs": len(summary),
        "failed_runs": len(failed),
        "all_runs_ok": len(failed) == 0,
        "runs": summary,
    }
    write_json_atomically(OUT_PATH, payload)
    print("Ecrit", OUT_PATH)
    if failed:
        raise SystemExit(f"Echec shadow: {len(failed)} run(s) en erreur")
    print(f"Succes: {len(summary)}/{len(summary)} runs shadow valides avec 0 mismatch/assertion.")


if __name__ == "__main__":
    main()
