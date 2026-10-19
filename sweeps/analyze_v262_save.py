#!/usr/bin/env python3
"""sweeps/analyze_v262_save.py - Analyse du coût en opcodes de Save() (V262 T04).

Lit les journaux moteur d'une campagne (.log et .log.gz), extrait les événements
`V262_SAVE ops=<consommés> budget=100000 lines=<L> abandons=<A> abandonCounts=<H> tasks=<n> full=<save_full_state>`,
et produit :
1. Par graine et par année : max et médiane de ops, L, A, H, et marge au budget (100k - ops).
2. Extrapolation linéaire de ops en fonction de L+A+H, avec l'année où le budget serait atteint.

Conforme à docs/fair_play_audit_20261018.md §6.3 et script_info.hpp:19 (MAX_SL_OPS = 100000).
"""

import argparse
import gzip
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

# Expression régulière pour les lignes V262_SAVE :
# Formats reconnus :
# - OPEX YYYY-MM-DD V262_SAVE ops=... budget=... lines=... abandons=... abandonCounts=... tasks=... full=...
# - [prefix] OPEX YYYY-M-D V262_SAVE ...
# - V262_SAVE ops=...
SAVE_RE = re.compile(
    r"(?:OPEX\s+(?P<date>(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2}))\s+)?"
    r"V262_SAVE\s+(?P<fields>[^\r\n]+)"
)

KV_RE = re.compile(r"(\w+)=(\S+)")


def extract_seed_from_filename(filename: Union[str, Path]) -> str:
    """Extrait l'identifiant de graine à partir du nom de fichier ou de chemin."""
    stem = Path(filename).name
    if stem.endswith(".gz"):
        stem = stem[:-3]
    if stem.endswith(".log"):
        stem = stem[:-4]
    # Patterns: seed_42, seed42, s42, _s42_
    m = re.search(r"(?:seed[_-]?|(?<=_s)|(?<=^s))(\d+)", stem, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d+)\b", stem)
    if m:
        return m.group(1)
    return stem


def parse_v262_save_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse une ligne brute de journal contenant un événement V262_SAVE.

    Retourne un dictionnaire avec :
    - year (int), month (int), day (int) si daté
    - ops (int), budget (int, défaut 100000)
    - lines (int), abandons (int), abandonCounts (int), tasks (int), full (int)
    - lah (int) = lines + abandons + abandonCounts
    - margin (int) = budget - ops
    """
    m = SAVE_RE.search(line)
    if not m:
        return None

    fields_str = m.group("fields")
    fields = {}
    for k, v in KV_RE.findall(fields_str):
        try:
            fields[k] = int(v)
        except ValueError:
            try:
                fields[k] = float(v)
            except ValueError:
                fields[k] = v

    year = int(m.group("year")) if m.group("year") else fields.get("year", 0)
    month = int(m.group("month")) if m.group("month") else fields.get("month", 1)
    day = int(m.group("day")) if m.group("day") else fields.get("day", 1)

    ops = int(fields.get("ops", 0))
    budget = int(fields.get("budget", 100000))
    lines_cnt = int(fields.get("lines", 0))
    abandons_cnt = int(fields.get("abandons", 0))
    abandon_counts_cnt = int(fields.get("abandonCounts", 0))
    tasks_cnt = int(fields.get("tasks", 0))
    full = int(fields.get("full", 1))

    lah = lines_cnt + abandons_cnt + abandon_counts_cnt
    margin = budget - ops

    return {
        "year": year,
        "month": month,
        "day": day,
        "ops": ops,
        "budget": budget,
        "lines": lines_cnt,
        "abandons": abandons_cnt,
        "abandonCounts": abandon_counts_cnt,
        "tasks": tasks_cnt,
        "full": full,
        "lah": lah,
        "margin": margin,
    }


def parse_log_file(path: Union[str, Path], seed_override: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lit un fichier .log ou .log.gz et extrait tous les événements V262_SAVE."""
    path = Path(path)
    seed = seed_override if seed_override is not None else extract_seed_from_filename(path)
    events = []

    if path.suffix == ".gz":
        open_fn = lambda: gzip.open(path, "rt", encoding="utf-8", errors="replace")
    else:
        open_fn = lambda: open(path, "r", encoding="utf-8", errors="replace")

    with open_fn() as f:
        for line in f:
            if "V262_SAVE" in line:
                parsed = parse_v262_save_line(line)
                if parsed:
                    parsed["seed"] = seed
                    parsed["file"] = str(path)
                    events.append(parsed)

    return events


