"""C78 : Analyse diagnostique ligne par ligne contre AAAHogEx.

Pour chaque graine et pour les annees 1973 et 1975 :
- selectionne les 20 lignes les plus rentables d'AAAHogEx (profit_last_year) ;
- pour chacune (mode, paire non ordonnee, vehicules, profit) :
  * recherche dans le vivier C78_CAND de la meme annee un candidat OpexAI correspondant
    (present ? rang, P predit, C, financable) ;
  * recherche une ligne OpexAI construite sur la meme paire
    (vehicules, profit, aeroport) ;
  * classe chaque ligne en :
    ABSENT (jamais genere)
    GÉNÉRÉ_NON_CONSTRUIT (avec rang et P)
    CONSTRUIT_MOINS_RENTABLE (profit OpexAI < 50 % de celui d'AAAHogEx)
    CONSTRUIT_COMPARABLE (profit OpexAI >= 50 %)
- publie les comptes par classe et par mode, le rapport P_predit / profit_AAA,
  et pour les lignes moins rentables le detail des vehicules et types d'aeroport.
"""
import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "results" / "diag_c78_lines_vs_aaa.json"
TARGET_YEARS = (1973, 1975)


def get_line_pair(line):
    towns = line.get("towns") or []
    if len(towns) >= 2:
        return tuple(sorted(int(t) for t in towns[:2]))
    if len(towns) == 1:
        return (int(towns[0]), int(towns[0]))
    return ()


def get_candidate_pair(cand):
    town_a = cand.get("townA", -1)
    town_b = cand.get("townB", -1)
    if town_a >= 0 and town_b >= 0:
        return tuple(sorted([int(town_a), int(town_b)]))
    ind_a = cand.get("indA", -1)
    ind_b = cand.get("indB", -1)
    if ind_a >= 0 and ind_b >= 0:
        return tuple(sorted([int(ind_a), int(ind_b)]))
    return ()


def classify_aaa_line(aaa_line, opex_built_lines, opex_candidates):
    mode = aaa_line.get("mode")
    aaa_pair = get_line_pair(aaa_line)
    aaa_profit = float(aaa_line.get("profit_last_year", 0.0))

    # 1. Recherche d'une ligne OpexAI construite sur la meme paire et le meme mode
    built_match = None
    if aaa_pair != ():
        for ol in opex_built_lines:
            if ol.get("mode") == mode and get_line_pair(ol) == aaa_pair:
                if built_match is None or ol.get("profit_last_year", 0.0) > built_match.get("profit_last_year", 0.0):
                    built_match = ol

    # 2. Recherche dans le vivier de candidats OpexAI C78_CAND de la meme annee
    cand_match = None
    if aaa_pair != ():
        for c in opex_candidates:
            if c.get("mode") == mode and get_candidate_pair(c) == aaa_pair:
                if cand_match is None:
                    cand_match = c
                else:
                    # On prefere le meilleur rang dans best, puis le plus fort P
                    r_new = c.get("rank", -1)
                    r_old = cand_match.get("rank", -1)
                    if (r_old < 0 <= r_new) or (0 <= r_new < r_old) or (r_new == r_old and c.get("P", 0) > cand_match.get("P", 0)):
                        cand_match = c

    # 3. Classification mutuellement exclusive
    if built_match is not None:
        opex_profit = float(built_match.get("profit_last_year", 0.0))
        if opex_profit < 0.5 * aaa_profit:
            cls = "CONSTRUIT_MOINS_RENTABLE"
        else:
            cls = "CONSTRUIT_COMPARABLE"
    else:
        if cand_match is not None:
            cls = "GÉNÉRÉ_NON_CONSTRUIT"
        else:
            cls = "ABSENT"

    return {
        "classification": cls,
        "mode": mode,
        "pair": list(aaa_pair),
        "aaa_profit": aaa_profit,
        "aaa_vehicles": aaa_line.get("vehicles", 0),
        "aaa_airport_types": aaa_line.get("airport_types", []),
        "built_match": built_match,
        "cand_match": cand_match,
    }


