"""Grand banc factoriel et temporel C14 x C15 sur 10 ans (18 bras x 20 graines = 360 parties).

Analyse la trajectoire annuelle (annees 1 a 10) pour resoudre le compromis :
- a 3 ans : eviter la perte de valeur (-5.8 % avec buffer=50/cadence=90)
- a 10 ans : maximiser le profit et la valeur a long terme (+45 % profit annuel)

Mesures annuelles extraites au 1er decembre de chaque annee (1970 a 1979) :
company_value, profit_year, performance_history, n_vehicles, n_stations, median_station_rating.
"""
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import time
import scipy.stats as st

import openttdlab
from openttdlab import bananas_ai_library, run_experiments
import sweeps.bench_v2 as bench_v2

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
YEARS = 10
STARTING_YEAR = 1970
SEEDS = bench_v2.SEEDS  # 20 graines standard
MAX_WORKERS = 3

DEFAULT_ARMS = [
    # 1. Baseline de reference (buffer=-1, cadence=365)
    "OpexAI",

    # 2. Cadence seule (sans buffer)
    "OpexAI[air_fleet_cadence_days=90]",

    # 3. Buffer 0 (dimensionnement proportionnel des la premiere unite sans seuil d'attente)
    "OpexAI[air_fleet_buffer=0,air_fleet_cadence_days=365]",
    "OpexAI[air_fleet_buffer=0,air_fleet_cadence_days=180]",
    "OpexAI[air_fleet_buffer=0,air_fleet_cadence_days=90]",
    "OpexAI[air_fleet_buffer=0,air_fleet_cadence_days=30]",

    # 4. Buffer 15 (tampon ultra-leger : ~1/3 d'appareil)
    "OpexAI[air_fleet_buffer=15,air_fleet_cadence_days=365]",
    "OpexAI[air_fleet_buffer=15,air_fleet_cadence_days=180]",
    "OpexAI[air_fleet_buffer=15,air_fleet_cadence_days=90]",

    # 5. Buffer 25 (tampon modere : ~1/2 appareil)
    "OpexAI[air_fleet_buffer=25,air_fleet_cadence_days=365]",
    "OpexAI[air_fleet_buffer=25,air_fleet_cadence_days=180]",
    "OpexAI[air_fleet_buffer=25,air_fleet_cadence_days=90]",

    # 6. Buffer 35 (tampon intermediaire)
    "OpexAI[air_fleet_buffer=35,air_fleet_cadence_days=365]",
    "OpexAI[air_fleet_buffer=35,air_fleet_cadence_days=180]",
    "OpexAI[air_fleet_buffer=35,air_fleet_cadence_days=90]",

    # 7. Buffer 50 (tampon historique AAAHogEx)
    "OpexAI[air_fleet_buffer=50,air_fleet_cadence_days=365]",
    "OpexAI[air_fleet_buffer=50,air_fleet_cadence_days=180]",
    "OpexAI[air_fleet_buffer=50,air_fleet_cadence_days=90]",
]

METRICS_TRACKED = (
    "company_value",
    "profit_year",
    "performance_history",
    "n_vehicles",
    "n_stations",
    "median_station_rating",
)


def extract_annual_snapshots(rows, starting_year=1970, total_years=10):
    """Extrait l'etat au 1er decembre de chaque annee Y in [1..total_years]."""
    by_run = {}
    for row in rows:
        key = tuple(row["run"])  # (arm, seed, repeat)
        by_run.setdefault(key, []).append(row)

    snapshots = {}  # key -> dict of year -> record
    for key, series in by_run.items():
        series.sort(key=lambda r: r["date"])
        run_years = {}
        for y in range(1, total_years + 1):
            target_year = starting_year + y - 1
            target_date = f"{target_year}-12-01"
            # Cherche la sauvegarde exacte au 1er decembre, ou la plus proche precedente
            matching = [r for r in series if r["date"] == target_date]
            if not matching:
                matching = [r for r in series if r["date"] <= f"{target_year}-12-31"]
            if matching:
                run_years[y] = matching[-1]
            elif series:
                run_years[y] = series[-1]
        snapshots[key] = run_years
    return snapshots


