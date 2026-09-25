#!/usr/bin/env python3
"""Analyse de la rentabilité par ligne et par mode (rail, air, route, eau).

Lit un jsonl brut issu de `sweeps/diag_c69_bottleneck_probe.py --grep "C56_TASK"`
ou un flux texte brut d'événements C56_TASK_TRACE.

Pour chaque graine et au global (TOTAL) :
- Regroupe les lignes par mode de transport (rail, road, air, water).
- Déduplique les rapports par (graine, lineId, année_profit).
- Exclut l'année de mise en service (incomplète) du calcul de profit annuel stabilisé.
- Calcule pour chaque mode : nombre de lignes, profit annuel par ligne (moyenne, médiane,
  part de lignes à profit négatif), capital moyen/médian par ligne, ROI annuel moyen/médian/macro,
  âge des lignes.
- Fournit un détail complet des lignes ferroviaires (distance, trains, profit/an, capital,
  année de construction, ROI annuel).
- Préserve None pour les données absentes (ne convertit jamais None en zéro).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from sweeps.analyse_v86_cannibalisation import parse_c56_log_line, parse_kv_fields, to_float, to_int
except ImportError:
    try:
        from analyse_v86_cannibalisation import parse_c56_log_line, parse_kv_fields, to_float, to_int
    except ImportError:
        TASK_LOG_RE = re.compile(r"(?:OPEX\s+(\d+)-(\d+)-(\d+)\s+)?C56_TASK\s+(\w+)\s+(.*)")

        def parse_kv_fields(rest_text: str) -> Dict[str, str]:
            fields = {}
            for token in rest_text.split():
                if "=" in token:
                    k, v = token.split("=", 1)
                    fields[k] = v
            return fields

        def parse_c56_log_line(text: str) -> Optional[Dict[str, Any]]:
            m = TASK_LOG_RE.search(text)
            if not m:
                return None
            y_s, m_s, d_s, kind, rest = m.groups()
            log_year = int(y_s) if y_s is not None else None
            log_date = f"{y_s}-{m_s}-{d_s}" if y_s is not None else None
            fields = parse_kv_fields(rest)
            return {
                "kind": kind,
                "log_date": log_date,
                "log_year": log_year,
                "fields": fields,
            }

        def to_int(val: Any, default: Optional[int] = None) -> Optional[int]:
            try:
                return int(val)
            except (TypeError, ValueError):
                return default

        def to_float(val: Any, default: Optional[float] = None) -> Optional[float]:
            try:
                return float(val)
            except (TypeError, ValueError):
                return default


def median(values: List[float]) -> Optional[float]:
    """Calcule la médiane d'une liste de nombres, ou None si vide."""
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return float(s[mid])
    return float((s[mid - 1] + s[mid]) / 2.0)


def mean(values: List[float]) -> Optional[float]:
    """Calcule la moyenne d'une liste de nombres, ou None si vide."""
    if not values:
        return None
    return float(sum(values) / len(values))