def aggregate_by_seed_year(events: List[Dict[str, Any]]) -> Dict[Tuple[str, int], Dict[str, Any]]:
    """Agrège les événements par (graine, année) et calcule max et médiane.

    Sorties par (graine, année) :
    - ops: max, median
    - lines (L): max, median
    - abandons (A): max, median
    - abandonCounts (H): max, median
    - margin: min, median (marge au budget = budget - ops)
    - lah (L+A+H): max, median
    """
    groups: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}
    for ev in events:
        key = (str(ev.get("seed", "unknown")), int(ev.get("year", 0)))
        if key not in groups:
            groups[key] = []
        groups[key].append(ev)

    aggregated = {}
    for (seed, year), rows in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1])):
        ops_list = [r["ops"] for r in rows]
        l_list = [r["lines"] for r in rows]
        a_list = [r["abandons"] for r in rows]
        h_list = [r["abandonCounts"] for r in rows]
        margin_list = [r["margin"] for r in rows]
        lah_list = [r["lah"] for r in rows]
        budget = rows[0]["budget"] if rows else 100000

        aggregated[(seed, year)] = {
            "seed": seed,
            "year": year,
            "count": len(rows),
            "budget": budget,
            "ops_max": max(ops_list),
            "ops_med": statistics.median(ops_list),
            "l_max": max(l_list),
            "l_med": statistics.median(l_list),
            "a_max": max(a_list),
            "a_med": statistics.median(a_list),
            "h_max": max(h_list),
            "h_med": statistics.median(h_list),
            "lah_max": max(lah_list),
            "lah_med": statistics.median(lah_list),
            "margin_min": min(margin_list),
            "margin_med": statistics.median(margin_list),
        }

    return aggregated


def linear_regression(xs: List[float], ys: List[float]) -> Tuple[float, float, float]:
    """Régression linéaire standard Y = alpha * X + beta.

    Retourne (alpha, beta, r_squared).
    """
    n = len(xs)
    if n < 2:
        mean_y = ys[0] if n == 1 else 0.0
        return 0.0, float(mean_y), 0.0

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    ss_yy = sum((y - mean_y) ** 2 for y in ys)
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))

    if ss_xx == 0.0:
        return 0.0, float(mean_y), 0.0

    alpha = ss_xy / ss_xx
    beta = mean_y - alpha * mean_x

    if ss_yy > 0.0:
        r2 = (ss_xy ** 2) / (ss_xx * ss_yy)
    else:
        r2 = 1.0 if ss_xy == 0.0 else 0.0

    return float(alpha), float(beta), float(r2)


def extrapolate_ops_vs_lah(
    events: List[Dict[str, Any]],
    budget: int = 100000,
) -> Dict[str, Any]:
    """Effectue l'extrapolation linéaire de ops en fonction de L+A+H et projette l'année du budget.

    Modèles calculés :
    1. ops = alpha * (L+A+H) + beta
    2. (L+A+H) en fonction de l'année : (L+A+H)(t) = m * t + c
    3. Année où budget est atteint :
       - via croissance d'état : t_budget = (X_crit - c) / m avec X_crit = (budget - beta) / alpha
       - via régression directe de ops sur l'année : ops(t) = a_direct * t + b_direct
    """
    if not events:
        return {
            "n_points": 0,
            "alpha": 0.0,
            "beta": 0.0,
            "r2": 0.0,
            "x_crit": None,
            "m_lah_per_year": 0.0,
            "c_lah": 0.0,
            "r2_lah_growth": 0.0,
            "year_budget_reached_via_lah": None,
            "direct_slope_ops_year": 0.0,
            "direct_intercept_ops": 0.0,
            "r2_direct": 0.0,
            "year_budget_reached_direct": None,
        }

    xs_lah = [float(ev["lah"]) for ev in events]
    ys_ops = [float(ev["ops"]) for ev in events]
    ts_year = [float(ev["year"]) + (float(ev.get("month", 1)) - 1.0) / 12.0 for ev in events]

    # 1. ops = alpha * (L+A+H) + beta
    alpha, beta, r2_lah = linear_regression(xs_lah, ys_ops)

    x_crit = None
    if alpha > 0.0:
        x_crit = (budget - beta) / alpha

    # 2. Croissance de (L+A+H) au fil des années
    m_lah, c_lah, r2_lah_growth = linear_regression(ts_year, xs_lah)

    year_reached_via_lah = None
    if x_crit is not None and m_lah > 0.0:
        year_reached_via_lah = (x_crit - c_lah) / m_lah

    # 3. Régression directe de ops sur l'année
    a_ops, b_ops, r2_direct = linear_regression(ts_year, ys_ops)

    year_reached_direct = None
    if a_ops > 0.0:
        year_reached_direct = (budget - b_ops) / a_ops

    return {
        "n_points": len(events),
        "alpha": alpha,
        "beta": beta,
        "r2": r2_lah,
        "x_crit": x_crit,
        "m_lah_per_year": m_lah,
        "c_lah": c_lah,
        "r2_lah_growth": r2_lah_growth,
        "year_budget_reached_via_lah": year_reached_via_lah,
        "direct_slope_ops_year": a_ops,
        "direct_intercept_ops": b_ops,
        "r2_direct": r2_direct,
        "year_budget_reached_direct": year_reached_direct,
    }


