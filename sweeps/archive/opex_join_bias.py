"""Chiffre la sur-estimation de l'etage 1, et teste la cause qui lui etait attribuee.

CONTEXTE. Le banc apparie du 2026-08-29 (results/bench_v2_vivier.json) a montre que rouvrir le vivier
de candidats fait batir l'IA beaucoup plus (+37,2 % de vehicules, 18 graines sur 20) sans creer de
valeur (company_value -0,3 %). La cause SOUPCONNEE etait nommee dans ai/OpexAI/candidates.nut
(commentaire BIAIS CONNU) : quand une extremite reutilise une origine deja desservie, `monthly`
compte sa production ENTIERE et ignore ce que la ligne existante en prelevait deja. Ce script
teste cette hypothese -- et mesure ce que les donnees montrent a la place.

METHODE. Lit une ou plusieurs campagnes de sweeps/opex_full_campaign.py lancees AVEC
`--setting station_join=1` (le defaut est 0 depuis le verdict), et compare pour chaque ligne rail
le REEL de sa premiere annee pleine au PREDIT au moment de la construction. Le marqueur PJ donne
`origin_served`.

Pourquoi la PREMIERE annee pleine : la prediction part de la production observee juste avant la
construction. Les annees suivantes derivent avec la croissance des villes, ce qui melangerait le
biais cherche a un effet de calendrier -- or les lignes a origine servie naissent tard.

Trois lectures, dans l'ordre, parce que les deux premieres sont trompeuses seules :
  1. le rapport brut servie/libre ;
  2. le meme, A TYPE EGAL (l'etage 1 ne se trompe pas dans le meme sens sur le pax et sur le fret) ;
  3. un modele multiplicatif qui neutralise ENSEMBLE le type, la distance et l'epoque -- seul
     capable de dire ce qui revient a l'origine servie, puisque les lignes a origine servie sont
     aussi nettement plus longues (mediane 84 tuiles contre 47) et plus tardives.
"""
import argparse
import json
import math
import random
import statistics
from pathlib import Path

DISTANCE_BANDS = ((0, 50), (50, 75), (75, 100), (100, 300))
LATE_FROM = 1980


def first_full_year(line):
    """Premiere annee de la serie reelle : la ligne y a tourne douze mois."""
    series = line.get("actual_series") or {}
    if not series:
        return None, None
    year = min(series, key=int)
    return int(year), series[year]


def collect(paths):
    rows = []
    for path in paths:
        payload = json.loads(Path(path).read_text())
        settings = payload.get("ai_settings") or {}
        if settings.get("station_join") != 1:
            raise SystemExit(
                f"{path}: campagne sans station_join=1 (ai_settings={settings}). "
                "Le marqueur PJ n'est pas emis, il n'y a rien a ventiler."
            )
        for run in payload["runs"]:
            for line in run["lines"]:
                if line["mode"] != "rail":
                    continue
                if line.get("origin_served") is None:
                    continue  # panneau PJ absent : non mesure, jamais confondu avec "libre"
                year, actual = first_full_year(line)
                predicted = line.get("predicted") or {}
                revenue_pred = predicted.get("revenueAnnual")
                profit_pred = predicted.get("profitAnnual")
                if year is None or not revenue_pred or not line.get("distance"):
                    continue
                revenue = actual.get("revenue")
                if revenue is None:
                    continue
                rows.append({
                    "seed": run["seed"],
                    "line_index": line["line_index"],
                    "kind": predicted.get("kind"),
                    "distance": line["distance"],
                    "origin_served": line["origin_served"],
                    "joined_end": line.get("joined_end"),
                    "first_year": year,
                    "predicted_revenue": revenue_pred,
                    "actual_revenue": revenue,
                    "ratio": revenue / revenue_pred,
                    "predicted_profit": profit_pred,
                    "actual_profit": actual.get("profit"),
                    "profit_ratio": ((actual.get("profit") or 0) / profit_pred) if profit_pred else None,
                    "vehicles": actual.get("vehCount"),
                })
    return rows


