#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sweeps/analyze_v268_early.py — Analyseur hors ligne de l'estimation precoce V268.

Lit un journal moteur OpenTTD ou un fichier JSONL issu d'un banc, extrait les
enregistrements V268_EST, et calcule l'erreur de l'estimation a 3 et 6 mois contre
le realise a 12 puis 24 mois :
  erreur = P_annuel(palier_precoce) - P_annuel(palier_realise)
  - Biais   = moyenne(erreur)
  - MAE     = moyenne(|erreur|)
  - Mediane = mediane(erreur)
  - n       = nombre de vehicules observes aux deux paliers

Ventilation separee :
  - Par mode : AIR, RAIL, ROAD
  - Par genre : pax, fret
  - Global et croise mode x genre
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


def parse_v268_line(line_str: str) -> Optional[Dict[str, Any]]:
    """Extrait un enregistrement V268_EST d'une ligne de log texte ou JSON."""
    line_str = line_str.strip()
    if not line_str:
        return None

    text = line_str
    if line_str.startswith("{") and line_str.endswith("}"):
        try:
            obj = json.loads(line_str)
            if isinstance(obj, dict):
                # Si l'objet JSON contient deja les cles
                if "palier" in obj and "line" in obj and "p_annual" in obj:
                    return normalize_record(obj)
                for key in ("message", "log", "text", "line"):
                    if key in obj and isinstance(obj[key], str) and "V268_EST" in obj[key]:
                        text = obj[key]
                        break
        except Exception:
            pass

    if "V268_EST" not in text:
        return None

    idx = text.find("V268_EST")
    payload = text[idx + len("V268_EST"):].strip()
    tokens = payload.split()
    fields: Dict[str, Any] = {}
    for tok in tokens:
        if "=" in tok:
            k, v = tok.split("=", 1)
            fields[k] = v

    required = ("palier", "line", "mode", "kind", "veh", "p_annual")
    if not all(k in fields for k in required):
        return None

    return normalize_record(fields)


def normalize_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise les types et valeurs d'un enregistrement."""
    kind = str(raw.get("kind", "unknown")).lower()
    if kind in ("freight", "fret"):
        kind = "fret"
    elif kind == "pax":
        kind = "pax"

    mode = str(raw.get("mode", "unknown")).lower()

    return {
        "palier": int(raw["palier"]),
        "line": int(raw["line"]),
        "mode": mode,
        "kind": kind,
        "veh": int(raw["veh"]),
        "days": int(raw.get("days", 0)),
        "trips": int(raw.get("trips", 0)),
        "profit_obs": float(raw.get("profit_obs", 0.0)),
        "p_annual": float(raw["p_annual"]),
        "pred_amort": float(raw.get("pred_amort", 0.0)),
        "predicted": float(raw.get("predicted", 0.0)),
    }


def group_vehicle_windows(records: List[Dict[str, Any]]) -> List[Dict[int, Dict[str, Any]]]:
    """Groupe les enregistrements par fenetre d'observation de chaque vehicule.

    Chaque fenetre temporelle porte au plus une observation par palier (3, 6, 12, 24).
    Si un vehicule re-ouvre une fenetre (remplacement), une nouvelle fenetre commence.
    """
    by_veh: Dict[Tuple[int, int], List[Dict[int, Dict[str, Any]]]] = defaultdict(list)

    for rec in records:
        key = (rec["line"], rec["veh"])
        windows = by_veh[key]
        if not windows:
            windows.append({})
        cur_window = windows[-1]
        p = rec["palier"]
        if p in cur_window:
            # Re-ouverture de fenetre pour ce vehicule
            windows.append({})
            cur_window = windows[-1]
        cur_window[p] = rec

    all_windows: List[Dict[int, Dict[str, Any]]] = []
    for w_list in by_veh.values():
        all_windows.extend(w_list)
    return all_windows