def analyse_snapshots(snapshots, target_years=TARGET_YEARS):
    index = {}
    for row in snapshots:
        seed = row.get("seed")
        year = row.get("year")
        if seed is not None and year is not None:
            index[(seed, year)] = row

    results = []
    for (seed, year), row in sorted(index.items()):
        if year not in target_years:
            continue
        companies = row.get("companies", {})
        aaa_data = companies.get("1") or companies.get(1) or {}
        opex_data = companies.get("0") or companies.get(0) or {}
        candidates = row.get("candidates", [])

        aaa_lines = list(aaa_data.get("lines", []))
        aaa_lines.sort(key=lambda l: float(l.get("profit_last_year", 0.0)), reverse=True)
        top20 = aaa_lines[:20]

        opex_built = opex_data.get("lines", [])

        for line in top20:
            info = classify_aaa_line(line, opex_built, candidates)
            info["seed"] = seed
            info["year"] = year
            results.append(info)

    return results


def summarize_results(results):
    classes = ("ABSENT", "GÉNÉRÉ_NON_CONSTRUIT", "CONSTRUIT_MOINS_RENTABLE", "CONSTRUIT_COMPARABLE")
    counts = {c: defaultdict(int) for c in classes}
    all_modes = set()

    for item in results:
        cls = item["classification"]
        mode = item.get("mode", "unknown")
        counts[cls][mode] += 1
        all_modes.add(mode)

    sorted_modes = sorted(all_modes)

    # Ratios P predit / profit reel AAA pour GÉNÉRÉ_NON_CONSTRUIT
    ratios_gen = []
    gen_details = []
    for item in results:
        if item["classification"] == "GÉNÉRÉ_NON_CONSTRUIT":
            cand = item.get("cand_match") or {}
            p_pred = cand.get("P", 0)
            p_aaa = item.get("aaa_profit", 0.0)
            ratio = (p_pred / p_aaa) if p_aaa > 0 else None
            gen_details.append({
                "seed": item["seed"],
                "year": item["year"],
                "mode": item["mode"],
                "pair": item["pair"],
                "rank": cand.get("rank", -1),
                "P_pred": p_pred,
                "C": cand.get("C", 0),
                "affordable": cand.get("affordable", 0),
                "AAA_profit": p_aaa,
                "ratio_P_over_AAA": ratio,
            })
            if ratio is not None:
                ratios_gen.append(ratio)

    # Details pour CONSTRUIT_MOINS_RENTABLE
    moins_rentable_details = []
    for item in results:
        if item["classification"] == "CONSTRUIT_MOINS_RENTABLE":
            bm = item.get("built_match") or {}
            moins_rentable_details.append({
                "seed": item["seed"],
                "year": item["year"],
                "mode": item["mode"],
                "pair": item["pair"],
                "aaa_profit": item["aaa_profit"],
                "opex_profit": bm.get("profit_last_year", 0.0),
                "aaa_vehicles": item["aaa_vehicles"],
                "opex_vehicles": bm.get("vehicles", 0),
                "aaa_airport_types": item["aaa_airport_types"],
                "opex_airport_types": bm.get("airport_types", []),
            })

    return {
        "classes": classes,
        "modes": sorted_modes,
        "counts": {c: dict(counts[c]) for c in classes},
        "total_by_class": {c: sum(counts[c].values()) for c in classes},
        "total_lines_analyzed": len(results),
        "ratios_gen": {
            "count": len(ratios_gen),
            "median": statistics.median(ratios_gen) if ratios_gen else None,
            "mean": statistics.mean(ratios_gen) if ratios_gen else None,
            "min": min(ratios_gen) if ratios_gen else None,
            "max": max(ratios_gen) if ratios_gen else None,
        },
        "gen_details": gen_details,
        "moins_rentable_details": moins_rentable_details,
    }