def parse_raw_records(lines_or_stream: Iterable[str]) -> Tuple[Dict[Any, Dict[str, Any]], int]:
    """Charge les traces de construction et de profit groupées par seed.

    Retourne un dict `seeds_raw[seed]` et le nombre de doublons exacts éliminés.
    """
    seeds_raw: Dict[Any, Dict[str, Any]] = defaultdict(lambda: {
        "built_lines": {},     # line_id -> metadata de construction
        "profit_obs": [],      # liste brute des observations LINE_PROFIT
    })

    duplicates_count = 0
    seen_profit_keys = set()

    for line in lines_or_stream:
        line = line.strip()
        if not line:
            continue
        seed: Any = None
        raw_text = line
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                seed = data.get("seed")
                raw_text = data.get("grep", data.get("raw", data.get("log", data.get("text", ""))))
            except json.JSONDecodeError:
                pass

        if seed is None:
            seed = "default"

        parsed = parse_c56_log_line(raw_text)
        if not parsed:
            continue

        kind = parsed["kind"]
        fields = parsed["fields"]
        log_year = parsed["log_year"]
        log_date = parsed["log_date"]

        if kind == "AIR_BUILT":
            line_id = to_int(fields.get("line"))
            if line_id is not None:
                cost = to_float(fields.get("cost"))
                seeds_raw[seed]["built_lines"][line_id] = {
                    "mode": "air",
                    "capital": cost,
                    "build_year": log_year,
                    "build_date": log_date,
                    "arm": fields.get("arm", fields.get("name")),
                    "stA": to_int(fields.get("stA")),
                    "stB": to_int(fields.get("stB")),
                }

        elif kind == "RAIL_COMMISSION":
            line_id = to_int(fields.get("line"))
            if line_id is not None:
                cost = to_float(fields.get("cost", fields.get("capital")))
                dist = to_float(fields.get("dist"))
                trains = to_int(fields.get("trains"))
                existing = seeds_raw[seed]["built_lines"].get(line_id, {})
                seeds_raw[seed]["built_lines"][line_id] = {
                    "mode": "rail",
                    "capital": cost if cost is not None else existing.get("capital"),
                    "dist": dist if dist is not None else existing.get("dist"),
                    "trains": trains if trains is not None else existing.get("trains"),
                    "build_year": log_year if log_year is not None else existing.get("build_year"),
                    "build_date": log_date,
                }

        elif kind in ("ROAD_BUILT", "WATER_BUILT"):
            line_id = to_int(fields.get("line"))
            if line_id is not None:
                mode = "road" if kind == "ROAD_BUILT" else "water"
                cost = to_float(fields.get("cost", fields.get("capital")))
                dist = to_float(fields.get("dist"))
                vehs = to_int(fields.get("veh", fields.get("vehicles")))
                seeds_raw[seed]["built_lines"][line_id] = {
                    "mode": mode,
                    "capital": cost,
                    "dist": dist,
                    "trains": vehs,
                    "build_year": log_year,
                    "build_date": log_date,
                }

        elif kind == "LINE_PROFIT":
            line_id = to_int(fields.get("line", fields.get("name")))
            if line_id is None:
                continue

            # Le champ year est l'annee du rapport (1er jan Y) : le profit porte sur l'annee N-1
            report_year = to_int(fields.get("year"))
            profit_year = (report_year - 1) if report_year is not None else None

            # Cle de deduplication (seed, line_id, profit_year)
            dedup_key = (seed, line_id, profit_year)
            if dedup_key in seen_profit_keys:
                duplicates_count += 1
                continue
            seen_profit_keys.add(dedup_key)

            profit = to_float(fields.get("profit"))
            veh = to_int(fields.get("veh"))
            mode = fields.get("mode")
            capital = to_float(fields.get("capital"))
            if capital is not None and capital < 0:
                capital = None
            dist = to_float(fields.get("dist"))
            if dist is not None and dist < 0:
                dist = None
            built = to_int(fields.get("built"))
            if built is not None and built <= 0:
                built = None

            seeds_raw[seed]["profit_obs"].append({
                "line_id": line_id,
                "report_year": report_year,
                "profit_year": profit_year,
                "profit": profit,
                "veh": veh,
                "mode": mode,
                "capital": capital,
                "dist": dist,
                "built": built,
                "stA": to_int(fields.get("stA")),
                "stB": to_int(fields.get("stB")),
            })

    return seeds_raw, duplicates_count


