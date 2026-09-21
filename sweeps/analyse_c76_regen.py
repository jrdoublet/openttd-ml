#!/usr/bin/env python3
"""Analyseur de régénération du vivier C76 (étape 1 : la régénération sert-elle ?).

Lit le jsonl produit par `diag_c69_bottleneck_probe.py --raw ... --extra-tags C76_REGEN`
(ou directement les lignes de log OpenTTD) et affiche par année :
1. Régénérations complètes et incrémentales, volume et coût (opcodes et jours de jeu) ;
2. Part des régénérations à dépendances inchangées et part où le Top 1 / la liste classée sont identiques ;
3. Distribution des variations de population et de production ;
4. Répartition de la stabilité des candidats par mode (nombre, mêmes clés %, même économie %).
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

REGEN_TAG_RE = re.compile(r"OPEX (\d+)-\d+-\d+ C76_REGEN\s*(.*)")
MODES = ("rail", "road", "air", "water", "fleet")


def parse_fields(fields_str: str) -> Dict[str, Any]:
    """Parse une chaîne de jetons key=val séparés par des espaces."""
    fields: Dict[str, Any] = {}
    for token in fields_str.split():
        if "=" in token:
            k, v = token.split("=", 1)
            fields[k] = v
    return fields


def parse_line(raw: str) -> Optional[Dict[str, Any]]:
    """Parse une ligne brute (JSON ou log brut OpenTTD)."""
    raw = raw.strip()
    if not raw:
        return None
    if raw.startswith("{") and raw.endswith("}"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                tag = data.get("tag")
                phase = data.get("phase")
                if tag == "C76_REGEN" or phase in ("regen", "regen_year"):
                    return data
            return None
        except json.JSONDecodeError:
            return None

    m = REGEN_TAG_RE.search(raw)
    if m:
        log_year, fields_str = m.group(1), m.group(2)
        fields = parse_fields(fields_str)
        fields["_log_year"] = int(log_year)
        fields["tag"] = "C76_REGEN"
        return fields

    if "=" in raw:
        fields = parse_fields(raw)
        if fields.get("phase") in ("regen", "regen_year"):
            return fields

    return None


def parse_stream(lines: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Sépare les lignes en événements 'regen' et agrégats 'regen_year'."""
    regen_events: List[Dict[str, Any]] = []
    year_events: List[Dict[str, Any]] = []
    for line in lines:
        entry = parse_line(line)
        if not entry:
            continue
        phase = entry.get("phase")
        if phase == "regen":
            regen_events.append(entry)
        elif phase == "regen_year":
            year_events.append(entry)
    return regen_events, year_events


def safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def median(vals: List[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def format_stats(vals: List[float]) -> str:
    if not vals:
        return "N/A"
    s = sorted(vals)
    med = median(s)
    return f"{med:+.2f}% [{s[0]:+.2f}%, {s[-1]:+.2f}%]"


def aggregate_regen(events: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """Agrège les métriques des passes de régénération par année."""
    by_year: Dict[int, Dict[str, Any]] = {}

    for e in events:
        year = safe_int(e.get("year", e.get("_log_year", 0)))
        if year <= 0:
            continue
        if year not in by_year:
            by_year[year] = {
                "year": year,
                "count": 0,
                "full": 0,
                "incremental": 0,
                "ops_total": 0,
                "days_since_prev": [],
                "unchanged_deps": 0,
                "top1_unchanged": 0,
                "best_same_keys_pct": [],
                "pop_deltas": [],
                "prod_deltas": [],
                "budget_deltas": [],
                "events_count": 0,
                "modes": {
                    m: {"n": [], "same_keys": [], "same_econ": []}
                    for m in MODES
                },
            }

        rec = by_year[year]
        rec["count"] += 1
        kind = e.get("kind", "full")
        if kind == "full":
            rec["full"] += 1
        else:
            rec["incremental"] += 1

        rec["ops_total"] += safe_int(e.get("ops", 0))
        rec["days_since_prev"].append(safe_int(e.get("days_since_prev", 0)))

        # Dépendances inchangées
        ind_changed = safe_int(e.get("industries_changed", 0))
        lines_delta = safe_int(e.get("lines_delta", 0))
        eng_rail = safe_int(e.get("engines_changed_rail", 0))
        eng_road = safe_int(e.get("engines_changed_road", 0))
        eng_air = safe_int(e.get("engines_changed_air", 0))
        eng_water = safe_int(e.get("engines_changed_water", 0))

        unchanged = (
            ind_changed == 0
            and lines_delta == 0
            and eng_rail == 0
            and eng_road == 0
            and eng_air == 0
            and eng_water == 0
        )
        if unchanged:
            rec["unchanged_deps"] += 1

        if safe_int(e.get("best_same_top1", 0)) == 1:
            rec["top1_unchanged"] += 1

        if "best_same_keys_pct" in e:
            rec["best_same_keys_pct"].append(safe_float(e["best_same_keys_pct"]))

        if "towns_pop_delta_pct" in e:
            rec["pop_deltas"].append(safe_float(e["towns_pop_delta_pct"]))
        if "ind_prod_delta_pct" in e:
            rec["prod_deltas"].append(safe_float(e["ind_prod_delta_pct"]))
        if "cash_budget_delta_pct" in e:
            rec["budget_deltas"].append(safe_float(e["cash_budget_delta_pct"]))

        # Événements reçus
        ev_raw = str(e.get("events_since_prev", "0"))
        ev_match = re.match(r"^(\d+)", ev_raw)
        if ev_match:
            rec["events_count"] += int(ev_match.group(1))

        # Métriques par mode
        for m in MODES:
            k_n = f"cand_{m}_n"
            k_keys = f"cand_{m}_same_keys_pct"
            k_econ = f"cand_{m}_same_econ_pct"
            if k_n in e:
                rec["modes"][m]["n"].append(safe_int(e[k_n]))
            if k_keys in e:
                rec["modes"][m]["same_keys"].append(safe_float(e[k_keys]))
            if k_econ in e:
                rec["modes"][m]["same_econ"].append(safe_float(e[k_econ]))

    return by_year


def aggregate_years(events: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """Agrège les lignes annuelles phase=regen_year."""
    by_year: Dict[int, Dict[str, Any]] = {}
    for e in events:
        year = safe_int(e.get("year", e.get("_log_year", 0)))
        if year <= 0:
            continue
        by_year[year] = {
            "year": year,
            "full": safe_int(e.get("full", 0)),
            "incremental": safe_int(e.get("incremental", 0)),
            "ops_total": safe_int(e.get("ops_total", 0)),
            "days_total": safe_int(e.get("days_total", 0)),
            "unchanged_deps": safe_int(e.get("unchanged_deps", 0)),
            "top1_unchanged": safe_int(e.get("top1_unchanged", 0)),
        }
    return by_year


def format_volume_table(
    agg: Dict[int, Dict[str, Any]],
    agg_yr: Optional[Dict[int, Dict[str, Any]]] = None,
) -> str:
    """Tableau 1 : Volume, coût et dépendances."""
    lines = [
        "=" * 105,
        "  C76 — VOLUME, COÛT ET DÉPENDANCES DES RÉGÉNÉRATIONS DU VIVIER",
        "=" * 105,
        f"{'Année':>5} | {'Full':>4} {'Incr':>4} {'Total':>5} | {'Ops Total':>10} {'Ops/Passe':>10} {'Jours Coût':>10} | {'Sans Chgt Dép':>14} | {'Top 1 Idem':>10} {'Liste Idem':>10}",
        "-" * 105,
    ]

    all_years = sorted(set(agg.keys()) | (set(agg_yr.keys()) if agg_yr else set()))
    for y in all_years:
        r = agg.get(y)
        ry = agg_yr.get(y) if agg_yr else None

        if r:
            full = r["full"]
            incr = r["incremental"]
            total = r["count"]
            ops = r["ops_total"]
            ops_per_pass = ops // total if total > 0 else 0
            unchanged = r["unchanged_deps"]
            unchanged_pct = (unchanged * 100.0) / total if total > 0 else 0.0
            top1 = r["top1_unchanged"]
            top1_pct = (top1 * 100.0) / total if total > 0 else 0.0
            best_keys_avg = (
                sum(r["best_same_keys_pct"]) / len(r["best_same_keys_pct"])
                if r["best_same_keys_pct"]
                else 0.0
            )
            days_cost = ry["days_total"] if ry else 0
        elif ry:
            full = ry["full"]
            incr = ry["incremental"]
            total = full + incr
            ops = ry["ops_total"]
            ops_per_pass = ops // total if total > 0 else 0
            unchanged = ry["unchanged_deps"]
            unchanged_pct = (unchanged * 100.0) / total if total > 0 else 0.0
            top1 = ry["top1_unchanged"]
            top1_pct = (top1 * 100.0) / total if total > 0 else 0.0
            best_keys_avg = 0.0
            days_cost = ry["days_total"]
        else:
            continue

        ops_str = f"{ops / 1_000_000:.2f} Mop"
        ops_pass_str = f"{ops_per_pass / 1_000:.1f} kop"
        days_str = f"{days_cost} j" if days_cost > 0 else "-"
        unchanged_str = f"{unchanged}/{total} ({unchanged_pct:.1f}%)"
        top1_str = f"{top1_pct:.1f}%"
        best_str = f"{best_keys_avg:.1f}%" if r and r["best_same_keys_pct"] else "-"

        lines.append(
            f"{y:>5} | {full:>4} {incr:>4} {total:>5} | {ops_str:>10} {ops_pass_str:>10} {days_str:>10} | {unchanged_str:>14} | {top1_str:>10} {best_str:>10}"
        )

    lines.append("-" * 105)
    return "\n".join(lines)


def format_drift_table(agg: Dict[int, Dict[str, Any]]) -> str:
    """Tableau 2 : Dérive de population, production et budget."""
    lines = [
        "=" * 100,
        "  C76 — DÉRIVE POPULATION, PRODUCTION ET BUDGET (médiane [min, max])",
        "=" * 100,
        f"{'Année':>5} | {'Δ Pop Villes %':>24} | {'Δ Prod Industries %':>24} | {'Δ Budget Trésor %':>24} | {'Événements':>10}",
        "-" * 100,
    ]

    for y in sorted(agg.keys()):
        r = agg[y]
        pop_str = format_stats(r["pop_deltas"])
        prod_str = format_stats(r["prod_deltas"])
        budget_str = format_stats(r["budget_deltas"])
        ev_str = f"{r['events_count']} ev"
        lines.append(
            f"{y:>5} | {pop_str:>24} | {prod_str:>24} | {budget_str:>24} | {ev_str:>10}"
        )

    lines.append("-" * 100)
    return "\n".join(lines)


def format_modes_table(agg: Dict[int, Dict[str, Any]]) -> str:
    """Tableau 3 : Stabilité des candidats par mode."""
    lines = [
        "=" * 95,
        "  C76 — STABILITÉ DES CANDIDATS PAR MODE (médianes annuelles)",
        "=" * 95,
        f"{'Année':>5} | {'Mode':>6} | {'Candidats N':>12} | {'Mêmes Clés %':>15} | {'Même Écon % (±1%)':>18}",
        "-" * 95,
    ]

    for y in sorted(agg.keys()):
        r = agg[y]
        for m in MODES:
            m_data = r["modes"][m]
            if not m_data["n"]:
                continue
            med_n = median(m_data["n"])
            med_keys = median(m_data["same_keys"])
            med_econ = median(m_data["same_econ"])
            lines.append(
                f"{y:>5} | {m:>6} | {med_n:>12.0f} | {med_keys:>14.1f}% | {med_econ:>17.1f}%"
            )
        lines.append("-" * 95)

    return "\n".join(lines)


def run_selftest() -> None:
    """Vérification unitaire interne de parsing et d'agrégation."""
    sample_lines = [
        # 1971 pass 1 (full)
        json.dumps({
            "tag": "C76_REGEN",
            "_log_year": 1971,
            "phase": "regen",
            "kind": "full",
            "year": "1971",
            "days_since_prev": "0",
            "ops": "2500000",
            "towns_n": "50",
            "towns_pop_delta_pct": "0.00",
            "industries_n": "120",
            "industries_changed": "0",
            "ind_prod_delta_pct": "0.00",
            "engines_changed_rail": "0",
            "engines_changed_road": "0",
            "engines_changed_air": "0",
            "engines_changed_water": "0",
            "lines_n": "0",
            "lines_delta": "0",
            "cash_budget_delta_pct": "0.00",
            "events_since_prev": "0",
            "cand_rail_n": "40",
            "cand_rail_same_keys_pct": "100.00",
            "cand_rail_same_econ_pct": "100.00",
            "cand_road_n": "20",
            "cand_road_same_keys_pct": "100.00",
            "cand_road_same_econ_pct": "100.00",
            "cand_air_n": "15",
            "cand_air_same_keys_pct": "100.00",
            "cand_air_same_econ_pct": "100.00",
            "cand_water_n": "0",
            "cand_water_same_keys_pct": "100.00",
            "cand_water_same_econ_pct": "100.00",
            "cand_fleet_n": "0",
            "cand_fleet_same_keys_pct": "100.00",
            "cand_fleet_same_econ_pct": "100.00",
            "best_same_top1": "1",
            "best_same_keys_pct": "100.00",
        }),
        # 1971 pass 2 (incremental)
        json.dumps({
            "tag": "C76_REGEN",
            "_log_year": 1971,
            "phase": "regen",
            "kind": "incremental",
            "year": "1971",
            "days_since_prev": "45",
            "ops": "450",
            "towns_n": "50",
            "towns_pop_delta_pct": "+0.50",
            "industries_n": "120",
            "industries_changed": "0",
            "ind_prod_delta_pct": "-0.10",
            "engines_changed_rail": "0",
            "engines_changed_road": "0",
            "engines_changed_air": "0",
            "engines_changed_water": "0",
            "lines_n": "1",
            "lines_delta": "1",
            "cash_budget_delta_pct": "+5.20",
            "events_since_prev": "1(ind_open:1)",
            "cand_rail_n": "39",
            "cand_rail_same_keys_pct": "97.50",
            "cand_rail_same_econ_pct": "95.00",
            "cand_road_n": "20",
            "cand_road_same_keys_pct": "100.00",
            "cand_road_same_econ_pct": "100.00",
            "cand_air_n": "15",
            "cand_air_same_keys_pct": "100.00",
            "cand_air_same_econ_pct": "93.30",
            "cand_water_n": "0",
            "cand_water_same_keys_pct": "100.00",
            "cand_water_same_econ_pct": "100.00",
            "cand_fleet_n": "0",
            "cand_fleet_same_keys_pct": "100.00",
            "cand_fleet_same_econ_pct": "100.00",
            "best_same_top1": "1",
            "best_same_keys_pct": "95.00",
        }),
        # 1971 annual aggregate
        json.dumps({
            "tag": "C76_REGEN",
            "_log_year": 1972,
            "phase": "regen_year",
            "year": "1971",
            "full": "1",
            "incremental": "1",
            "ops_total": "2500450",
            "days_total": "2",
            "unchanged_deps": "1",
            "top1_unchanged": "2",
        }),
        # Raw log format for 1972
        "OPEX 1972-04-01 C76_REGEN phase=regen kind=full year=1972 days_since_prev=48 ops=2600000 towns_n=50 towns_pop_delta_pct=+1.10 industries_n=120 industries_changed=0 ind_prod_delta_pct=+0.20 engines_changed_rail=0 engines_changed_road=0 engines_changed_air=0 engines_changed_water=0 lines_n=2 lines_delta=0 cash_budget_delta_pct=+12.00 events_since_prev=0 cand_rail_n=38 cand_rail_same_keys_pct=95.00 cand_rail_same_econ_pct=92.00 cand_road_n=20 cand_road_same_keys_pct=100.00 cand_road_same_econ_pct=100.00 cand_air_n=15 cand_air_same_keys_pct=100.00 cand_air_same_econ_pct=95.00 cand_water_n=0 cand_water_same_keys_pct=100.00 cand_water_same_econ_pct=100.00 cand_fleet_n=1 cand_fleet_same_keys_pct=100.00 cand_fleet_same_econ_pct=100.00 best_same_top1=1 best_same_keys_pct=92.00",
        "OPEX 1973-01-01 C76_REGEN phase=regen_year year=1972 full=1 incremental=0 ops_total=2600000 days_total=2 unchanged_deps=1 top1_unchanged=1",
    ]

    regens, years = parse_stream(sample_lines)
    assert len(regens) == 3, f"Attendu 3 regens, obtenu {len(regens)}"
    assert len(years) == 2, f"Attendu 2 years, obtenu {len(years)}"

    agg_r = aggregate_regen(regens)
    agg_y = aggregate_years(years)

    assert 1971 in agg_r
    assert agg_r[1971]["count"] == 2
    assert agg_r[1971]["full"] == 1
    assert agg_r[1971]["incremental"] == 1
    assert agg_r[1971]["unchanged_deps"] == 1
    assert agg_r[1971]["top1_unchanged"] == 2

    assert 1972 in agg_r
    assert agg_r[1972]["count"] == 1
    assert agg_r[1972]["full"] == 1
    assert agg_r[1972]["unchanged_deps"] == 1

    t1 = format_volume_table(agg_r, agg_y)
    assert "VOLUME, COÛT ET DÉPENDANCES" in t1
    assert "1971" in t1
    assert "1972" in t1

    t2 = format_drift_table(agg_r)
    assert "DÉRIVE POPULATION" in t2
    assert "+0.50%" in t2

    t3 = format_modes_table(agg_r)
    assert "STABILITÉ DES CANDIDATS PAR MODE" in t3
    assert "rail" in t3
    assert "road" in t3

    print("selftest passed: C76 regen analyser verified")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="Fichiers jsonl bruts (ou stdin si vide)")
    parser.add_argument("--raw", type=Path, default=None, help="Fichier jsonl issu de diag_c69_bottleneck_probe.py --raw")
    parser.add_argument("--selftest", action="store_true", help="Lance la suite d'auto-tests internes")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    input_paths: List[Path] = []
    if args.raw:
        input_paths.append(args.raw)
    for f in args.files:
        if str(f) != "-":
            input_paths.append(f)

    lines: List[str] = []
    if not input_paths or any(str(f) == "-" for f in args.files):
        lines = sys.stdin.readlines()
    else:
        for p in input_paths:
            if p.is_file():
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    lines.extend(fh.readlines())
            else:
                sys.stderr.write(f"Avertissement: fichier introuvable: {p}\n")

    if not lines:
        sys.stderr.write("Erreur: aucune ligne d'entrée trouvée.\n")
        sys.exit(1)

    regens, years = parse_stream(lines)
    if not regens and not years:
        sys.stderr.write("Aucun événement C76_REGEN trouvé dans l'entrée.\n")
        sys.exit(1)

    agg_r = aggregate_regen(regens)
    agg_y = aggregate_years(years)

    print(format_volume_table(agg_r, agg_y))
    if agg_r:
        print()
        print(format_drift_table(agg_r))
        print()
        print(format_modes_table(agg_r))


if __name__ == "__main__":
    main()