def med(values):
    return statistics.median(values) if values else float("nan")


def bootstrap_factor(fresh, served, draws=20000, seed=20260829):
    """IC 95 % sur le rapport des medianes. Les groupes sont petits et dissymetriques : un rapport
    nu se lirait comme un resultat alors qu'il peut n'etre que du bruit d'echantillonnage."""
    if len(fresh) < 3 or len(served) < 3:
        return None
    rng = random.Random(seed)
    factors = []
    for _ in range(draws):
        f = statistics.median(rng.choices(fresh, k=len(fresh)))
        v = statistics.median(rng.choices(served, k=len(served)))
        if v > 0:
            factors.append(f / v)
    if not factors:
        return None
    factors.sort()
    return factors[int(0.025 * len(factors))], factors[int(0.975 * len(factors))]


def solve(matrix, vector):
    """Moindres carres par equations normales et pivot de Gauss. Pas de numpy : ce script doit
    tourner hors du conteneur de simulation, ou seule la bibliotheque standard est garantie."""
    n = len(matrix[0])
    ata = [[sum(row[i] * row[j] for row in matrix) for j in range(n)] for i in range(n)]
    atb = [sum(row[i] * value for row, value in zip(matrix, vector)) for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(ata[r][col]))
        if abs(ata[pivot][col]) < 1e-12:
            return None
        ata[col], ata[pivot] = ata[pivot], ata[col]
        atb[col], atb[pivot] = atb[pivot], atb[col]
        for r in range(n):
            if r == col:
                continue
            factor = ata[r][col] / ata[col][col]
            for c in range(col, n):
                ata[r][c] -= factor * ata[col][c]
            atb[r] -= factor * atb[col]
    return [atb[i] / ata[i][i] for i in range(n)]


TERMS = ("const", "freight", "log(distance)", "decennie", "origine_servie")


def design(rows):
    matrix, vector = [], []
    for r in rows:
        matrix.append([1.0,
                       1.0 if r["kind"] == "freight" else 0.0,
                       math.log(r["distance"]),
                       (r["first_year"] - LATE_FROM) / 10.0,
                       1.0 if r["origin_served"] else 0.0])
        vector.append(math.log(r["ratio"]))
    return matrix, vector


