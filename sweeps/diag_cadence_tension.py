"""Sonde conjointe Cadence x Tension (Tâche B7, docs/taches.md).

Protocole B7 :
- 2 bras :
  1. `buffer=0,cadence=365` (cadence annuelle lente)
  2. `buffer=0,cadence=90`  (cadence trimestrielle rapide)
  Tous deux avec `tension_probe=1` et `decision_log=1`.
- 5 graines (42, 100, 7, 999, 2026) x 6 ans (1970-1975) pour encadrer le croisement de l'année 4.
- Analyse :
  - Amplitude et répartition de la tension ARGENT par année et par bras.
  - Distribution de la ressource dominante (argent, slots_vehicules, opcodes, foncier).
  - Évolution des composantes financières (available, commitments, flow, tau).
- Hypothèse à tester :
  « La cadence 90 fait monter la tension argent à partir de l'année 4 ».
"""
import argparse
from collections import Counter, defaultdict
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import enable_savegame_cleanup, make_cfg, quarter_profit, year_profit, station_ratings  # noqa: E402

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
DEFAULT_SEEDS = (42, 100, 7, 999, 2026)
DEFAULT_YEARS = 6
STARTING_YEAR = 1970

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

OPEX_TENSION_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) (TENSION|TENSION_COST) (.*)$")
OPEX_EVENT_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")
FAIL_RE = re.compile(r"Your script made an error|The script died unexpectedly")


def result_extractor(row):
    chunks = row.get("chunks", {})
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    ratings = station_ratings(chunks)
    return ({
        "arm": row["experiment"]["bench_arm"],
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "company_value": last_closed.get("company_value"),
        "profit_year": year_profit(closed),
        "profit": quarter_profit(last_closed),
        "performance_history": last_closed.get("performance_history"),
        "money": (player or {}).get("money"),
        "current_loan": (player or {}).get("current_loan"),
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "output": row.get("output"),
    },)


def parse_trace(output):
    tensions = []
    costs = []
    events = defaultdict(list)
    errors = []

    for line in (output or "").splitlines():
        if FAIL_RE.search(line):
            errors.append(line.strip()[:200])
            continue
        m_tens = OPEX_TENSION_RE.search(line)
        if m_tens:
            year, month, day, kind, rest = m_tens.groups()
            fields = {"year": int(year), "month": int(month), "day": int(day)}
            for token in rest.split():
                if "=" in token:
                    k, _, v = token.partition("=")
                    fields[k] = v
            if kind == "TENSION":
                tensions.append(fields)
            else:
                costs.append(fields)
            continue
        m_evt = OPEX_EVENT_RE.search(line)
        if m_evt:
            year, month, day, kind, rest = m_evt.groups()
            fields = {"year": int(year), "month": int(month), "day": int(day)}
            for token in rest.split():
                if "=" in token:
                    k, _, v = token.partition("=")
                    fields[k] = v
            events[kind].append(fields)

    return tensions, costs, events, errors