def compute_annual_trajectories(snapshots, arms, seeds, total_years=10, baseline_name="OpexAI"):
    """Calcule pour chaque arm (vs baseline) les statistiques appariees annee par annee."""
    trajectories = {}
    for arm in arms:
        arm_traj = {}
        for y in range(1, total_years + 1):
            year_stats = {}
            for metric in METRICS_TRACKED:
                pairs = []
                for seed in seeds:
                    arm_rec = snapshots.get((arm, seed, 0), {}).get(y)
                    base_rec = snapshots.get((baseline_name, seed, 0), {}).get(y)
                    if arm_rec and base_rec:
                        val_arm = arm_rec.get(metric)
                        val_base = base_rec.get(metric)
                        if val_arm is not None and val_base is not None:
                            pairs.append((float(val_arm), float(val_base)))

                if not pairs:
                    year_stats[metric] = None
                    continue

                diffs = [a - b for a, b in pairs]
                mean_arm = statistics.mean([a for a, _ in pairs])
                mean_base = statistics.mean([b for _, b in pairs])
                mean_diff = statistics.mean(diffs)
                std_diff = statistics.stdev(diffs) if len(diffs) > 1 else 0.0
                se_diff = std_diff / math.sqrt(len(diffs)) if len(diffs) > 0 else 0.0
                diff_pct = (100.0 * mean_diff / mean_base) if mean_base != 0 else None
                wins = sum(1 for d in diffs if d > 0)
                ties = sum(1 for d in diffs if d == 0)
                losses = sum(1 for d in diffs if d < 0)

                # P-value t-test appaire
                p_val = 1.0
                if std_diff > 1e-9 and len(diffs) >= 2:
                    try:
                        res = st.ttest_rel([a for a, _ in pairs], [b for _, b in pairs])
                        p_val = float(res.pvalue) if not math.isnan(res.pvalue) else 1.0
                    except Exception:
                        p_val = 1.0

                year_stats[metric] = {
                    "n": len(pairs),
                    "mean_arm": bench_v2.number(mean_arm),
                    "mean_base": bench_v2.number(mean_base),
                    "mean_difference": bench_v2.number(mean_diff),
                    "mean_difference_percent": bench_v2.number(diff_pct),
                    "standard_deviation": bench_v2.number(std_diff),
                    "standard_error": bench_v2.number(se_diff),
                    "wins": wins,
                    "ties": ties,
                    "losses": losses,
                    "p_value": bench_v2.number(p_val),
                }
            arm_traj[y] = year_stats
        trajectories[arm] = arm_traj
    return trajectories


def build_ranking_summary(trajectories, arms):
    """Cree un tableau comparatif 3 ans vs 10 ans avec classification Pareto."""
    summary_list = []
    for arm in arms:
        if arm == "OpexAI":
            continue
        traj = trajectories.get(arm, {})
        y3 = traj.get(3, {})
        y10 = traj.get(10, {})

        y3_val = y3.get("company_value") or {}
        y3_prof = y3.get("profit_year") or {}
        y10_val = y10.get("company_value") or {}
        y10_prof = y10.get("profit_year") or {}

        val_3y_pct = y3_val.get("mean_difference_percent")
        val_3y_wins = y3_val.get("wins")
        val_3y_pval = y3_val.get("p_value")

        prof_10y_pct = y10_prof.get("mean_difference_percent")
        prof_10y_wins = y10_prof.get("wins")
        prof_10y_pval = y10_prof.get("p_value")

        val_10y_pct = y10_val.get("mean_difference_percent")
        val_10y_wins = y10_val.get("wins")

        # Critere de viabilite a 3 ans : pas de perte statistiquement significative de valeur
        # (gain positif >= 0%, ou perte negligeable non significative avec p >= 0.05)
        is_safe_3y = (
            val_3y_pct is not None and (
                val_3y_pct >= 0.0 or
                (val_3y_pct >= -2.0 and (val_3y_pval is None or val_3y_pval >= 0.05))
            )
        )

        summary_list.append({
            "arm": arm,
            "val_3y_pct": val_3y_pct,
            "val_3y_wins": val_3y_wins,
            "val_3y_pval": val_3y_pval,
            "prof_3y_pct": y3_prof.get("mean_difference_percent"),
            "val_10y_pct": val_10y_pct,
            "val_10y_wins": val_10y_wins,
            "prof_10y_pct": prof_10y_pct,
            "prof_10y_wins": prof_10y_wins,
            "prof_10y_pval": prof_10y_pval,
            "is_safe_3y": is_safe_3y,
            "trajectory_val_pct": [
                (traj.get(y, {}).get("company_value") or {}).get("mean_difference_percent")
                for y in range(1, 11)
            ],
            "trajectory_prof_pct": [
                (traj.get(y, {}).get("profit_year") or {}).get("mean_difference_percent")
                for y in range(1, 11)
            ],
        })

    # Tri : prioritiser les bras viables a 3 ans, puis trier par profit a 10 ans decroissant
    summary_list.sort(key=lambda item: (
        1 if item["is_safe_3y"] else 0,
        item["prof_10y_pct"] if item["prof_10y_pct"] is not None else -999.0
    ), reverse=True)
    return summary_list


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", nargs="+", default=list(DEFAULT_ARMS), help="bras a tester")
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS), help="graines OpenTTD")
    parser.add_argument("--years", type=int, default=YEARS, help="duree en annees")
    parser.add_argument("--starting-year", type=int, default=STARTING_YEAR, help="annee de depart")
    parser.add_argument("--out", type=Path, default=Path("docs/bench_c14_c15_trajectory_10y.json"), help="JSON final")
    parser.add_argument("--max-workers", type=int, default=MAX_WORKERS, help="workers paralleles")
    args = parser.parse_args()
    try:
        args.built_arms = bench_v2.build_arms(args.arms)
    except ValueError as err:
        parser.error(str(err))
    return args


