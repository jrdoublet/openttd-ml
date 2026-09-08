"""Mesure propre du biais de cout route via road_cost_probe (AIAccounting, isole de la
tresorerie), en remplacement de diag_road_cost_bias.py qui appariait des paneaux existants
via un delta de solde bancaire bruite (ratio min -0,161, impossible).

Panneau RP|<id>|<plannedCapital>|<actualCost>|<vehicles> emis a chaque tentative
OpexBuildRoadRoute (reussie ou non) sous road_cost_probe=1.
"""
import argparse
import re
import statistics
from pathlib import Path

from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup, make_cfg
import bench_v2

RE_RP = re.compile(r"^RP\|(-?\d+)\|(-?\d+)\|(-?\d+)\|(\d+)$")


def keep(row):
    chunks = row["chunks"]
    signs = [s["name"] for s in chunks.get("SIGN", {}).values()]
    bench_v2.append_checkpoint({"run": row["experiment"]["bench_run"],
                                 "date": str(row["date"]), "signs": signs})
    return ({"run": row["experiment"]["bench_run"], "date": str(row["date"]), "signs": signs},)


def parse_rp(all_signs):
    rows = []
    for sign in all_signs:
        m = RE_RP.match(sign)
        if m:
            planned, actual, vehicles = int(m.group(2)), int(m.group(3)), int(m.group(4))
            rows.append({"planned": planned, "actual": actual, "vehicles": vehicles,
                         "ok": vehicles > 0})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 42, 73, 100, 2026])
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--out", type=Path,
                        default=Path("results/diag_road_cost_probe_6y_5seeds.json"))
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()

    arm_name = "OpexAI[road_cost_probe=1,decision_log=1]"
    arms = build_arms([arm_name])
    cfg = make_cfg(1970)

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=3,
        result_processor=keep,
        experiments=[
            {"seed": seed, "days": 365 * args.years, "openttd_config": cfg,
             "ais": (arms[arm_name],), "bench_run": [arm_name, seed, 0]}
            for seed in args.seeds
        ],
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    by_run = {}
    for row in rows:
        key = tuple(row["run"])
        by_run.setdefault(key, []).append(row)

    all_attempts = []
    for key, series in by_run.items():
        _arm, seed, _rep = key
        # C41.10 (docs/taches.md, 2026-09-08) : les signes s'accumulent sur la carte, donc chaque
        # ligne de checkpoint mensuel contient le jeu COMPLET des signes deja poses -- pas
        # seulement les nouveaux depuis le mois precedent. Concatener toutes les lignes compte
        # chaque signe une fois par mois restant apres sa pose (bien pire qu'un facteur uniforme :
        # ca sur-pondere les tentatives precoces). Corrige : ne lire que la DERNIERE ligne, deja
        # complete (verifie empiriquement : la croissance est monotone, 0 -> 3035 sur 72 lignes).
        series.sort(key=lambda r: r["date"])
        all_signs = series[-1]["signs"] if series else []
        for a in parse_rp(all_signs):
            a["seed"] = seed
            all_attempts.append(a)

    ok = [a for a in all_attempts if a["ok"] and a["planned"] > 0]
    ratios = [a["actual"] / float(a["planned"]) for a in ok]

    summary = {
        "n_attempts_total": len(all_attempts),
        "n_ok_with_planned_capital": len(ok),
        "n_failed": sum(1 for a in all_attempts if not a["ok"]),
        "ratio_mean": statistics.mean(ratios) if ratios else None,
        "ratio_median": statistics.median(ratios) if ratios else None,
        "ratio_stdev": statistics.stdev(ratios) if len(ratios) > 1 else None,
        "ratio_min": min(ratios) if ratios else None,
        "ratio_max": max(ratios) if ratios else None,
        "per_seed": {},
    }
    for seed in args.seeds:
        seed_ratios = [a["actual"] / float(a["planned"]) for a in ok if a["seed"] == seed]
        summary["per_seed"][seed] = {
            "n": len(seed_ratios),
            "mean": statistics.mean(seed_ratios) if seed_ratios else None,
        }

    import json
    args.out.write_text(json.dumps({"summary": summary, "attempts": all_attempts}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