def process_lines(
    seeds_raw: Dict[Any, Dict[str, Any]],
    include_incomplete_year: bool = False,
) -> Dict[str, Any]:
    """Traite les observations pour extraire les metriques par ligne, par graine et par mode."""
    results_by_seed: Dict[Any, Dict[str, Any]] = {}
    all_lines: List[Dict[str, Any]] = []

    for seed, raw in sorted(seeds_raw.items(), key=lambda x: str(x[0])):
        built_dict = raw["built_lines"]
        profit_obs = raw["profit_obs"]

        # Regrouper les observations par line_id
        obs_by_line: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for obs in profit_obs:
            obs_by_line[obs["line_id"]].append(obs)

        # Ensemble de toutes les lignes connues pour cette graine
        all_line_ids = sorted(set(built_dict.keys()) | set(obs_by_line.keys()))
        seed_lines: List[Dict[str, Any]] = []

        for line_id in all_line_ids:
            obs_list = sorted(
                obs_by_line.get(line_id, []),
                key=lambda o: (o["profit_year"] if o["profit_year"] is not None else -999),
            )
            built_meta = built_dict.get(line_id, {})

            # 1. Mode de la ligne
            mode: Optional[str] = None
            for o in obs_list:
                if o.get("mode"):
                    mode = o["mode"]
                    break
            if mode is None:
                mode = built_meta.get("mode")
            if mode is None:
                # Si non specifie et sans trace built, on ne l'invente pas
                mode = "unknown"

            # 2. Capital investi
            capital: Optional[float] = None
            for o in obs_list:
                if o.get("capital") is not None:
                    capital = o["capital"]
                    break
            if capital is None and built_meta.get("capital") is not None:
                capital = built_meta["capital"]

            # 3. Distance
            dist: Optional[float] = None
            for o in obs_list:
                if o.get("dist") is not None:
                    dist = o["dist"]
                    break
            if dist is None and built_meta.get("dist") is not None:
                dist = built_meta["dist"]

            # 4. Annee de construction
            build_year: Optional[int] = None
            for o in obs_list:
                if o.get("built") is not None:
                    build_year = o["built"]
                    break
            if build_year is None and built_meta.get("build_year") is not None:
                build_year = built_meta["build_year"]

            # 5. Nombre de trains / vehicules
            trains: Optional[int] = None
            for o in reversed(obs_list):
                if o.get("veh") is not None:
                    trains = o["veh"]
                    break
            if trains is None and built_meta.get("trains") is not None:
                trains = built_meta["trains"]

            # 6. Profits et annees de service
            full_service_profits: List[float] = []
            all_profits: List[float] = []
            observed_years: List[int] = []
            has_incomplete_year = False

            for o in obs_list:
                py = o["profit_year"]
                p = o["profit"]
                if py is not None:
                    observed_years.append(py)
                if p is not None:
                    all_profits.append(p)
                    if build_year is not None and py is not None:
                        if py > build_year:
                            full_service_profits.append(p)
                        else:
                            has_incomplete_year = True
                    else:
                        full_service_profits.append(p)

            # Selection des profits selon l'option include_incomplete_year
            if include_incomplete_year:
                effective_profits = all_profits
            else:
                effective_profits = full_service_profits

            profit_per_year = mean(effective_profits)
            full_years_count = len(effective_profits)

            # ROI annuel
            roi_annual: Optional[float] = None
            if capital is not None and capital > 0 and profit_per_year is not None:
                roi_annual = profit_per_year / capital

            # Age de la ligne
            age: Optional[int] = None
            if build_year is not None and observed_years:
                age = max(observed_years) - build_year + 1

            status = "NO_DATA"
            if effective_profits:
                if profit_per_year is not None and profit_per_year < 0:
                    status = "LOSS"
                else:
                    status = "PROFITABLE"
            elif all_profits and not full_service_profits:
                status = "INCOMPLETE_ONLY"

            line_entry = {
                "seed": seed,
                "line_id": line_id,
                "mode": mode,
                "distance": dist,
                "trains": trains,
                "build_year": build_year,
                "capital": capital,
                "profit_per_year": profit_per_year,
                "roi_annual": roi_annual,
                "full_years_count": full_years_count,
                "observed_years_count": len(all_profits),
                "has_incomplete_year": has_incomplete_year,
                "age": age,
                "status": status,
            }
            seed_lines.append(line_entry)
            all_lines.append(line_entry)

        results_by_seed[seed] = {
            "lines": seed_lines,
            "summary_by_mode": compute_mode_summary(seed_lines),
        }

    total_summary = compute_mode_summary(all_lines)

    # Filtrer et trier les lignes ferroviaires
    rail_lines = [l for l in all_lines if l["mode"] == "rail"]
    rail_lines.sort(key=lambda x: (str(x["seed"]), x["line_id"]))

    return {
        "by_seed": results_by_seed,
        "total_summary": total_summary,
        "rail_lines": rail_lines,
        "total_lines_count": len(all_lines),
    }