def model(rows, draws=4000, seed=20260829):
    usable = [r for r in rows if r["ratio"] > 0]
    matrix, vector = design(usable)
    beta = solve(matrix, vector)
    if beta is None:
        return None
    rng = random.Random(seed)
    draws_beta = []
    for _ in range(draws):
        sample = [usable[rng.randrange(len(usable))] for _ in usable]
        m, v = design(sample)
        b = solve(m, v)
        if b is not None:
            draws_beta.append(b)
    out = {}
    for i, name in enumerate(TERMS):
        column = sorted(d[i] for d in draws_beta)
        out[name] = {
            "effet": math.exp(beta[i]),
            "ic95": [math.exp(column[int(0.025 * len(column))]),
                     math.exp(column[int(0.975 * len(column))])],
        }
    return {"n": len(usable), "n_exclus_ratio_non_positif": len(rows) - len(usable), "terms": out}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("campaigns", nargs="+", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    rows = collect(args.campaigns)
    served = [r["ratio"] for r in rows if r["origin_served"]]
    fresh = [r["ratio"] for r in rows if not r["origin_served"]]
    print(f"lignes rail retenues : {len(rows)} "
          f"({len(served)} a origine servie, {len(fresh)} libres)\n")

    print("--- 1. lecture brute (TROMPEUSE, gardee pour montrer d'ou vient l'illusion) ---")
    span = bootstrap_factor(fresh, served)
    naive = med(fresh) / med(served) if served and fresh else float("nan")
    print(f"libre {med(fresh):.3f}  servie {med(served):.3f}  facteur {naive:.2f}x"
          + (f"  IC 95 % [{span[0]:.2f} ; {span[1]:.2f}]" if span else ""))

    print("\n--- 2. a type egal ---")
    per_kind = {}
    for kind in ("pax", "freight"):
        f = [r["ratio"] for r in rows if not r["origin_served"] and r["kind"] == kind]
        v = [r["ratio"] for r in rows if r["origin_served"] and r["kind"] == kind]
        if not f or not v:
            print(f"{kind:<9} n libre={len(f)}, n servie={len(v)} -- insuffisant")
            continue
        span = bootstrap_factor(f, v)
        per_kind[kind] = {"n_fresh": len(f), "n_served": len(v), "median_fresh": med(f),
                          "median_served": med(v), "factor": med(f) / med(v),
                          "ci95": list(span) if span else None}
        print(f"{kind:<9} libre {med(f):.3f} (n={len(f)})  servie {med(v):.3f} (n={len(v)})  "
              f"facteur {med(f)/med(v):.2f}x"
              + (f"  IC 95 % [{span[0]:.2f} ; {span[1]:.2f}]" if span else ""))

    print("\n--- 3. le confondant : les lignes a origine servie sont plus LONGUES et plus TARDIVES ---")
    for label, sel in (("libre", False), ("servie", True)):
        group = [r for r in rows if r["origin_served"] == sel]
        print(f"{label:<9} distance mediane {med([r['distance'] for r in group]):.0f}  "
              f"annee mediane {med([r['first_year'] for r in group]):.0f}")

    print("\n  profit REEL / profit PREDIT, par bande de distance (toutes lignes confondues)")
    bands = {}
    for lo, hi in DISTANCE_BANDS:
        band = [r["profit_ratio"] for r in rows
                if r["profit_ratio"] is not None and lo <= r["distance"] < hi]
        bands[f"{lo}-{hi}"] = {"n": len(band), "median_profit_ratio": med(band)}
        print(f"    {lo:>3}-{hi:<3} {med(band):>6.2f}  (n={len(band)})")

    print("\n  et croise avec l'epoque")
    print(f"    {'bande':<9} {'avant ' + str(LATE_FROM):>16} {str(LATE_FROM) + '+':>16}")
    for lo, hi in DISTANCE_BANDS:
        early = [r["profit_ratio"] for r in rows if r["profit_ratio"] is not None
                 and lo <= r["distance"] < hi and r["first_year"] < LATE_FROM]
        late = [r["profit_ratio"] for r in rows if r["profit_ratio"] is not None
                and lo <= r["distance"] < hi and r["first_year"] >= LATE_FROM]
        print(f"    {f'{lo}-{hi}':<9} {f'{med(early):.2f} (n={len(early)})':>16} "
              f"{f'{med(late):.2f} (n={len(late)})':>16}")

    print("\n--- 4. modele multiplicatif : ce qui revient VRAIMENT a l'origine servie ---")
    fitted = model(rows)
    if fitted:
        print(f"log(revenu reel / revenu predit) ~ type + log(distance) + epoque + origine_servie"
              f"   (n={fitted['n']})")
        for name, item in fitted["terms"].items():
            print(f"  {name:<15} x{item['effet']:.2f}   IC 95 % "
                  f"[{item['ic95'][0]:.2f} ; {item['ic95'][1]:.2f}]")

    payload = {
        "campaigns": [str(p) for p in args.campaigns],
        "metric": "revenu reel de la premiere annee pleine / revenueAnnual predit",
        "n_lines": len(rows),
        "naive_factor": naive,
        "by_kind": per_kind,
        "profit_ratio_by_distance_band": bands,
        "controlled_model": fitted,
        "lines": rows,
    }
    if args.out:
        args.out.write_text(json.dumps(payload, indent=2))
        print(f"\necrit {args.out}")


if __name__ == "__main__":
    main()