def print_report(summary):
    print("=" * 78)
    print(" C78 : DIAGNOSTIC LIGNE PAR LIGNE OPEXAI VS AAAHOGEX (1973, 1975)")
    print("=" * 78)
    print(f"Total des lignes AAAHogEx analysees (top 20 / an / graine) : {summary['total_lines_analyzed']}")
    print()

    # Tableau des comptes par classe et par mode
    modes = summary["modes"]
    header = f"{'Classe':<26} | " + " | ".join(f"{m:>6}" for m in modes) + " | Total"
    print(header)
    print("-" * len(header))
    for c in summary["classes"]:
        row_modes = " | ".join(f"{summary['counts'][c].get(m, 0):>6}" for m in modes)
        tot = summary["total_by_class"][c]
        print(f"{c:<26} | {row_modes} | {tot:>5}")
    print("-" * len(header))
    print()

    # Section GÉNÉRÉ_NON_CONSTRUIT
    gen = summary["ratios_gen"]
    print("--- [GÉNÉRÉ_NON_CONSTRUIT] : Evaluation d'OpexAI vs profit reel d'AAAHogEx ---")
    print(f"Nombre de lignes : {gen['count']}")
    if gen['count'] > 0:
        med_str = f"{gen['median']:.2f}" if gen['median'] is not None else "N/A"
        mean_str = f"{gen['mean']:.2f}" if gen['mean'] is not None else "N/A"
        min_str = f"{gen['min']:.2f}" if gen['min'] is not None else "N/A"
        max_str = f"{gen['max']:.2f}" if gen['max'] is not None else "N/A"
        print(f"Rapport P predit / profit reel AAA : mediane={med_str}, moyenne={mean_str}, min={min_str}, max={max_str}")
        print()
        print(f"  {'Graine':>6} {'An':>4} {'Mode':>5} {'Paire':>12} {'Rang':>5} {'P predit':>10} {'C':>8} {'Fin':>3} {'AAA profit':>11} {'P/AAA':>8}")
        for d in summary["gen_details"][:25]:
            r_str = f"{d['ratio_P_over_AAA']:.2f}" if d['ratio_P_over_AAA'] is not None else "N/A"
            pair_str = f"({d['pair'][0]},{d['pair'][1]})" if len(d['pair']) >= 2 else str(d['pair'])
            print(f"  {d['seed']:>6} {d['year']:>4} {d['mode']:>5} {pair_str:>12} {d['rank']:>5} {d['P_pred']:>10} {d['C']:>8} {d['affordable']:>3} {int(d['AAA_profit']):>11} {r_str:>8}")
        if len(summary["gen_details"]) > 25:
            print(f"  ... ({len(summary['gen_details']) - 25} lignes supplementaires)")
    print()

    # Section CONSTRUIT_MOINS_RENTABLE
    mr = summary["moins_rentable_details"]
    print("--- [CONSTRUIT_MOINS_RENTABLE] : Vehicules et aeroports des deux cotes ---")
    print(f"Nombre de lignes : {len(mr)}")
    if mr:
        print(f"  {'Graine':>6} {'An':>4} {'Mode':>5} {'Paire':>12} {'Opex £':>9} {'AAA £':>9} {'Vehi O/A':>8} {'Aeroports Opex':>16} {'Aeroports AAA':>16}")
        for d in mr:
            pair_str = f"({d['pair'][0]},{d['pair'][1]})" if len(d['pair']) >= 2 else str(d['pair'])
            vehs_str = f"{d['opex_vehicles']}/{d['aaa_vehicles']}"
            op_ap = ",".join(str(t) for t in d['opex_airport_types']) if d['opex_airport_types'] else "-"
            aaa_ap = ",".join(str(t) for t in d['aaa_airport_types']) if d['aaa_airport_types'] else "-"
            print(f"  {d['seed']:>6} {d['year']:>4} {d['mode']:>5} {pair_str:>12} {int(d['opex_profit']):>9} {int(d['aaa_profit']):>9} {vehs_str:>8} {op_ap:>16} {aaa_ap:>16}")
    print("=" * 78)