def analyze_arm_seed(arm_name, seed, tensions, costs, events):
    by_year = defaultdict(lambda: {
        "evals": 0,
        "dominant_counts": Counter(),
        "argent_tensions_all": [],
        "argent_tensions_finite": [],
        "argent_infinite_count": 0,
        "argent_binding_count": 0,  # >= 0.5 or infinite
        "argent_slack_count": 0,    # < 0.1
        "argent_available": [],
        "argent_commitments": [],
        "argent_flow": [],
        "argent_tau": [],
    })

    for t in tensions:
        y = t["year"]
        by_year[y]["evals"] += 1
        dom = t.get("dominant", "unknown")
        by_year[y]["dominant_counts"][dom] += 1

        try:
            at = float(t.get("argent_tension", "nan"))
        except ValueError:
            at = float("nan")

        if at == -1.0:
            by_year[y]["argent_infinite_count"] += 1
            by_year[y]["argent_binding_count"] += 1
            by_year[y]["argent_tensions_all"].append(-1.0)
        elif at == at and at >= 0:
            by_year[y]["argent_tensions_all"].append(at)
            by_year[y]["argent_tensions_finite"].append(at)
            if at >= 0.5:
                by_year[y]["argent_binding_count"] += 1
            elif at < 0.1:
                by_year[y]["argent_slack_count"] += 1

        for fld, key in [("argent_available", "argent_available"),
                         ("argent_commitments", "argent_commitments"),
                         ("argent_flow", "argent_flow"),
                         ("argent_tau", "argent_tau")]:
            try:
                val = float(t.get(fld, "nan"))
                if val == val:
                    by_year[y][key].append(val)
            except ValueError:
                pass

    summary_by_year = {}
    for y in sorted(by_year.keys()):
        d = by_year[y]
        evals = d["evals"]
        finite = d["argent_tensions_finite"]
        med_finite = statistics.median(finite) if finite else 0.0
        mean_finite = statistics.mean(finite) if finite else 0.0
        max_finite = max(finite) if finite else 0.0
        inf_pct = (100.0 * d["argent_infinite_count"] / evals) if evals else 0.0
        binding_pct = (100.0 * d["argent_binding_count"] / evals) if evals else 0.0
        slack_pct = (100.0 * d["argent_slack_count"] / evals) if evals else 0.0

        summary_by_year[y] = {
            "evals": evals,
            "dominant": dict(d["dominant_counts"]),
            "dominant_pct": {k: round(100.0 * v / evals, 1) for k, v in d["dominant_counts"].items()} if evals else {},
            "argent_med_finite": round(med_finite, 4),
            "argent_mean_finite": round(mean_finite, 4),
            "argent_max_finite": round(max_finite, 4),
            "argent_infinite_count": d["argent_infinite_count"],
            "argent_infinite_pct": round(inf_pct, 1),
            "argent_binding_count": d["argent_binding_count"],
            "argent_binding_pct": round(binding_pct, 1),
            "argent_slack_pct": round(slack_pct, 1),
            "med_available": round(statistics.median(d["argent_available"]), 0) if d["argent_available"] else 0,
            "med_commitments": round(statistics.median(d["argent_commitments"]), 0) if d["argent_commitments"] else 0,
            "med_flow": round(statistics.median(d["argent_flow"]), 0) if d["argent_flow"] else 0,
            "med_tau": round(statistics.median(d["argent_tau"]), 1) if d["argent_tau"] else 0,
        }

    return {
        "arm": arm_name,
        "seed": seed,
        "by_year": summary_by_year,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_cadence_tension.json")
    args = parser.parse_args()

    enable_savegame_cleanup()

    arms_def = {
        "cadence_365": (
            ("air_fleet_buffer", 0),
            ("air_fleet_cadence_days", 365),
            ("probe_portfolio", 1),
            ("decision_log", 1),
        ),
        "cadence_90": (
            ("air_fleet_buffer", 0),
            ("air_fleet_cadence_days", 90),
            ("probe_portfolio", 1),
            ("decision_log", 1),
        ),
    }

    built_experiments = []
    for arm_name, params in arms_def.items():
        ai_folder = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", params)
        for seed in args.seeds:
            built_experiments.append({
                "bench_arm": arm_name,
                "seed": seed,
                "days": 365 * args.years,
                "openttd_config": make_cfg(STARTING_YEAR),
                "ais": (ai_folder,),
            })

    print(f"=== Lancement Sonde B7 : Cadence x Tension ({len(arms_def)} bras x {len(args.seeds)} graines x {args.years} ans) ===")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.workers,
        result_processor=result_extractor,
        experiments=built_experiments,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    results = {}
    financials = defaultdict(dict)
    all_errors = defaultdict(list)

    for r in rows:
        arm = r["arm"]
        seed = r["seed"]
        financials[arm][seed] = {
            "company_value": r.get("company_value"),
            "profit_year": r.get("profit_year"),
            "profit": r.get("profit"),
            "n_vehicles": r.get("n_vehicles"),
            "n_stations": r.get("n_stations"),
            "money": r.get("money"),
        }
        tensions, costs, events, errors = parse_trace(r.get("output", ""))
        if errors:
            all_errors[f"{arm}_s{seed}"].extend(errors)
        results.setdefault(arm, {})[seed] = analyze_arm_seed(arm, seed, tensions, costs, events)

    aggregated = {}
    for arm in arms_def:
        agg_years = {}
        for y in range(STARTING_YEAR, STARTING_YEAR + args.years):
            evals_tot = 0
            dom_counts = Counter()
            binding_counts = 0
            inf_counts = 0
            slack_counts = 0
            med_finites = []
            med_availables = []
            med_commitments = []
            med_flows = []
            med_taus = []

            for seed in args.seeds:
                sy = results[arm][seed]["by_year"].get(y, {})
                if not sy:
                    continue
                evals_tot += sy["evals"]
                for d, c in sy["dominant"].items():
                    dom_counts[d] += c
                binding_counts += sy["argent_binding_count"]
                inf_counts += sy["argent_infinite_count"]
                med_finites.append(sy["argent_med_finite"])
                med_availables.append(sy["med_available"])
                med_commitments.append(sy["med_commitments"])
                med_flows.append(sy["med_flow"])
                med_taus.append(sy["med_tau"])

            agg_years[y] = {
                "evals_total": evals_tot,
                "dominant_share": {k: round(100.0 * v / evals_tot, 1) for k, v in dom_counts.items()} if evals_tot else {},
                "argent_binding_share_pct": round(100.0 * binding_counts / evals_tot, 1) if evals_tot else 0.0,
                "argent_infinite_share_pct": round(100.0 * inf_counts / evals_tot, 1) if evals_tot else 0.0,
                "mean_of_median_finite_tension": round(statistics.mean(med_finites), 4) if med_finites else 0.0,
                "mean_available_k": round(statistics.mean(med_availables) / 1000.0, 1) if med_availables else 0.0,
                "mean_commitments_k": round(statistics.mean(med_commitments) / 1000.0, 1) if med_commitments else 0.0,
                "mean_flow_k": round(statistics.mean(med_flows) / 1000.0, 1) if med_flows else 0.0,
                "mean_tau_months": round(statistics.mean(med_taus), 1) if med_taus else 0.0,
            }
        aggregated[arm] = agg_years

    print("\n" + "=" * 95)
    print("SONDE CONJOINTE CADENCE x TENSION (B7) : RAPPORT COMPARATIF PAR ANNEE")
    print("=" * 95)

    print("\n1. AMPLITUDE DE LA TENSION ARGENT (Moyenne des médianes de tension finie)")
    print(f"{'Année':<6} | {'Année jeu':<10} | {'cadence=365 (lente)':<22} | {'cadence=90 (rapide)':<22} | {'Écart (90 - 365)':<16}")
    print("-" * 85)
    for i, y in enumerate(range(STARTING_YEAR, STARTING_YEAR + args.years), 1):
        t365 = aggregated["cadence_365"][y]["mean_of_median_finite_tension"]
        t90 = aggregated["cadence_90"][y]["mean_of_median_finite_tension"]
        diff = t90 - t365
        print(f"Y{i:<5} | {y:<10} | {t365:<22.4f} | {t90:<22.4f} | {diff:+16.4f}")

    print("\n2. PART DES PROJETS AVEC TENSION ARGENT QUI MORD (>= 0.50 ou Infinie)")
    print(f"{'Année':<6} | {'Année jeu':<10} | {'cadence=365':<18} | {'cadence=90':<18} | {'Écart (% pts)':<16}")
    print("-" * 75)
    for i, y in enumerate(range(STARTING_YEAR, STARTING_YEAR + args.years), 1):
        b365 = aggregated["cadence_365"][y]["argent_binding_share_pct"]
        b90 = aggregated["cadence_90"][y]["argent_binding_share_pct"]
        diff = b90 - b365
        print(f"Y{i:<5} | {y:<10} | {b365:<17.1f}% | {b90:<17.1f}% | {diff:+15.1f}%")

    print("\n3. TRÉSORERIE DISPONIBLE MOYENNE (Cash + Emprunt mobilisable disponible)")
    print(f"{'Année':<6} | {'Année jeu':<10} | {'cadence=365':<18} | {'cadence=90':<18} | {'Écart (k£)':<16}")
    print("-" * 75)
    for i, y in enumerate(range(STARTING_YEAR, STARTING_YEAR + args.years), 1):
        a365 = aggregated["cadence_365"][y]["mean_available_k"]
        a90 = aggregated["cadence_90"][y]["mean_available_k"]
        diff = a90 - a365
        print(f"Y{i:<5} | {y:<10} | {a365:<16.1f}k£ | {a90:<16.1f}k£ | {diff:+14.1f}k£")

    print("\n4. RÉPARTITION DE LA RESSOURCE DOMINANTE (% des évaluations)")
    for arm_label, arm_key in [("Cadence 365 (Annuelle lente)", "cadence_365"),
                                ("Cadence 90 (Trimestrielle rapide)", "cadence_90")]:
        print(f"\n--- {arm_label} ---")
        print(f"{'Année':<6} | {'Évals':<7} | {'argent':<12} | {'slots_vehs':<12} | {'foncier':<12} | {'opcodes':<12}")
        print("-" * 70)
        for i, y in enumerate(range(STARTING_YEAR, STARTING_YEAR + args.years), 1):
            sy = aggregated[arm_key][y]
            ev = sy["evals_total"]
            sh = sy["dominant_share"]
            print(f"Y{i:<5} | {ev:<7} | {sh.get('argent', 0.0):<11.1f}% | {sh.get('slots_vehicules', 0.0):<11.1f}% | {sh.get('foncier', 0.0):<11.1f}% | {sh.get('opcodes', 0.0):<11.1f}%")

    print("\n5. BILAN ÉCONOMIQUE FINAL À 6 ANS (Moyenne sur 5 graines)")
    for metric in ["company_value", "profit_year"]:
        vals_365 = [financials["cadence_365"][s][metric] for s in args.seeds]
        vals_90 = [financials["cadence_90"][s][metric] for s in args.seeds]
        m365 = statistics.mean(vals_365)
        m90 = statistics.mean(vals_90)
        diff = m90 - m365
        pct = 100.0 * diff / m365
        print(f"  {metric:<16}: cadence_365={m365:10.0f} £ | cadence_90={m90:10.0f} £ | delta={diff:+10.0f} £ ({pct:+.1f}%)")

    payload = {
        "years": args.years,
        "seeds": args.seeds,
        "arms": list(arms_def.keys()),
        "aggregated": aggregated,
        "financials": {a: {str(s): v for s, v in d.items()} for a, d in financials.items()},
        "per_seed_results": {a: {str(s): v for s, v in d.items()} for a, d in results.items()},
        "errors": {k: v for k, v in all_errors.items()},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"\nRapport complet écrit dans : {args.out}")


if __name__ == "__main__":
    main()
