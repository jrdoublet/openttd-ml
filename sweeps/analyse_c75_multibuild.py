#!/usr/bin/env python3
"""Analyseur multi-chantiers C75 (étape 2 : le levier multi-build en phase riche).

Lit le jsonl produit par `diag_c69_bottleneck_probe.py --raw` (ou directement
les lignes de log OpenTTD) et affiche par année et par graine :
1. Le nombre de passes de la tâche projects
2. Le nombre de chantiers construits
3. Le ratio chantiers par passe
4. Le K_pass médian (flux d'exploitation F × intervalle moyen tau_pass)
5. Le tau_pass médian (jours moyens entre deux passes de projects)
6. La répartition des raisons d'arrêt :
   - k_pass : capital du projet >= K_pass
   - cash : capital du projet > capital disponible
   - list_end : fin de liste du vivier atteinte
   - rail_search : recherche A* rail suspendue (pending)
   - single(levier off) : arrêt unitaire classique (levier désactivé)
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import statistics
import sys
from typing import Any, Dict, List, Optional, Tuple

EVENT_RE = re.compile(r"OPEX (\d+)-\d+-\d+ C69_BOTTLENECK\s*(.*)")
STOP_REASONS = ("k_pass", "cash", "list_end", "rail_search", "single(levier off)")


def parse_line(raw: str) -> List[Dict[str, Any]]:
    """Extrait les événements C75 d'une ligne (JSON ou log brut)."""
    raw = raw.strip()
    if not raw:
        return []

    if raw.startswith("{") and raw.endswith("}"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                # Si c'est directement un événement avec 'phase'
                if "phase" in data:
                    return [data]
                # Si c'est un conteneur de run avec 'openttd_output' ou 'stdout'
                output_text = data.get("openttd_output") or data.get("stdout") or ""
                seed = data.get("seed")
                if output_text:
                    events = []
                    for line in output_text.splitlines():
                        sub_events = parse_line(line)
                        for ev in sub_events:
                            if seed is not None and "seed" not in ev:
                                ev["seed"] = seed
                            events.append(ev)
                    return events
                return [data]
        except json.JSONDecodeError:
            pass

    m = EVENT_RE.search(raw)
    if m:
        log_year, fields_str = m.group(1), m.group(2)
        fields: Dict[str, Any] = {"_log_year": int(log_year)}
        last_k = None
        for token in fields_str.split():
            if "=" in token:
                k, v = token.split("=", 1)
                fields[k] = v
                last_k = k
            elif last_k:
                fields[last_k] += " " + token
        if "phase" in fields:
            return [fields]
        return []

    if "=" in raw:
        fields = {}
        last_k = None
        for token in raw.split():
            if "=" in token:
                k, v = token.split("=", 1)
                fields[k] = v
                last_k = k
            elif last_k:
                fields[last_k] += " " + token
        if "phase" in fields:
            return [fields]

    return []


def parse_stream(lines: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Sépare les événements c75_pass et c75_year."""
    pass_events: List[Dict[str, Any]] = []
    year_events: List[Dict[str, Any]] = []

    for line in lines:
        for entry in parse_line(line):
            phase = entry.get("phase")
            if phase == "c75_pass":
                pass_events.append(entry)
            elif phase == "c75_year":
                year_events.append(entry)

    return pass_events, year_events


def aggregate_c75(
    pass_events: List[Dict[str, Any]],
    year_events: List[Dict[str, Any]],
) -> Dict[Tuple[int, Any], Dict[str, Any]]:
    """Agrège les métriques C75 par (year, seed)."""
    agg: Dict[Tuple[int, Any], Dict[str, Any]] = {}

    def get_or_create(year: int, seed: Any) -> Dict[str, Any]:
        key = (year, seed)
        if key not in agg:
            agg[key] = {
                "year": year,
                "seed": seed,
                "passes": 0,
                "builds": 0,
                "multi_passes": 0,
                "k_pass_list": [],
                "tau_pass_list": [],
                "f_list": [],
                "built_list": [],
                "stop_reasons": defaultdict(int),
                "has_year_event": False,
            }
        return agg[key]

    for ye in year_events:
        try:
            year = int(ye.get("year", ye.get("_log_year", 0)))
        except (TypeError, ValueError):
            continue
        seed = ye.get("seed", "all")
        rec = get_or_create(year, seed)
        rec["passes"] += int(ye.get("passes", 0))
        rec["builds"] += int(ye.get("builds", 0))
        rec["multi_passes"] += int(ye.get("multi_passes", 0))
        rec["has_year_event"] = True

    for pe in pass_events:
        try:
            year = int(pe.get("year", pe.get("_log_year", 0)))
        except (TypeError, ValueError):
            continue
        seed = pe.get("seed", "all")
        rec = get_or_create(year, seed)

        built = int(pe.get("built", 0))
        rec["built_list"].append(built)

        if not rec["has_year_event"]:
            # Si pas de c75_year pour cette année/graine, décompte à partir des passes bâtisseuses
            rec["builds"] += built
            rec["passes"] += 1
            if built > 1:
                rec["multi_passes"] += 1

        try:
            k_pass = float(pe.get("k_pass", 0.0))
            rec["k_pass_list"].append(k_pass)
        except (TypeError, ValueError):
            pass

        try:
            tau_pass = float(pe.get("tau_pass", 0.0))
            rec["tau_pass_list"].append(tau_pass)
        except (TypeError, ValueError):
            pass

        try:
            f_val = float(pe.get("F", 0.0))
            rec["f_list"].append(f_val)
        except (TypeError, ValueError):
            pass

        stop = str(pe.get("stop", "unknown"))
        rec["stop_reasons"][stop] += 1

    return agg


def format_table(agg: Dict[Tuple[int, Any], Dict[str, Any]]) -> str:
    """Formate les résultats par année et par graine dans un tableau texte."""
    if not agg:
        return "Aucune donnée C75 trouvée."

    lines = []
    lines.append("=" * 115)
    lines.append("TABLEAU C75 : MULTI-BUILD PAR PASSE EN PHASE RICHE")
    lines.append("=" * 115)
    header = (
        f"{'Année':<6} | {'Graine':<8} | {'Passes':<6} | {'Chantiers':<9} | "
        f"{'Ch/Passe':<8} | {'K_pass méd':<10} | {'τ_pass méd':<10} | "
        f"{'Raisons d arrêt (k_pass / cash / fin / rail / single)':<40}"
    )
    lines.append(header)
    lines.append("-" * 115)

    sorted_keys = sorted(agg.keys(), key=lambda k: (k[0], str(k[1])))
    for key in sorted_keys:
        rec = agg[key]
        year = rec["year"]
        seed = str(rec["seed"])
        passes = rec["passes"]
        builds = rec["builds"]
        ch_per_pass = (builds / passes) if passes > 0 else 0.0

        med_k = statistics.median(rec["k_pass_list"]) if rec["k_pass_list"] else 0.0
        med_tau = statistics.median(rec["tau_pass_list"]) if rec["tau_pass_list"] else 0.0

        reasons = rec["stop_reasons"]
        total_stops = sum(reasons.values())
        k_cnt = reasons.get("k_pass", 0)
        cash_cnt = reasons.get("cash", 0)
        end_cnt = reasons.get("list_end", 0)
        rail_cnt = reasons.get("rail_search", 0)
        single_cnt = reasons.get("single(levier off)", 0)

        stops_summary = f"{k_cnt}/{cash_cnt}/{end_cnt}/{rail_cnt}/{single_cnt}"
        if total_stops > 0:
            stops_summary += f" (tot={total_stops})"

        row = (
            f"{year:<6} | {seed:<8} | {passes:<6} | {builds:<9} | "
            f"{ch_per_pass:<8.2f} | {int(med_k):<10} | {med_tau:<10.1f} | "
            f"{stops_summary:<40}"
        )
        lines.append(row)

    lines.append("-" * 115)
    return "\n".join(lines)


def format_annual_summary(agg: Dict[Tuple[int, Any], Dict[str, Any]]) -> str:
    """Formate un résumé consolidé par année (toutes graines confondues)."""
    by_year: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
        "passes": 0,
        "builds": 0,
        "multi_passes": 0,
        "k_pass_list": [],
        "tau_pass_list": [],
        "stop_reasons": defaultdict(int),
        "seeds": set(),
    })

    for (year, seed), rec in agg.items():
        by_year[year]["passes"] += rec["passes"]
        by_year[year]["builds"] += rec["builds"]
        by_year[year]["multi_passes"] += rec["multi_passes"]
        by_year[year]["k_pass_list"].extend(rec["k_pass_list"])
        by_year[year]["tau_pass_list"].extend(rec["tau_pass_list"])
        by_year[year]["seeds"].add(seed)
        for r, cnt in rec["stop_reasons"].items():
            by_year[year]["stop_reasons"][r] += cnt

    lines = []
    lines.append("\n" + "=" * 115)
    lines.append("SYNTHÈSE ANNUELLE C75 (CONSOLIDÉE TOUTES GRAINES)")
    lines.append("=" * 115)
    header = (
        f"{'Année':<6} | {'Graines':<7} | {'Passes':<7} | {'Chantiers':<9} | "
        f"{'Ch/Passe':<8} | {'MultiPass':<9} | {'K_pass méd':<10} | {'τ_pass méd':<10} | "
        f"{'Arrêts (k_pass / cash / fin / rail / single)':<35}"
    )
    lines.append(header)
    lines.append("-" * 115)

    for year in sorted(by_year.keys()):
        yrec = by_year[year]
        passes = yrec["passes"]
        builds = yrec["builds"]
        mp = yrec["multi_passes"]
        ch_per_pass = (builds / passes) if passes > 0 else 0.0

        med_k = statistics.median(yrec["k_pass_list"]) if yrec["k_pass_list"] else 0.0
        med_tau = statistics.median(yrec["tau_pass_list"]) if yrec["tau_pass_list"] else 0.0

        reasons = yrec["stop_reasons"]
        k_cnt = reasons.get("k_pass", 0)
        cash_cnt = reasons.get("cash", 0)
        end_cnt = reasons.get("list_end", 0)
        rail_cnt = reasons.get("rail_search", 0)
        single_cnt = reasons.get("single(levier off)", 0)

        stops_summary = f"{k_cnt}/{cash_cnt}/{end_cnt}/{rail_cnt}/{single_cnt}"

        row = (
            f"{year:<6} | {len(yrec['seeds']):<7} | {passes:<7} | {builds:<9} | "
            f"{ch_per_pass:<8.2f} | {mp:<9} | {int(med_k):<10} | {med_tau:<10.1f} | "
            f"{stops_summary:<35}"
        )
        lines.append(row)

    lines.append("-" * 115)
    return "\n".join(lines)


def run_selftest() -> None:
    """Auto-test interne avec données synthétiques."""
    sample_lines = [
        # Graine 100, 1974 : 2 passes qui construisent, levier off
        'OPEX 1974-03-15 C69_BOTTLENECK phase=c75_pass year=1974 built=1 k_pass=100000 tau_pass=45.0 F=2222.2 stop=single(levier off)',
        'OPEX 1974-08-20 C69_BOTTLENECK phase=c75_pass year=1974 built=1 k_pass=120000 tau_pass=46.0 F=2608.7 stop=single(levier off)',
        'OPEX 1975-01-01 C69_BOTTLENECK phase=c75_year year=1974 passes=8 builds=2 multi_passes=0',
        # Graine 100, 1975 : multi-build actif (2 chantiers, puis arrêt k_pass ; 3 chantiers, puis cash)
        '{"seed": 100, "phase": "c75_pass", "year": "1975", "built": "2", "k_pass": "250000", "tau_pass": "40.0", "F": "6250.0", "stop": "k_pass"}',
        '{"seed": 100, "phase": "c75_pass", "year": "1975", "built": "3", "k_pass": "300000", "tau_pass": "38.0", "F": "7894.7", "stop": "cash"}',
        '{"seed": 100, "phase": "c75_year", "year": "1975", "passes": "9", "builds": "5", "multi_passes": "2"}',
        # Graine 42, 1975 : 1 passe avec 2 chantiers arrêt fin de liste, 1 passe rail_search
        '{"seed": 42, "phase": "c75_pass", "year": "1975", "built": "2", "k_pass": "200000", "tau_pass": "42.0", "F": "4761.9", "stop": "list_end"}',
        '{"seed": 42, "phase": "c75_pass", "year": "1975", "built": "1", "k_pass": "210000", "tau_pass": "41.0", "F": "5121.9", "stop": "rail_search"}',
        '{"seed": 42, "phase": "c75_year", "year": "1975", "passes": "8", "builds": "3", "multi_passes": "1"}',
    ]

    pass_ev, year_ev = parse_stream(sample_lines)
    assert len(pass_ev) == 6, f"Expected 6 pass events, got {len(pass_ev)}"
    assert len(year_ev) == 3, f"Expected 3 year events, got {len(year_ev)}"

    agg = aggregate_c75(pass_ev, year_ev)

    # Vérification 1974 (graine par défaut 'all' car non spécifiée dans les logs bruts)
    r74 = agg.get((1974, "all"))
    assert r74 is not None
    assert r74["passes"] == 8
    assert r74["builds"] == 2
    assert r74["multi_passes"] == 0
    assert r74["stop_reasons"]["single(levier off)"] == 2
    assert abs(statistics.median(r74["k_pass_list"]) - 110000.0) < 1e-3

    # Vérification 1975 seed 100
    r75_100 = agg.get((1975, 100))
    assert r75_100 is not None
    assert r75_100["passes"] == 9
    assert r75_100["builds"] == 5
    assert r75_100["multi_passes"] == 2
    assert r75_100["stop_reasons"]["k_pass"] == 1
    assert r75_100["stop_reasons"]["cash"] == 1
    assert abs(statistics.median(r75_100["k_pass_list"]) - 275000.0) < 1e-3

    # Vérification 1975 seed 42
    r75_42 = agg.get((1975, 42))
    assert r75_42 is not None
    assert r75_42["passes"] == 8
    assert r75_42["builds"] == 3
    assert r75_42["multi_passes"] == 1
    assert r75_42["stop_reasons"]["list_end"] == 1
    assert r75_42["stop_reasons"]["rail_search"] == 1

    table_str = format_table(agg)
    assert "TABLEAU C75" in table_str
    assert "1974" in table_str
    assert "1975" in table_str

    annual_str = format_annual_summary(agg)
    assert "SYNTHÈSE ANNUELLE C75" in annual_str

    print("selftest passed: C75 multibuild analyser verified")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="Fichiers jsonl ou logs bruts (ou stdin si vide)")
    parser.add_argument("--raw", type=Path, default=None, help="Chemin vers le fichier jsonl produit par --raw")
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
        sys.stderr.write("Aucune ligne d'entrée trouvée.\n")
        sys.exit(1)

    pass_ev, year_ev = parse_stream(lines)
    if not pass_ev and not year_ev:
        sys.stderr.write("Aucun événement C75 (c75_pass ou c75_year) trouvé dans l'entrée.\n")
        sys.exit(1)

    agg = aggregate_c75(pass_ev, year_ev)
    print(format_table(agg))
    print(format_annual_summary(agg))


if __name__ == "__main__":
    main()
