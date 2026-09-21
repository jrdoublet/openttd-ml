"""C69 §15 : pourquoi l'avance du levier s'erode en duel.

Rejoue en duel les bras `c70` et `c70_c69` du diagnostic 5x6 (memes graines, sans sonde : parties
identiques a celles du banc, qui est deterministe). A chaque decembre, lit passivement dans la
sauvegarde les lignes des deux compagnies (mode, villes desservies, vehicules, profit de l'annee
ecoulee). Aucun journal de script : rien ne change dans la partie.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from openttdlab import bananas_ai_library, local_folder, run_experiments
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg, year_profit
from bench_1v1_5y_20seeds import extract_line_telemetry
from diag_c69_paired_solo_duel_5x6 import ARMS, DEFAULT_SEEDS, _profit_year

KEEP_ARMS = ("c70", "c70_c69")


def keep(row):
    if not re.match(r"^\d{4}-12-", str(row.get("date", ""))):
        return ()
    chunks = row.get("chunks", {})
    out = {"arm": row["experiment"]["bench_arm"], "seed": row["experiment"]["seed"],
           "date": str(row["date"]), "companies": {}}
    for owner in (0, 1):
        telemetry = extract_line_telemetry(chunks, owner)
        out["companies"][owner] = {
            "profit_year": _profit_year(chunks, owner),
            "lines": [{"mode": l["mode"], "towns": l["town_ids"], "vehicles": l["vehicles"],
                       "profit_last_year": l["profit_last_year_gbp"]} for l in telemetry["lines"]],
        }
    return (out,)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_c69_duel_erosion_5x6.json")
    args = parser.parse_args()
    enable_savegame_cleanup()
    aaahogex = local_folder(str(ROOT / "ai" / "AAAHogEx-115"), "AAAHogEx", ())
    cfg = make_cfg(1970)
    experiments = []
    for arm, settings in ARMS:
        if arm not in KEEP_ARMS:
            continue
        opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", settings)
        for seed in args.seeds:
            experiments.append({"bench_context": "duel", "bench_arm": arm, "seed": seed,
                                "days": 365 * args.years, "openttd_config": cfg, "ais": (opex, aaahogex)})
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        experiments=experiments, max_workers=3, result_processor=keep,
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail")),
    ))
    args.out.write_text(json.dumps(rows) + "\n", encoding="utf-8")
    print("snapshots", len(rows), "out", args.out)


if __name__ == "__main__":
    main()
