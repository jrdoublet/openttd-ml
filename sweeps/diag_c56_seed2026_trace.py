"""Diagnostic C56 : capturer le journal complet de la graine morte, pour voir ou l'IA s'arrete.

La graine 2026 ne journalise qu'une annee sur dix et finit a 13 gares contre 94,5 de mediane, alors
que le run est declare run_ok = True. Ce script ne mesure rien : il ECRIT LE JOURNAL BRUT sur le
disque, pour analyse. Une graine temoin vivante est capturee en meme temps : sans elle on ne peut
pas distinguer "l'IA s'arrete" de "le journal s'arrete".

⚠️ Volume : `-d script=4` produit ~2 000 lignes par an et par partie. Deux parties de dix ans
restent petites (quelques Mo), mais ne JAMAIS etendre ce script a vingt graines sans y repenser --
une campagne de 13 Go a deja tue un disque ici.
"""
import argparse
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup, experiments,
)

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

ARM = "OpexAI[decision_log=1]"


def keep_output(row):
    """⚠️ La cle est `bench_run` ([arm, graine, repetition]), PAS `bench_arm` : le modele de
    AGENTS.md se trompe sur ce point et le script echoue alors en KeyError apres avoir joue les
    parties. `keep` est appelee une fois par sauvegarde MENSUELLE, pas une fois par partie ; on ne
    garde donc que la derniere ligne de chaque partie, seule a porter le journal complet."""
    arm, seed, _repeat = row["experiment"]["bench_run"]
    return ({
        "seed": seed,
        "arm": arm,
        "date": str(row["date"]),
        "output": row.get("output", ""),
        "n_stations": len(row.get("chunks", {}).get("STNN", {})),
        "n_vehicles": len(row.get("chunks", {}).get("VEHS", {})),
    },)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=[2026, 999],
                        help="2026 = la graine morte ; 999 = temoin vivant (94 gares)")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=2)
    args = parser.parse_args()

    out_dir = args.out_dir or ROOT / "results" / "c56_seed2026_trace"
    out_dir.mkdir(parents=True, exist_ok=True)
    enable_savegame_cleanup()
    built = build_arms([ARM])
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep_output,
        experiments=experiments(built, args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    latest = {}
    for row in rows:
        key = row["seed"]
        if key not in latest or row["date"] > latest[key]["date"]:
            latest[key] = row
    for row in latest.values():
        path = out_dir / f"seed_{row['seed']}.log"
        path.write_text(row["output"] or "")
        lines = (row["output"] or "").count("\n")
        print(f"graine {row['seed']:>5} : {lines:>7} lignes, {row['n_stations']:>3} gares, "
              f"{row['n_vehicles']:>3} vehicules -> {path}")


if __name__ == "__main__":
    main()