def main():
    args = parse_args()
    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path = out.with_suffix(".jsonl")
    bench_v2.CHECKPOINT_PATH = checkpoint_path
    bench_v2.enable_savegame_cleanup()

    experiments_list = bench_v2.experiments(
        args.built_arms, args.seeds, args.years, repeats=1, starting_year=args.starting_year
    )
    total_experiments = len(experiments_list)

    print(f"=== GRAND BANC C14 x C15 : {len(args.arms)} BRAS x {len(args.seeds)} GRAINES = {total_experiments} EXPERIENCES ({args.years} ANS) ===", flush=True)
    print(f"Workers : {args.max_workers} | Checkpoint : {checkpoint_path} | Sortie : {out}", flush=True)

    t0 = time.time()
    rows = []
    completed = 0
    last_date_target = f"{args.starting_year + args.years - 1}-12-01"

    for record in run_experiments(
        openttd_version=bench_v2.OPENTTD_VERSION,
        opengfx_version=bench_v2.OPENGFX_VERSION,
        max_workers=args.max_workers,
        result_processor=bench_v2.keep,
        experiments=experiments_list,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ):
        rows.append(record)
        if record["date"] == last_date_target:
            completed += 1
            elapsed = time.time() - t0
            rate = completed / elapsed if elapsed > 0 else 0
            eta_sec = (total_experiments - completed) / rate if rate > 0 else 0
            arm_name = record["run"][0]
            seed = record["run"][1]
            val = record.get("company_value", 0)
            prof = record.get("profit_year", 0)
            print(
                f"[{completed:>3}/{total_experiments}] ({elapsed/60:>4.1f}m, ETA {eta_sec/60:>4.1f}m) "
                f"{arm_name:<50} s={seed:<6} val={val:>9} prof={prof:>8}",
                flush=True
            )

    elapsed_total = time.time() - t0
    print(f"\n--- TOUTES LES EXPERIENCES TERMINEES EN {elapsed_total/60:.2f} MINUTES ---", flush=True)

    # 1. Synthese finale annee 10
    final_summary = bench_v2.summarise(rows)
    failed_runs = [r for r in final_summary if not r.get("run_ok", True)]

    # 2. Extraction des etats annuels 1 a 10
    print("Extraction des instantanes annuels...", flush=True)
    snapshots = extract_annual_snapshots(rows, args.starting_year, args.years)

    # 3. Trajectoires annuelles appariees contre OpexAI
    print("Calcul des trajectoires annuelles appariees...", flush=True)
    trajectories = compute_annual_trajectories(
        snapshots, args.arms, args.seeds, args.years, baseline_name="OpexAI"
    )

    # 4. Classement et analyse Pareto
    ranking = build_ranking_summary(trajectories, args.arms)

    # Ecriture JSON complet
    payload = {
        "openttd_version": bench_v2.OPENTTD_VERSION,
        "opengfx_version": bench_v2.OPENGFX_VERSION,
        "years": args.years,
        "starting_year": args.starting_year,
        "seeds": args.seeds,
        "arms": args.arms,
        "total_experiments": total_experiments,
        "elapsed_seconds": bench_v2.number(elapsed_total),
        "ranking": ranking,
        "annual_trajectories": trajectories,
        "statistics_year_10": bench_v2.arm_statistics(final_summary, args.arms),
        "paired_comparisons_year_10": bench_v2.paired_comparisons(final_summary, args.arms),
        "summary_year_10": final_summary,
        "failed_runs": failed_runs,
    }

    bench_v2.write_json_atomically(out, payload)
    print(f"Rapport JSON ecrit : {out}", flush=True)

    # Affichage du tableau recapitulatif dans la sortie standard
    print("\n" + "=" * 120, flush=True)
    print(f"{'Bras':<52} | {'Val 3y %':>9} {'Wins':>5} {'p-val':>7} | {'Val 10y %':>10} | {'Prof 10y %':>11} {'Wins':>5} {'p-val':>7} | {'Statut 3y'}", flush=True)
    print("-" * 120, flush=True)
    for item in ranking:
        arm = item["arm"]
        v3_pct = f"{item['val_3y_pct']:+.1f} %" if item['val_3y_pct'] is not None else "N/A"
        v3_wins = f"{item['val_3y_wins']}/20" if item['val_3y_wins'] is not None else "N/A"
        v3_pval = f"{item['val_3y_pval']:.3f}" if item['val_3y_pval'] is not None else "N/A"

        v10_pct = f"{item['val_10y_pct']:+.1f} %" if item['val_10y_pct'] is not None else "N/A"

        p10_pct = f"{item['prof_10y_pct']:+.1f} %" if item['prof_10y_pct'] is not None else "N/A"
        p10_wins = f"{item['prof_10y_wins']}/20" if item['prof_10y_wins'] is not None else "N/A"
        p10_pval = f"{item['prof_10y_pval']:.3f}" if item['prof_10y_pval'] is not None else "N/A"

        statut = "VIABLE" if item["is_safe_3y"] else "REGRESSION"

        print(
            f"{arm:<52} | {v3_pct:>9} {v3_wins:>5} {v3_pval:>7} | {v10_pct:>10} | {p10_pct:>11} {p10_wins:>5} {p10_pval:>7} | {statut}",
            flush=True
        )
    print("=" * 120, flush=True)

    # Tableau detaille de la trajectoire de valeur nette
    print("\n" + "=" * 140, flush=True)
    print("TRAJECTOIRE DE VALEUR NETTE (% difference relative vs OpexAI)", flush=True)
    print(f"{'Bras':<48} | " + " | ".join(f" Y{y:<2}" for y in range(1, 11)), flush=True)
    print("-" * 140, flush=True)
    for item in ranking:
        vals = item["trajectory_val_pct"]
        val_str = " | ".join(f"{v:>4.1f}%" if v is not None else " N/A " for v in vals)
        print(f"{item['arm']:<48} | {val_str}", flush=True)
    print("=" * 140, flush=True)

    # Tableau detaille de la trajectoire de profit annuel
    print("\n" + "=" * 140, flush=True)
    print("TRAJECTOIRE DE PROFIT ANNUEL (% difference relative vs OpexAI)", flush=True)
    print(f"{'Bras':<48} | " + " | ".join(f" Y{y:<2}" for y in range(1, 11)), flush=True)
    print("-" * 140, flush=True)
    for item in ranking:
        profs = item["trajectory_prof_pct"]
        prof_str = " | ".join(f"{p:>4.1f}%" if p is not None else " N/A " for p in profs)
        print(f"{item['arm']:<48} | {prof_str}", flush=True)
    print("=" * 140, flush=True)

    if failed_runs:
        print(f"ATTENTION : {len(failed_runs)} run(s) ont echoue avec une erreur fatale NoAI !", flush=True)


if __name__ == "__main__":
    main()