def find_log_files(targets: List[str]) -> List[Path]:
    """Résout une liste de chemins, dossiers ou noms de campagnes en fichiers .log/.log.gz."""
    files: List[Path] = []
    for target in targets:
        p = Path(target)
        if p.is_file():
            if p.name.endswith(".log") or p.name.endswith(".log.gz"):
                files.append(p)
        elif p.is_dir():
            files.extend(sorted(p.rglob("*.log")))
            files.extend(sorted(p.rglob("*.log.gz")))
        else:
            # Essayer sous results/<target>
            res_p = Path("results") / target
            if res_p.is_dir():
                files.extend(sorted(res_p.rglob("*.log")))
                files.extend(sorted(res_p.rglob("*.log.gz")))
    return sorted(set(files))


def format_report_markdown(
    aggregated: Dict[Tuple[str, int], Dict[str, Any]],
    extrapolation: Dict[str, Any],
    budget: int = 100000,
) -> str:
    """Met en forme les résultats sous forme d'un tableau et d'une analyse Markdown."""
    lines = []
    lines.append("# Analyse du Coût de Save() (V262 T04)")
    lines.append(f"Budget moteur MAX_SL_OPS : {budget:,} opcodes (script_info.hpp:19)\n")

    lines.append("## 1. Métriques par graine et par année")
    lines.append("| Graine | Année | Événements | Ops (max / méd) | Marge (min / méd) | L (max / méd) | A (max / méd) | H (max / méd) | L+A+H (max / méd) |")
    lines.append("|-------:|------:|-----------:|----------------:|------------------:|--------------:|--------------:|--------------:|------------------:|")

    for (seed, year), row in sorted(aggregated.items(), key=lambda x: (x[0][0], x[0][1])):
        ops_str = f"{row['ops_max']:,} / {int(row['ops_med']):,}"
        margin_str = f"{row['margin_min']:,} / {int(row['margin_med']):,}"
        l_str = f"{row['l_max']} / {int(row['l_med'])}"
        a_str = f"{row['a_max']} / {int(row['a_med'])}"
        h_str = f"{row['h_max']} / {int(row['h_med'])}"
        lah_str = f"{row['lah_max']} / {int(row['lah_med'])}"

        lines.append(
            f"| {seed:>6} | {year:>5} | {row['count']:>10} | {ops_str:>15} | {margin_str:>17} | {l_str:>13} | {a_str:>13} | {h_str:>13} | {lah_str:>17} |"
        )

    lines.append("\n## 2. Extrapolation linéaire et épuisement du budget")
    n = extrapolation["n_points"]
    lines.append(f"- **Nombre de points analysés** : {n}")
    if n >= 2:
        alpha = extrapolation["alpha"]
        beta = extrapolation["beta"]
        r2 = extrapolation["r2"]
        lines.append(f"- **Modèle de coût** : `ops = {alpha:.3f} * (L+A+H) + {beta:.1f}` (R² = {r2:.4f})")
        lines.append(f"  - Coût marginal par item d'état (L+A+H) : **{alpha:.2f} opcodes / élément**")
        lines.append(f"  - Coût fixe de base (ordonnancement, C69/C75, queues) : **{beta:.1f} opcodes**")

        x_crit = extrapolation["x_crit"]
        if x_crit is not None:
            lines.append(f"  - Taille critique d'état (L+A+H) pour atteindre le budget ({budget:,} ops) : **{int(math.ceil(x_crit)):,} éléments**")
        else:
            lines.append("  - Taille critique : N/A (pente <= 0)")

        m_lah = extrapolation["m_lah_per_year"]
        c_lah = extrapolation["c_lah"]
        lines.append(f"- **Croissance de l'état (L+A+H)** : `{m_lah:+.2f} éléments / an` (R² = {extrapolation['r2_lah_growth']:.4f})")

        y_via_lah = extrapolation["year_budget_reached_via_lah"]
        if y_via_lah is not None:
            lines.append(f"- **Année projetée d'épuisement du budget (via L+A+H)** : **{y_via_lah:.1f}**")
        else:
            lines.append("- **Année projetée d'épuisement (via L+A+H)** : **Aucun épuisement projeté (pente <= 0)**")

        a_dir = extrapolation["direct_slope_ops_year"]
        b_dir = extrapolation["direct_intercept_ops"]
        y_dir = extrapolation["year_budget_reached_direct"]
        lines.append(f"- **Tendance annuelle directe de ops** : `{a_dir:+.1f} ops / an` (R² = {extrapolation['r2_direct']:.4f})")
        if y_dir is not None:
            lines.append(f"- **Année projetée d'épuisement (directe)** : **{y_dir:.1f}**")
        else:
            lines.append("- **Année projetée d'épuisement (directe)** : **Aucun épuisement projeté (pente <= 0)**")
    else:
        lines.append("- Pas assez de points pour calculer la régression linéaire (N < 2).")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Lit les journaux moteur (.log / .log.gz) et analyse le coût de Save()."
    )
    parser.add_argument("paths", nargs="*", help="Fichiers journaux ou dossiers contenant des .log/.log.gz")
    parser.add_argument("--campaign", type=str, help="Nom de la campagne sous results/")
    parser.add_argument("--budget", type=int, default=100000, help="Budget MAX_SL_OPS (défaut 100000)")
    parser.add_argument("--json", action="store_true", help="Sortie au format JSON")
    parser.add_argument("--selftest", action="store_true", help="Exécute les tests unitaires internes")

    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    targets = list(args.paths)
    if args.campaign:
        targets.append(args.campaign)

    if not targets:
        parser.error("Spécifiez au moins un fichier, dossier ou --campaign (ou utilisez --selftest).")

    log_files = find_log_files(targets)
    if not log_files:
        print(f"Erreur: Aucun fichier journal trouvé dans {targets}", file=sys.stderr)
        sys.exit(1)

    all_events: List[Dict[str, Any]] = []
    for f in log_files:
        all_events.extend(parse_log_file(f))

    if not all_events:
        print(f"Aucun événement V262_SAVE trouvé dans {len(log_files)} fichier(s).", file=sys.stderr)
        sys.exit(0)

    aggregated = aggregate_by_seed_year(all_events)
    extrapolation = extrapolate_ops_vs_lah(all_events, budget=args.budget)

    if args.json:
        # Clés de aggregated converties en chaînes pour JSON
        json_agg = {f"{k[0]}_{k[1]}": v for k, v in aggregated.items()}
        out = {
            "budget": args.budget,
            "total_events": len(all_events),
            "files_count": len(log_files),
            "by_seed_year": json_agg,
            "extrapolation": extrapolation,
        }
        print(json.dumps(out, indent=2))
    else:
        print(format_report_markdown(aggregated, extrapolation, budget=args.budget))


