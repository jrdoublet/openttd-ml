"""C43/E3 famille 2 : ATTEMPT_FLOOR mord-il ? Aucun nouveau code de jeu -- le panneau `OR|`
(builder_rail.nut/main.nut, deja livre) porte deja `budgetInfo.path` sur CHAQUE tentative rail,
reussie ou non : "Z" = pas d'alternative, "F" = plancher ATTEMPT_FLOOR, "C" = plafond dur,
"N" = forme fermee non bornee (OpexIterationBudget, builder_rail.nut:112).

Panneaux AISign : lus depuis chunks["SIGN"], qui s'accumulent sur la carte -- une seule lecture
par (graine, arm), depuis la DERNIERE ligne de checkpoint (deja complete), jamais une
concatenation de toutes les lignes. docs/taches.md 2026-09-08 (2562e96) : bug de duplication deja
trouve et corrige ailleurs, evite ici des la conception.
"""
import argparse
import re
from collections import Counter
from pathlib import Path

from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup, make_cfg
import bench_v2

RE_OR = re.compile(r"^OR\|(\d+)\|(\d+)\|(\d+)\|([A-Z])S([A-Z])\|(-?\d+)\|(-?\d+)$")


def keep(row):
    chunks = row["chunks"]
    signs = [s["name"] for s in chunks.get("SIGN", {}).values()]
    bench_v2.append_checkpoint({"run": row["experiment"]["bench_run"],
                                 "date": str(row["date"]), "signs": signs})
    return ({"run": row["experiment"]["bench_run"], "date": str(row["date"]), "signs": signs},)


def parse_or(all_signs):
    rows = []
    for sign in all_signs:
        m = RE_OR.match(sign)
        if m:
            yy, line_id, pos, path, reason, budget, iterations = m.groups()
            rows.append({"path": path, "reason": reason, "budget": int(budget),
                        "iterations": int(iterations)})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 42, 73, 100, 2026])
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--out", type=Path,
                        default=Path("results/diag_attempt_floor_6y_5seeds.json"))
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()

    arm_name = "OpexAI[decision_log=1]"
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
    per_seed_path = {}
    for key, series in by_run.items():
        _arm, seed, _rep = key
        series.sort(key=lambda r: r["date"])
        # SIGN chunks accumulent sur la carte : une seule lecture, derniere ligne.
        all_signs = series[-1]["signs"] if series else []
        attempts = parse_or(all_signs)
        for a in attempts:
            a["seed"] = seed
            all_attempts.append(a)
        per_seed_path[seed] = Counter(a["path"] for a in attempts)

    path_counts = Counter(a["path"] for a in all_attempts)
    total = len(all_attempts)
    floor_budgets = [a["budget"] for a in all_attempts if a["path"] == "F"]
    floor_iterations = [a["iterations"] for a in all_attempts if a["path"] == "F"]

    payload = {
        "seeds": args.seeds, "years": args.years, "arm": arm_name,
        "n_attempts_total": total,
        "path_counts": dict(path_counts),
        "pct_by_path": {p: (100.0 * n / total if total else None) for p, n in path_counts.items()},
        "attempt_floor_iterations_mean": (sum(floor_iterations) / len(floor_iterations)
                                          if floor_iterations else None),
        "attempt_floor_budget_sample": floor_budgets[:5],
        "per_seed_path": {seed: dict(c) for seed, c in per_seed_path.items()},
    }
    import json
    with open(args.out, "w") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)

    print(f"n_attempts_total={total}")
    print("path_counts:", dict(path_counts))
    print("pct_by_path:", payload["pct_by_path"])
    print("per_seed_path:", payload["per_seed_path"])
    print("out", args.out)


if __name__ == "__main__":
    main()