def compute_mode_summary(lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcule le resume statistique agrege par mode pour un ensemble de lignes."""
    modes = ["rail", "road", "air", "water"]
    summary: Dict[str, Any] = {}

    # Initialiser les modes reconnus
    for m in modes:
        summary[m] = _empty_mode_stat()

    # Si d'autres modes (ex unknown) existent
    for l in lines:
        m = l["mode"]
        if m not in summary:
            summary[m] = _empty_mode_stat()

    for l in lines:
        m = l["mode"]
        entry = summary[m]
        entry["lines_count"] += 1

        ppy = l["profit_per_year"]
        if ppy is not None:
            entry["_profits"].append(ppy)
            if ppy < 0:
                entry["negative_lines_count"] += 1

        cap = l["capital"]
        if cap is not None and cap >= 0:
            entry["_capitals"].append(cap)

        roi = l["roi_annual"]
        if roi is not None:
            entry["_rois"].append(roi)

        age = l["age"]
        if age is not None and age >= 0:
            entry["_ages"].append(age)

    # Synthese statistique pour chaque mode
    for m, entry in summary.items():
        n_lines = entry["lines_count"]
        profits = entry.pop("_profits")
        capitals = entry.pop("_capitals")
        rois = entry.pop("_rois")
        ages = entry.pop("_ages")

        entry["evaluated_lines_count"] = len(profits)
        entry["profit_annual_mean"] = mean(profits)
        entry["profit_annual_median"] = median(profits)

        if len(profits) > 0:
            entry["negative_profit_share"] = float(entry["negative_lines_count"] / len(profits))
        else:
            entry["negative_profit_share"] = None

        entry["capital_mean"] = mean(capitals)
        entry["capital_median"] = median(capitals)
        entry["capital_total"] = float(sum(capitals)) if capitals else None

        entry["roi_annual_mean"] = mean(rois)
        entry["roi_annual_median"] = median(rois)

        # ROI macro = somme des profits / somme des capitaux des lignes exploitables
        if capitals and sum(capitals) > 0 and profits:
            # Pour un ratio macro coherent, sommer sur les lignes ayant a la fois profit et capital
            valid_pairs = [(l["profit_per_year"], l["capital"]) for l in lines
                           if l["mode"] == m and l["profit_per_year"] is not None and l["capital"] is not None and l["capital"] > 0]
            if valid_pairs:
                sum_p = sum(p for p, _ in valid_pairs)
                sum_c = sum(c for _, c in valid_pairs)
                entry["roi_macro"] = float(sum_p / sum_c) if sum_c > 0 else None
            else:
                entry["roi_macro"] = None
        else:
            entry["roi_macro"] = None

        entry["age_mean"] = mean(ages)
        entry["age_median"] = median(ages)

    return summary


def _empty_mode_stat() -> Dict[str, Any]:
    return {
        "lines_count": 0,
        "evaluated_lines_count": 0,
        "negative_lines_count": 0,
        "negative_profit_share": None,
        "profit_annual_mean": None,
        "profit_annual_median": None,
        "capital_mean": None,
        "capital_median": None,
        "capital_total": None,
        "roi_annual_mean": None,
        "roi_annual_median": None,
        "roi_macro": None,
        "age_mean": None,
        "age_median": None,
        "_profits": [],
        "_capitals": [],
        "_rois": [],
        "_ages": [],
    }


def format_pounds(val: Optional[float]) -> str:
    """Formate une somme en livres sterling ou None."""
    if val is None:
        return "None"
    sign = "-" if val < 0 else ""
    return f"{sign}{abs(val):,.0f} £".replace(",", " ")


def format_pct(val: Optional[float]) -> str:
    """Formate un ratio en pourcentage ou None."""
    if val is None:
        return "None"
    return f"{val * 100:.1f} %"


def format_num(val: Optional[float], decimals: int = 1) -> str:
    """Formate un nombre flottant ou None."""
    if val is None:
        return "None"
    return f"{val:.{decimals}f}"


def print_report(results: Dict[str, Any], duplicates_count: int, include_incomplete_year: bool) -> None:
    """Affiche le rapport complet formate en texte."""
    by_seed = results["by_seed"]
    total_summary = results["total_summary"]
    rail_lines = results["rail_lines"]

    print("=" * 110)
    print("RENTABILITÉ PAR LIGNE ET PAR MODE (OpenTTD / OpexAI)")
    print(f"Graines analysées : {len(by_seed)} | Total lignes : {results['total_lines_count']} | Doublons dédupliqués : {duplicates_count}")
    if include_incomplete_year:
        print("Note : L'année de mise en service (incomplète) EST incluse dans les moyennes annuelles.")
    else:
        print("Note : L'année de mise en service (incomplète) est EXCLUE du calcul de profit annuel stabilisé.")
    print("=" * 110)

    # 1. Tableau global par mode (TOTAL)
    print("\n--- SYNTHÈSE GLOBALE PAR MODE (TOUTES GRAINES) ---")
    _print_summary_table(total_summary)

    # 2. Tableaux par graine si > 1 graine
    if len(by_seed) > 1:
        for seed, sdata in by_seed.items():
            print(f"\n--- GRAINE {seed} ---")
            _print_summary_table(sdata["summary_by_mode"])

    # 3. Détail des lignes ferroviaires (RAIL)
    print("\n--- DÉTAIL DES LIGNES FERROVIAIRES (RAIL) ---")
    if not rail_lines:
        print("Aucune ligne ferroviaire identifiée dans les journaux.")
    else:
        header = f"{'Graine':<8} {'Ligne':<6} {'Dist':<6} {'Trains':<7} {'Année':<7} {'Années':<7} {'Capital':<13} {'Profit/an':<13} {'ROI/an':<9} {'Statut'}"
        print(header)
        print("-" * len(header))
        for rl in rail_lines:
            s_seed = str(rl["seed"])
            s_line = str(rl["line_id"])
            s_dist = format_num(rl["distance"], 0)
            s_trains = str(rl["trains"]) if rl["trains"] is not None else "None"
            s_built = str(rl["build_year"]) if rl["build_year"] is not None else "None"
            s_years = f"{rl['full_years_count']} an(s)"
            s_cap = format_pounds(rl["capital"])
            s_prof = format_pounds(rl["profit_per_year"])
            s_roi = format_pct(rl["roi_annual"])
            status = rl["status"]
            print(f"{s_seed:<8} {s_line:<6} {s_dist:<6} {s_trains:<7} {s_built:<7} {s_years:<7} {s_cap:<13} {s_prof:<13} {s_roi:<9} {status}")
    print()


def _print_summary_table(summary: Dict[str, Any]) -> None:
    header = f"{'Mode':<8} {'Lignes':<7} {'Éval.':<7} {'Profit/an (méd)':<16} {'Profit/an (moy)':<16} {'Pertes (%)':<11} {'Capital (moy)':<14} {'ROI (méd)':<10} {'ROI macro':<10} {'Âge (moy)'}"
    print(header)
    print("-" * len(header))
    for m in ["rail", "air", "road", "water"]:
        if m not in summary:
            continue
        entry = summary[m]
        s_mode = m
        s_cnt = str(entry["lines_count"])
        s_eval = str(entry["evaluated_lines_count"])
        s_prof_med = format_pounds(entry["profit_annual_median"])
        s_prof_mean = format_pounds(entry["profit_annual_mean"])
        s_loss = format_pct(entry["negative_profit_share"])
        s_cap = format_pounds(entry["capital_mean"])
        s_roi_med = format_pct(entry["roi_annual_median"])
        s_roi_mac = format_pct(entry["roi_macro"])
        s_age = f"{format_num(entry['age_mean'])} ans" if entry["age_mean"] is not None else "None"
        print(f"{s_mode:<8} {s_cnt:<7} {s_eval:<7} {s_prof_med:<16} {s_prof_mean:<16} {s_loss:<11} {s_cap:<14} {s_roi_med:<10} {s_roi_mac:<10} {s_age}")


def run_selftest() -> bool:
    """Vérification autonome des calculs et du contrat de rentabilité."""
    # Fixture synthétique inline
    synthetic_logs = [
        # Graine 42 - Ligne AIR 1 : construite en 1971, profit 1971 rapporté en 1972, profit 1972 rapporté en 1973
        json.dumps({"seed": 42, "grep": "OPEX 1971-06-15 C56_TASK AIR_BUILT name=hubhub line=1 cost=80000 profit=50000 stA=10 stB=20"}),
        json.dumps({"seed": 42, "grep": "OPEX 1972-01-01 C56_TASK LINE_PROFIT name=1 cycle=- tick=10 opsclk=10 year=1972 profit=25000 veh=2 stA=10 stB=20"}),  # annee 1971 incomplete
        json.dumps({"seed": 42, "grep": "OPEX 1973-01-01 C56_TASK LINE_PROFIT name=1 cycle=- tick=20 opsclk=20 year=1973 profit=60000 veh=2 stA=10 stB=20"}),  # annee 1972 pleine
        json.dumps({"seed": 42, "grep": "OPEX 1974-01-01 C56_TASK LINE_PROFIT name=1 cycle=- tick=30 opsclk=30 year=1974 profit=64000 veh=2 stA=10 stB=20"}),  # annee 1973 pleine

        # Doublon exact de trace pour verifier la deduplication
        json.dumps({"seed": 42, "grep": "OPEX 1974-01-01 C56_TASK LINE_PROFIT name=1 cycle=- tick=30 opsclk=30 year=1974 profit=64000 veh=2 stA=10 stB=20"}),

        # Graine 42 - Ligne RAIL 2 : construite en 1972 (via nouveau format enrichi C56)
        json.dumps({"seed": 42, "grep": "OPEX 1972-05-10 C56_TASK RAIL_COMMISSION primary line=2 src=100 dst=200 cost=150000 dist=90 trains=2 iters=850 delay_days=100 search_to_service_days=20"}),
        json.dumps({"seed": 42, "grep": "OPEX 1973-01-01 C56_TASK LINE_PROFIT name=2 cycle=- tick=25 opsclk=25 year=1973 profit=5000 veh=2 mode=rail capital=150000 dist=90 built=1972 stA=100 stB=200"}), # annee 1972 incomplete
        json.dumps({"seed": 42, "grep": "OPEX 1974-01-01 C56_TASK LINE_PROFIT name=2 cycle=- tick=35 opsclk=35 year=1974 profit=15000 veh=2 mode=rail capital=150000 dist=90 built=1972 stA=100 stB=200"}), # annee 1973 pleine

        # Graine 42 - Ligne RAIL 3 : ligne ferroviaire deficitaire !
        json.dumps({"seed": 42, "grep": "OPEX 1973-03-01 C56_TASK RAIL_COMMISSION primary line=3 src=110 dst=210 cost=200000 dist=120 trains=1 iters=1200 delay_days=150 search_to_service_days=30"}),
        json.dumps({"seed": 42, "grep": "OPEX 1974-01-01 C56_TASK LINE_PROFIT name=3 cycle=- tick=36 opsclk=36 year=1974 profit=-5000 veh=1 mode=rail capital=200000 dist=120 built=1973 stA=110 stB=210"}), # annee 1973 incomplete
        json.dumps({"seed": 42, "grep": "OPEX 1975-01-01 C56_TASK LINE_PROFIT name=3 cycle=- tick=46 opsclk=46 year=1975 profit=-8000 veh=1 mode=rail capital=200000 dist=120 built=1973 stA=110 stB=210"}), # annee 1974 pleine (perte)

        # Graine 42 - Ligne ROAD 4 : ligne sans capital trace (pour tester que capital reste None et non 0)
        json.dumps({"seed": 42, "grep": "OPEX 1974-01-01 C56_TASK LINE_PROFIT name=4 cycle=- tick=37 opsclk=37 year=1974 profit=4000 veh=3 mode=road dist=15 built=1972 stA=50 stB=60"}),
    ]

    seeds_raw, dup_count = parse_raw_records(synthetic_logs)
    assert dup_count == 1, f"Attendu 1 doublon, obtenu {dup_count}"

    res = process_lines(seeds_raw, include_incomplete_year=False)
    summary = res["total_summary"]

    # Verifications Air
    air_s = summary["air"]
    assert air_s["lines_count"] == 1
    assert air_s["evaluated_lines_count"] == 1
    # Profit annees pleines (1972: 60000, 1973: 64000) -> moyenne 62000, annee 1971 exclue
    assert air_s["profit_annual_mean"] == 62000.0, f"Attendu 62000, obtenu {air_s['profit_annual_mean']}"
    assert air_s["capital_mean"] == 80000.0
    # ROI: 62000 / 80000 = 0.775
    assert abs(air_s["roi_annual_mean"] - 0.775) < 1e-4

    # Verifications Rail
    rail_s = summary["rail"]
    assert rail_s["lines_count"] == 2
    assert rail_s["evaluated_lines_count"] == 2
    # Ligne 2 : pleine 1973 = 15 000 £. Ligne 3 : pleine 1974 = -8 000 £.
    # Moyenne = (15000 - 8000) / 2 = 3500 £
    assert rail_s["profit_annual_mean"] == 3500.0, f"Attendu 3500, obtenu {rail_s['profit_annual_mean']}"
    # Mediane = 3500 £
    assert rail_s["profit_annual_median"] == 3500.0
    # Pertes = 1 ligne sur 2 = 50%
    assert rail_s["negative_profit_share"] == 0.5
    assert rail_s["capital_mean"] == 175000.0  # (150k + 200k) / 2

    # Verifications Road (capital None preserve)
    road_s = summary["road"]
    assert road_s["lines_count"] == 1
    assert road_s["capital_mean"] is None, "Le capital inconnu doit rester None, pas zero"
    assert road_s["roi_annual_mean"] is None, "Le ROI d'une ligne sans capital doit etre None"

    # Verifications liste des lignes rail
    rls = res["rail_lines"]
    assert len(rls) == 2
    rl2 = next(l for l in rls if l["line_id"] == 2)
    assert rl2["profit_per_year"] == 15000.0
    assert rl2["distance"] == 90.0
    assert rl2["trains"] == 2
    assert rl2["status"] == "PROFITABLE"

    rl3 = next(l for l in rls if l["line_id"] == 3)
    assert rl3["profit_per_year"] == -8000.0
    assert rl3["distance"] == 120.0
    assert rl3["trains"] == 1
    assert rl3["status"] == "LOSS"

    print("Selftest analyse_line_profit_by_mode : PASS (toutes les assertions sont validées).")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyse de rentabilité par ligne et par mode (OpexAI / OpenTTD)")
    parser.add_argument("input_file", nargs="?", help="Fichier jsonl brut produit par diag_c69_bottleneck_probe.py --grep 'C56_TASK' (ou stdin si omis)")
    parser.add_argument("--json", action="store_true", help="Sortie au format JSON structuré")
    parser.add_argument("--include-incomplete-year", action="store_true", help="Inclure l'année de mise en service dans la moyenne annuelle")
    parser.add_argument("--selftest", action="store_true", help="Exécuter les tests internes de validation")
    args = parser.parse_args()

    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # Lecture des donnees (fichier ou stdin)
    if args.input_file and args.input_file != "-":
        p = Path(args.input_file)
        if not p.is_file():
            print(f"Erreur : fichier introuvable {p}", file=sys.stderr)
            sys.exit(1)
        with open(p, "r", encoding="utf-8") as fh:
            seeds_raw, dup_count = parse_raw_records(fh)
    else:
        if sys.stdin.isatty():
            parser.print_help()
            sys.exit(1)
        seeds_raw, dup_count = parse_raw_records(sys.stdin)

    results = process_lines(seeds_raw, include_incomplete_year=args.include_incomplete_year)

    if args.json:
        # Enlever les structures circulaires ou non JSON-friendly si necessaire
        print(json.dumps(results, indent=2))
    else:
        print_report(results, dup_count, args.include_incomplete_year)


if __name__ == "__main__":
    main()