def compute_metric_stats(errors: List[float]) -> Dict[str, Any]:
    """Calcule mediane, MAE, biais et n d'une serie d'erreurs."""
    if not errors:
        return {"n": 0, "bias": None, "mae": None, "median": None}

    n = len(errors)
    bias = sum(errors) / float(n)
    mae = sum(abs(e) for e in errors) / float(n)
    s_err = sorted(errors)
    if n % 2 == 1:
        med = s_err[n // 2]
    else:
        med = (s_err[n // 2 - 1] + s_err[n // 2]) / 2.0

    return {
        "n": n,
        "bias": round(bias, 2),
        "mae": round(mae, 2),
        "median": round(med, 2),
    }


COMPARISONS = [
    ("3m_vs_12m", 3, 12),
    ("3m_vs_24m", 3, 24),
    ("6m_vs_12m", 6, 12),
    ("6m_vs_24m", 6, 24),
]


def evaluate_windows(windows: List[Dict[int, Dict[str, Any]]]) -> Dict[str, Any]:
    """Evalue les erreurs pour l'ensemble des fenetres selon toutes les decoupes."""
    categories: Dict[str, List[Dict[int, Dict[str, Any]]]] = defaultdict(list)

    for w in windows:
        # Prendre le premier palier present pour deduire mode et genre
        rep = next(iter(w.values()))
        mode = rep["mode"].upper()
        kind = rep["kind"]

        categories["OVERALL"].append(w)
        categories[f"MODE_{mode}"].append(w)
        categories[f"KIND_{kind}"].append(w)
        categories[f"{mode}_{kind}"].append(w)

    results: Dict[str, Dict[str, Any]] = {}

    for cat_name, cat_windows in categories.items():
        cat_stats: Dict[str, Any] = {}
        for comp_name, p_early, p_real in COMPARISONS:
            errors: List[float] = []
            for w in cat_windows:
                if p_early in w and p_real in w:
                    est = w[p_early]["p_annual"]
                    real = w[p_real]["p_annual"]
                    errors.append(est - real)
            cat_stats[comp_name] = compute_metric_stats(errors)
        results[cat_name] = cat_stats

    return results


def format_results_table(results: Dict[str, Dict[str, Any]]) -> str:
    """Produit un rapport formate en texte / markdown."""
    lines: List[str] = []
    lines.append("| Categorie | Comparaison | n | Biais (£/an) | MAE (£/an) | Mediane (£/an) |")
    lines.append("|---|---|---|---|---|---|")

    # Ordre de presentation
    order = [
        "OVERALL",
        "MODE_AIR", "MODE_RAIL", "MODE_ROAD",
        "KIND_pax", "KIND_fret",
        "AIR_pax", "AIR_fret",
        "RAIL_pax", "RAIL_fret",
        "ROAD_pax", "ROAD_fret"
    ]
    seen = set()
    for cat in order:
        if cat in results:
            seen.add(cat)
            for comp_name, _, _ in COMPARISONS:
                st = results[cat].get(comp_name, {})
                n = st.get("n", 0)
                b = st.get("bias")
                m = st.get("mae")
                med = st.get("median")
                b_str = f"{b:+.1f}" if b is not None else "-"
                m_str = f"{m:.1f}" if m is not None else "-"
                med_str = f"{med:+.1f}" if med is not None else "-"
                lines.append(f"| {cat} | {comp_name} | {n} | {b_str} | {m_str} | {med_str} |")

    # Reste eventuel
    for cat, comp_dict in sorted(results.items()):
        if cat in seen:
            continue
        for comp_name, _, _ in COMPARISONS:
            st = comp_dict.get(comp_name, {})
            n = st.get("n", 0)
            b = st.get("bias")
            m = st.get("mae")
            med = st.get("median")
            b_str = f"{b:+.1f}" if b is not None else "-"
            m_str = f"{m:.1f}" if m is not None else "-"
            med_str = f"{med:+.1f}" if med is not None else "-"
            lines.append(f"| {cat} | {comp_name} | {n} | {b_str} | {m_str} | {med_str} |")

    return "\n".join(lines)


def process_lines(lines_iter) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Traite un iterateur de lignes et rend les enregistrements et resultats."""
    records: List[Dict[str, Any]] = []
    for line in lines_iter:
        rec = parse_v268_line(line)
        if rec is not None:
            records.append(rec)
    windows = group_vehicle_windows(records)
    results = evaluate_windows(windows)
    return records, results


SYNTHETIC_TEST_EXTRACT = """
OPEX 1970-04-01 V268_EST palier=3 line=1 mode=air kind=pax veh=1 days=91 trips=25 profit_obs=3000 p_annual=11000 pred_amort=1000 predicted=10000
OPEX 1970-07-01 V268_EST palier=6 line=1 mode=air kind=pax veh=1 days=182 trips=50 profit_obs=5500 p_annual=10000 pred_amort=1000 predicted=10000
OPEX 1971-01-01 V268_EST palier=12 line=1 mode=air kind=pax veh=1 days=365 trips=100 profit_obs=10000 p_annual=9000 pred_amort=1000 predicted=10000
OPEX 1972-01-01 V268_EST palier=24 line=1 mode=air kind=pax veh=1 days=730 trips=200 profit_obs=19000 p_annual=8500 pred_amort=1000 predicted=10000

OPEX 1970-04-01 V268_EST palier=3 line=2 mode=rail kind=fret veh=2 days=91 trips=2 profit_obs=4000 p_annual=15000 pred_amort=1000 predicted=12000
OPEX 1970-07-01 V268_EST palier=6 line=2 mode=rail kind=fret veh=2 days=182 trips=4 profit_obs=7500 p_annual=14000 pred_amort=1000 predicted=12000
OPEX 1971-01-01 V268_EST palier=12 line=2 mode=rail kind=fret veh=2 days=365 trips=8 profit_obs=14000 p_annual=13000 pred_amort=1000 predicted=12000
OPEX 1972-01-01 V268_EST palier=24 line=2 mode=rail kind=fret veh=2 days=730 trips=16 profit_obs=27000 p_annual=12500 pred_amort=1000 predicted=12000

OPEX 1970-04-01 V268_EST palier=3 line=3 mode=road kind=pax veh=3 days=91 trips=12 profit_obs=1500 p_annual=5000 pred_amort=500 predicted=4500
OPEX 1970-07-01 V268_EST palier=6 line=3 mode=road kind=pax veh=3 days=182 trips=24 profit_obs=2800 p_annual=4800 pred_amort=500 predicted=4500
OPEX 1971-01-01 V268_EST palier=12 line=3 mode=road kind=pax veh=3 days=365 trips=48 profit_obs=5100 p_annual=4600 pred_amort=500 predicted=4500
OPEX 1972-01-01 V268_EST palier=24 line=3 mode=road kind=pax veh=3 days=730 trips=96 profit_obs=9800 p_annual=4400 pred_amort=500 predicted=4500
"""


def run_self_test() -> bool:
    """Execute le test unitaire interne sur l'extrait synthetique."""
    records, results = process_lines(SYNTHETIC_TEST_EXTRACT.strip().splitlines())
    assert len(records) == 12, f"Attendu 12 records, obtenu {len(records)}"

    # Verification AIR pax : veh 1
    # 3m=11000, 6m=10000, 12m=9000, 24m=8500
    # 3 vs 12: 11000 - 9000 = +2000
    # 3 vs 24: 11000 - 8500 = +2500
    # 6 vs 12: 10000 - 9000 = +1000
    # 6 vs 24: 10000 - 8500 = +1500
    air_stats = results["MODE_AIR"]
    assert air_stats["3m_vs_12m"]["n"] == 1
    assert air_stats["3m_vs_12m"]["bias"] == 2000.0
    assert air_stats["3m_vs_12m"]["mae"] == 2000.0
    assert air_stats["3m_vs_12m"]["median"] == 2000.0

    assert air_stats["3m_vs_24m"]["bias"] == 2500.0
    assert air_stats["6m_vs_12m"]["bias"] == 1000.0
    assert air_stats["6m_vs_24m"]["bias"] == 1500.0

    # Verification RAIL fret : veh 2
    # 3m=15000, 6m=14000, 12m=13000, 24m=12500
    # 3 vs 12: 15000 - 13000 = +2000
    # 6 vs 12: 14000 - 13000 = +1000
    rail_stats = results["MODE_RAIL"]
    assert rail_stats["3m_vs_12m"]["bias"] == 2000.0
    assert rail_stats["6m_vs_12m"]["bias"] == 1000.0

    # Verification ROAD pax : veh 3
    # 3m=5000, 6m=4800, 12m=4600, 24m=4400
    # 3 vs 12: 5000 - 4600 = +400
    # 6 vs 12: 4800 - 4600 = +200
    road_stats = results["MODE_ROAD"]
    assert road_stats["3m_vs_12m"]["bias"] == 400.0
    assert road_stats["6m_vs_12m"]["bias"] == 200.0

    # Verification OVERALL (3 vehicules)
    # 3 vs 12 : erreurs = [2000, 2000, 400] -> n=3, somme=4400, moyenne=1466.67, mediane=2000
    overall = results["OVERALL"]["3m_vs_12m"]
    assert overall["n"] == 3
    assert math.isclose(overall["bias"], 1466.67, abs_tol=0.01)
    assert math.isclose(overall["mae"], 1466.67, abs_tol=0.01)
    assert overall["median"] == 2000.0

    # Verification KIND fret (1 vehicule)
    fret = results["KIND_fret"]["3m_vs_12m"]
    assert fret["n"] == 1
    assert fret["bias"] == 2000.0

    # Verification KIND pax (2 vehicules : veh 1 et veh 3)
    # erreurs 3 vs 12 : [2000, 400] -> n=2, moyenne=1200, mediane=1200
    pax = results["KIND_pax"]["3m_vs_12m"]
    assert pax["n"] == 2
    assert pax["bias"] == 1200.0
    assert pax["mae"] == 1200.0
    assert pax["median"] == 1200.0

    print("SELFTEST OK: analyze_v268_early synthetic test passed.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyse des estimations precoces V268")
    parser.add_argument("file", nargs="?", help="Fichier JSONL ou log texte moteur")
    parser.add_argument("--json", action="store_true", help="Sortie structuree en JSON")
    parser.add_argument("--test", "--selftest", action="store_true", help="Execute le test interne")

    args = parser.parse_args()

    if args.test:
        run_self_test()
        return 0

    if args.file:
        with open(args.file, "r", encoding="utf-8", errors="replace") as f:
            records, results = process_lines(f)
    else:
        if sys.stdin.isatty():
            parser.print_help()
            return 1
        records, results = process_lines(sys.stdin)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"Enregistrements V268_EST detectes : {len(records)}")
        print(format_results_table(results))

    return 0


if __name__ == "__main__":
    sys.exit(main())
