"""Smoke test CI pour OpexAI.

Porte de PR rapide executant 2 graines x 3 ans avec OpenTTDLab.
Verifie :
1. Aucun crash / erreur fatale NoAI (run_ok == True).
2. Plancher de plausibilite :
   - au moins 1 gare construite (n_stations >= 1)
   - au moins 1 vehicule pilotable (primary_vehicles >= 1)
   - valeur de compagnie > 1 (£) et activite economique.
"""
import argparse
import json
import os
from pathlib import Path
import sys

from openttdlab import bananas_ai_library, run_experiments

# Importer les utilitaires et configurations eprouves du banc
from bench_v2 import (
    OPENTTD_VERSION,
    OPENGFX_VERSION,
    benchmark_completeness,
    build_arms,
    enable_savegame_cleanup,
    experiments,
    keep,
    make_cfg,
    summarise,
    write_json_atomically,
)
from game_health import enable_engine_failure_capture

DEFAULT_SEEDS = (42, 100)
DEFAULT_YEARS = 3
DEFAULT_ARM = "OpexAI"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", default=DEFAULT_ARM, help="Nom ou variante de l'IA (defaut: OpexAI)")
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS), help="Graines a tester (defaut: 42 100)")
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS, help="Duree en annees (defaut: 3)")
    parser.add_argument("--starting-year", type=int, default=1970, help="Annee de depart (defaut: 1970)")
    parser.add_argument("--max-workers", type=int, default=3, help="Workers paralleles (defaut: 3)")
    parser.add_argument("--out", type=Path, default=Path("results/smoke_ci.json"), help="Fichier de sortie JSON")
    return parser.parse_args()


def verify_plausibility(record):
    """Verifie qu'une partie est saine et respecte le plancher d'activite."""
    errors = []
    if not record.get("run_ok", True):
        errors.append(f"Erreur script fatale NoAI: {record.get('failure_reason')}")
    if (record.get("n_stations") or 0) < 1:
        errors.append(f"Plancher echoue: 0 gare construite (n_stations={record.get('n_stations')})")
    primary_vehicles = record.get("primary_vehicles", record.get("n_vehicles"))
    if (primary_vehicles or 0) < 1:
        errors.append(
            "Plancher echoue: 0 vehicule pilotable "
            f"(primary_vehicles={primary_vehicles})"
        )
    if (record.get("company_value") or 0) <= 1:
        errors.append(f"Plancher echoue: valeur de compagnie anormale/faillite (company_value={record.get('company_value')})")
    return errors


def main():
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    import bench_v2
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_engine_failure_capture()
    enable_savegame_cleanup()

    built_arms = build_arms([args.arm])
    cfg = make_cfg(args.starting_year)

    print(f"=== Lancement Smoke Test CI ({args.arm}) : {len(args.seeds)} graines x {args.years} ans ===")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=keep,
        experiments=experiments(built_arms, args.seeds, args.years, repeats=1, starting_year=args.starting_year),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    summary = summarise(
        rows,
        expected_last_year=args.starting_year + args.years - 1,
        expected_savegames=args.years * 12,
    )
    completeness = benchmark_completeness(summary, [args.arm], args.seeds, repeats=1)
    all_errors = [
        f"Run absent: arm={item['arm']} seed={item['seed']} repeat={item['repeat']}"
        for item in completeness["missing_runs"]
    ]
    all_errors.extend(
        f"Run inattendu: arm={item['arm']} seed={item['seed']} repeat={item['repeat']}"
        for item in completeness["unexpected_runs"]
    )

    print("\n=== Resultats par graine ===")
    for record in summary:
        seed_errors = verify_plausibility(record)
        status_str = "OK" if not seed_errors else "ECHEC"
        print(
            f"[{status_str}] seed={record['seed']:<6} "
            f"valeur={record['company_value']:>10} £ | "
            f"profit_an={record.get('profit_year', 0):>9} £ | "
            f"score={record.get('performance_history', 0):>4} | "
            f"gares={record.get('n_stations', 0):>2} | "
            f"vehs={record.get('primary_vehicles', record.get('n_vehicles', 0)):>2}"
        )
        if seed_errors:
            for err in seed_errors:
                print(f"  -> {err}")
                all_errors.append(f"Seed {record['seed']}: {err}")

    for record in summary:
        record.pop("openttd_output", None)

    payload = {
        "smoke_test_status": "PASSED" if not all_errors else "FAILED",
        "arm": args.arm,
        "seeds": args.seeds,
        "years": args.years,
        "errors": all_errors,
        "completeness": completeness,
        "summary": summary,
    }
    write_json_atomically(args.out, payload)
    print(f"\nRapport enregistre dans : {args.out}")

    if all_errors:
        print(f"\n❌ SMOKE TEST ECHOUE ({len(all_errors)} anomalie(s))", file=sys.stderr)
        sys.exit(1)
    else:
        print("\n✅ SMOKE TEST REUSSI (tous les planchers de plausibilite sont valides)")


if __name__ == "__main__":
    main()