def run_selftest():
    mock_snapshots = [
        {
            "seed": 42,
            "year": 1973,
            "date": "1973-12-31",
            "candidates": [
                # Candidat généré non construit (pair 10, 20)
                {"year": 1973, "mode": "air", "townA": 10, "townB": 20, "indA": -1, "indB": -1, "P": 120000, "C": 45000, "rank": 2, "affordable": 1},
                # Candidat généré construit (pair 30, 40)
                {"year": 1973, "mode": "air", "townA": 40, "townB": 30, "indA": -1, "indB": -1, "P": 80000, "C": 40000, "rank": 0, "affordable": 1},
                # Candidat généré construit comparable (pair 50, 60)
                {"year": 1973, "mode": "road", "townA": 50, "townB": 60, "indA": -1, "indB": -1, "P": 30000, "C": 10000, "rank": 1, "affordable": 1},
            ],
            "companies": {
                "0": {
                    "lines": [
                        # Construit mais moins rentable (40k vs 100k AAA -> 40%)
                        {"mode": "air", "towns": [30, 40], "vehicles": 1, "profit_last_year": 40000.0, "airports": [{"type": 0}, {"type": 0}], "airport_types": [0, 0]},
                        # Construit comparable (25k vs 30k AAA -> 83%)
                        {"mode": "road", "towns": [60, 50], "vehicles": 3, "profit_last_year": 25000.0, "airports": [], "airport_types": []},
                    ]
                },
                "1": {
                    "lines": [
                        # Ligne AAA 1 : pair (10, 20) -> GÉNÉRÉ_NON_CONSTRUIT
                        {"mode": "air", "towns": [20, 10], "vehicles": 3, "profit_last_year": 150000.0, "airports": [{"type": 1}, {"type": 1}], "airport_types": [1, 1]},
                        # Ligne AAA 2 : pair (30, 40) -> CONSTRUIT_MOINS_RENTABLE (Opex 40k < 50% de 100k)
                        {"mode": "air", "towns": [30, 40], "vehicles": 2, "profit_last_year": 100000.0, "airports": [{"type": 1}, {"type": 1}], "airport_types": [1, 1]},
                        # Ligne AAA 3 : pair (50, 60) -> CONSTRUIT_COMPARABLE (Opex 25k >= 50% de 30k)
                        {"mode": "road", "towns": [50, 60], "vehicles": 2, "profit_last_year": 30000.0, "airports": [], "airport_types": []},
                        # Ligne AAA 4 : pair (70, 80) -> ABSENT
                        {"mode": "rail", "towns": [70, 80], "vehicles": 4, "profit_last_year": 200000.0, "airports": [], "airport_types": []},
                    ]
                }
            }
        }
    ]

    results = analyse_snapshots(mock_snapshots, target_years=(1973,))
    assert len(results) == 4, f"Expected 4 results, got {len(results)}"

    by_class = {r["pair"][0]: r["classification"] for r in results}
    # Pairs ordonnees: (10, 20), (30, 40), (50, 60), (70, 80)
    assert by_class[10] == "GÉNÉRÉ_NON_CONSTRUIT", f"Expected GÉNÉRÉ_NON_CONSTRUIT for pair 10-20, got {by_class[10]}"
    assert by_class[30] == "CONSTRUIT_MOINS_RENTABLE", f"Expected CONSTRUIT_MOINS_RENTABLE for pair 30-40, got {by_class[30]}"
    assert by_class[50] == "CONSTRUIT_COMPARABLE", f"Expected CONSTRUIT_COMPARABLE for pair 50-60, got {by_class[50]}"
    assert by_class[70] == "ABSENT", f"Expected ABSENT for pair 70-80, got {by_class[70]}"

    summary = summarize_results(results)
    assert summary["total_by_class"]["GÉNÉRÉ_NON_CONSTRUIT"] == 1
    assert summary["total_by_class"]["CONSTRUIT_MOINS_RENTABLE"] == 1
    assert summary["total_by_class"]["CONSTRUIT_COMPARABLE"] == 1
    assert summary["total_by_class"]["ABSENT"] == 1

    # Verifier calcul ratio P predit / profit reel AAA
    # P predit = 120 000, AAA profit = 150 000 -> ratio = 0.8
    assert len(summary["gen_details"]) == 1
    assert abs(summary["gen_details"][0]["ratio_P_over_AAA"] - 0.8) < 1e-5

    # Verifier comparaison vehicules et aeroports pour CONSTRUIT_MOINS_RENTABLE
    assert len(summary["moins_rentable_details"]) == 1
    mr = summary["moins_rentable_details"][0]
    assert mr["aaa_vehicles"] == 2
    assert mr["opex_vehicles"] == 1
    assert mr["aaa_airport_types"] == [1, 1]
    assert mr["opex_airport_types"] == [0, 0]

    print("analyse_c78 selftest passed: all 4 classes, unordered pairing, ratios, vehicles and airport types verified.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="input_file", type=Path, default=DEFAULT_IN,
                        help=f"Chemin du fichier JSON produit par diag_c78_lines_vs_aaa.py (defaut: {DEFAULT_IN})")
    parser.add_argument("--years", nargs="+", type=int, default=list(TARGET_YEARS),
                        help=f"Annees a analyser (defaut: {list(TARGET_YEARS)})")
    parser.add_argument("--json-out", type=Path, default=None,
                        help="Chemin optionnel pour sauvegarder le resume en JSON")
    parser.add_argument("--selftest", action="store_true",
                        help="Lance les tests internes sans dependance externe")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    if not args.input_file.exists():
        sys.exit(f"Erreur : fichier introuvable {args.input_file}. Executez d'abord diag_c78_lines_vs_aaa.py.")

    data = json.loads(args.input_file.read_text(encoding="utf-8"))
    results = analyse_snapshots(data, target_years=tuple(args.years))
    summary = summarize_results(results)
    print_report(summary)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"Rapport JSON enregistre : {args.json_out}")


if __name__ == "__main__":
    main()