def run_selftest():
    """Autotest interne sans dépendance externe."""
    print("Running selftest for analyze_v262_save...")
    sample_line = "dbg: [script:0] [0] [I] OPEX 1975-6-30 V262_SAVE ops=1420 budget=100000 lines=12 abandons=3 abandonCounts=5 tasks=8 full=1"
    parsed = parse_v262_save_line(sample_line)
    assert parsed is not None, "Failed to parse sample line"
    assert parsed["year"] == 1975
    assert parsed["month"] == 6
    assert parsed["day"] == 30
    assert parsed["ops"] == 1420
    assert parsed["budget"] == 100000
    assert parsed["lines"] == 12
    assert parsed["abandons"] == 3
    assert parsed["abandonCounts"] == 5
    assert parsed["tasks"] == 8
    assert parsed["full"] == 1
    assert parsed["lah"] == 20
    assert parsed["margin"] == 98580

    # Test régression linéaire simple
    xs = [10.0, 20.0, 30.0, 40.0]
    ys = [100.0, 200.0, 300.0, 400.0]
    alpha, beta, r2 = linear_regression(xs, ys)
    assert abs(alpha - 10.0) < 1e-6
    assert abs(beta - 0.0) < 1e-6
    assert abs(r2 - 1.0) < 1e-6

    # Test extrapolation
    mock_events = [
        {"seed": "42", "year": 1970, "month": 6, "ops": 1000, "budget": 100000, "lines": 5, "abandons": 1, "abandonCounts": 2, "lah": 8, "margin": 99000},
        {"seed": "42", "year": 1971, "month": 6, "ops": 2000, "budget": 100000, "lines": 10, "abandons": 3, "abandonCounts": 5, "lah": 18, "margin": 98000},
        {"seed": "42", "year": 1972, "month": 6, "ops": 3000, "budget": 100000, "lines": 15, "abandons": 5, "abandonCounts": 8, "lah": 28, "margin": 97000},
    ]
    extrap = extrapolate_ops_vs_lah(mock_events, budget=100000)
    assert extrap["alpha"] == 100.0
    assert extrap["beta"] == 200.0
    assert abs(extrap["r2"] - 1.0) < 1e-6
    assert extrap["x_crit"] == (100000 - 200) / 100.0
    assert extrap["year_budget_reached_via_lah"] is not None
    assert abs(extrap["year_budget_reached_via_lah"] - 2069.5) < 1.0

    print("Selftest OK!")


if __name__ == "__main__":
    main()
