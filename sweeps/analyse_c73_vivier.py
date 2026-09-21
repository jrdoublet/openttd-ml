#!/usr/bin/env python3
"""Analyseur de vivier et passes C73 (étape 1 : pourquoi la caisse dort).

Lit le jsonl produit par `diag_c69_bottleneck_probe.py --raw` (ou directement
les lignes de log OpenTTD) et affiche :
1. L'entonnoir de génération et sélection par année et par mode :
   examined -> rejets par raison -> produced -> after_topk -> to_select -> affordable -> selected
2. Le tableau annuel des passes du portefeuille :
   passes -> vivier vide (%) -> passes bâtisseuses (%) -> caisse et capital mobilisable moyens.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

EVENT_RE = re.compile(r"OPEX (\d+)-\d+-\d+ C69_BOTTLENECK\s*(.*)")
MODES = ("rail", "road", "air", "water", "fleet")


def parse_line(raw: str) -> Optional[Dict[str, Any]]:
    raw = raw.strip()
    if not raw:
        return None
    if raw.startswith("{") and raw.endswith("}"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    m = EVENT_RE.search(raw)
    if m:
        log_year, fields_str = m.group(1), m.group(2)
        fields: Dict[str, Any] = {"_log_year": int(log_year)}
        for token in fields_str.split():
            if "=" in token:
                k, v = token.split("=", 1)
                fields[k] = v
        return fields
    if "=" in raw:
        fields = {}
        for token in raw.split():
            if "=" in token:
                k, v = token.split("=", 1)
                fields[k] = v
        if "phase" in fields:
            return fields
    return None


def parse_stream(lines: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    vivier_events: List[Dict[str, Any]] = []
    passes_events: List[Dict[str, Any]] = []
    for line in lines:
        entry = parse_line(line)
        if not entry:
            continue
        phase = entry.get("phase")
        if phase == "vivier_year":
            vivier_events.append(entry)
        elif phase == "passes_year":
            passes_events.append(entry)
    return vivier_events, passes_events


def aggregate_vivier(
    events: List[Dict[str, Any]]
) -> Dict[Tuple[int, str], Dict[str, Any]]:
    """Agrège les métriques du vivier par (year, mode)."""
    agg: Dict[Tuple[int, str], Dict[str, Any]] = {}
    for e in events:
        try:
            year = int(e.get("year", e.get("_log_year", 0)))
        except (TypeError, ValueError):
            continue
        mode = str(e.get("mode", "unknown"))
        key = (year, mode)
        if key not in agg:
            agg[key] = {
                "year": year,
                "mode": mode,
                "seeds": set(),
                "examined": 0,
                "rejections": defaultdict(int),
                "produced": 0,
                "after_topk": 0,
                "to_select": 0,
                "affordable": 0,
                "selected": 0,
            }
        rec = agg[key]
        if "seed" in e:
            rec["seeds"].add(e["seed"])
        rec["examined"] += int(e.get("examined", 0))
        rec["produced"] += int(e.get("produced", 0))
        rec["after_topk"] += int(e.get("after_topk", 0))
        rec["to_select"] += int(e.get("to_select", 0))
        rec["affordable"] += int(e.get("affordable", 0))
        rec["selected"] += int(e.get("selected", 0))
        for k, v in e.items():
            if k.startswith("rej_"):
                reason = k[4:]
                try:
                    rec["rejections"][reason] += int(v)
                except (TypeError, ValueError):
                    pass
    return agg


def aggregate_passes(
    events: List[Dict[str, Any]]
) -> Dict[int, Dict[str, Any]]:
    """Agrège les passes du portefeuille par year."""
    agg: Dict[int, Dict[str, Any]] = {}
    for e in events:
        try:
            year = int(e.get("year", e.get("_log_year", 0)))
        except (TypeError, ValueError):
            continue
        if year not in agg:
            agg[year] = {
                "year": year,
                "seeds": set(),
                "passes": 0,
                "empty": 0,
                "built": 0,
                "sum_cash_weighted": 0.0,
                "sum_avail_weighted": 0.0,
            }
        rec = agg[year]
        if "seed" in e:
            rec["seeds"].add(e["seed"])
        cnt = int(e.get("passes", 0))
        rec["passes"] += cnt
        rec["empty"] += int(e.get("empty", 0))
        rec["built"] += int(e.get("built", 0))
        try:
            cash = float(e.get("avg_cash", 0.0))
            avail = float(e.get("avg_avail", 0.0))
            rec["sum_cash_weighted"] += cash * cnt
            rec["sum_avail_weighted"] += avail * cnt
        except (TypeError, ValueError):
            pass
    for year, rec in agg.items():
        p = rec["passes"]
        rec["avg_cash"] = (rec["sum_cash_weighted"] / p) if p > 0 else 0.0
        rec["avg_avail"] = (rec["sum_avail_weighted"] / p) if p > 0 else 0.0
    return agg


def format_currency(val: float) -> str:
    ival = int(round(val))
    return f"{ival:n}" if hasattr(ival, "__format__") else f"{ival:,}"


def format_funnel_table(agg_vivier: Dict[Tuple[int, str], Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("=" * 105)
    lines.append("ENTONNOIR DU VIVIER C73 (par an et par mode)")
    lines.append("=" * 105)
    header = (
        f"{'Année':<6} {'Mode':<6} {'Exam':>7} {'Rejets':>7} {'Prod':>6} "
        f"{'TopK':>6} {'ToSel':>6} {'Financ':>7} {'Elu':>5}  {'Principaux rejets'}"
    )
    lines.append(header)
    lines.append("-" * 105)

    sorted_keys = sorted(agg_vivier.keys(), key=lambda k: (k[0], MODES.index(k[1]) if k[1] in MODES else 99))
    for key in sorted_keys:
        d = agg_vivier[key]
        year, mode = key
        exam = d["examined"]
        prod = d["produced"]
        topk = d["after_topk"]
        tosel = d["to_select"]
        aff = d["affordable"]
        sel = d["selected"]
        tot_rej = sum(d["rejections"].values())
        
        sorted_rejs = sorted(d["rejections"].items(), key=lambda x: x[1], reverse=True)
        top_rejs = ", ".join(f"{r}:{c}" for r, c in sorted_rejs[:3] if c > 0)
        
        row = (
            f"{year:<6} {mode:<6} {exam:>7} {tot_rej:>7} {prod:>6} "
            f"{topk:>6} {tosel:>6} {aff:>7} {sel:>5}  {top_rejs}"
        )
        lines.append(row)
    return "\n".join(lines)


def format_rejection_detail(agg_vivier: Dict[Tuple[int, str], Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("\n" + "=" * 80)
    lines.append("DÉTAIL COMPLET DES REJETS DE GÉNÉRATION (par an et mode)")
    lines.append("=" * 80)
    sorted_keys = sorted(agg_vivier.keys(), key=lambda k: (k[0], MODES.index(k[1]) if k[1] in MODES else 99))
    for key in sorted_keys:
        d = agg_vivier[key]
        year, mode = key
        exam = d["examined"]
        sorted_rejs = [(r, c) for r, c in sorted(d["rejections"].items(), key=lambda x: x[1], reverse=True) if c > 0]
        if not sorted_rejs and exam == 0:
            continue
        tot_rej = sum(c for _, c in sorted_rejs)
        lines.append(f"[{year}] {mode:<6} (examinés={exam}, rejetés={tot_rej}, produits={d['produced']}, élus={d['selected']}) :")
        if not sorted_rejs:
            lines.append("    (aucun rejet enregistré)")
        for r, c in sorted_rejs:
            pct = (c * 100.0 / exam) if exam > 0 else 0.0
            lines.append(f"    - rej_{r:<24} : {c:>6} ({pct:>5.1f} %)")
    return "\n".join(lines)


def format_passes_table(agg_passes: Dict[int, Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("\n" + "=" * 80)
    lines.append("TABLEAU DES PASSES DU PORTEFEUILLE C73")
    lines.append("=" * 80)
    header = f"{'Année':<6} {'Passes':>8} {'Vide':>7} {'% Vide':>8} {'Bâtit':>7} {'% Bâtit':>8} {'Caisse moy (£)':>16} {'Avail moy (£)':>16}"
    lines.append(header)
    lines.append("-" * 80)

    for year in sorted(agg_passes.keys()):
        d = agg_passes[year]
        p = d["passes"]
        empty = d["empty"]
        built = d["built"]
        pct_empty = (empty * 100.0 / p) if p > 0 else 0.0
        pct_built = (built * 100.0 / p) if p > 0 else 0.0
        cash_str = f"{int(round(d['avg_cash'])):,}"
        avail_str = f"{int(round(d['avg_avail'])):,}"
        row = f"{year:<6} {p:>8} {empty:>7} {pct_empty:>7.1f}% {built:>7} {pct_built:>7.1f}% {cash_str:>16} {avail_str:>16}"
        lines.append(row)
    return "\n".join(lines)


def run_selftest() -> None:
    sample_lines = [
        # JSONL format from diag_c69_bottleneck_probe.py --raw
        json.dumps({
            "seed": 100, "phase": "vivier_year", "year": "1970", "mode": "rail",
            "examined": "150", "rej_origin_served": "40", "rej_distance_short": "20",
            "rej_profit_nonpositive": "50", "produced": "40", "after_topk": "10",
            "to_select": "10", "affordable": "4", "selected": "1"
        }),
        json.dumps({
            "seed": 100, "phase": "vivier_year", "year": "1970", "mode": "road",
            "examined": "300", "rej_origin_served": "180", "rej_profit_nonpositive": "60",
            "produced": "60", "after_topk": "20", "to_select": "20", "affordable": "10", "selected": "2"
        }),
        json.dumps({
            "seed": 100, "phase": "vivier_year", "year": "1970", "mode": "air",
            "examined": "80", "rej_town_pop_small": "30", "rej_distance_short": "20",
            "produced": "30", "after_topk": "30", "to_select": "30", "affordable": "5", "selected": "1"
        }),
        json.dumps({
            "seed": 100, "phase": "vivier_year", "year": "1970", "mode": "water",
            "examined": "50", "rej_distance_short": "30", "rej_no_connection": "15",
            "produced": "5", "after_topk": "5", "to_select": "5", "affordable": "2", "selected": "1"
        }),
        json.dumps({
            "seed": 100, "phase": "vivier_year", "year": "1970", "mode": "fleet",
            "examined": "4", "rej_airport_capacity_reached": "2",
            "produced": "2", "after_topk": "2", "to_select": "2", "affordable": "2", "selected": "1"
        }),
        json.dumps({
            "seed": 100, "phase": "passes_year", "year": "1970",
            "passes": "24", "empty": "14", "built": "6", "avg_cash": "2500000", "avg_avail": "3200000"
        }),
        # Second seed to verify aggregation
        json.dumps({
            "seed": 42, "phase": "vivier_year", "year": "1970", "mode": "rail",
            "examined": "100", "rej_origin_served": "30", "rej_distance_short": "10",
            "rej_profit_nonpositive": "40", "produced": "20", "after_topk": "10",
            "to_select": "10", "affordable": "2", "selected": "1"
        }),
        json.dumps({
            "seed": 42, "phase": "passes_year", "year": "1970",
            "passes": "20", "empty": "12", "built": "5", "avg_cash": "3000000", "avg_avail": "3500000"
        }),
        # Also raw log format test
        "OPEX 1972-1-1 C69_BOTTLENECK phase=vivier_year year=1971 mode=rail examined=200 rej_origin_served=50 produced=50 after_topk=10 to_select=10 affordable=5 selected=2",
        "OPEX 1972-1-1 C69_BOTTLENECK phase=passes_year year=1971 passes=25 empty=15 built=7 avg_cash=4000000 avg_avail=5000000",
    ]

    vivier_ev, passes_ev = parse_stream(sample_lines)
    assert len(vivier_ev) == 7, f"Expected 7 vivier events, got {len(vivier_ev)}"
    assert len(passes_ev) == 3, f"Expected 3 passes events, got {len(passes_ev)}"

    agg_v = aggregate_vivier(vivier_ev)
    # Check 1970 rail aggregated across seed 100 and seed 42
    r70 = agg_v[(1970, "rail")]
    assert r70["examined"] == 250
    assert r70["rejections"]["origin_served"] == 70
    assert r70["rejections"]["distance_short"] == 30
    assert r70["produced"] == 60
    assert r70["after_topk"] == 20
    assert r70["to_select"] == 20
    assert r70["affordable"] == 6
    assert r70["selected"] == 2

    # Check 1971 rail from raw log
    r71 = agg_v[(1971, "rail")]
    assert r71["examined"] == 200
    assert r71["selected"] == 2

    agg_p = aggregate_passes(passes_ev)
    p70 = agg_p[1970]
    assert p70["passes"] == 44
    assert p70["empty"] == 26
    assert p70["built"] == 11
    # Weighted avg cash: (2500000 * 24 + 3000000 * 20) / 44 = 2727272.727
    expected_cash = (2500000 * 24 + 3000000 * 20) / 44
    assert abs(p70["avg_cash"] - expected_cash) < 1e-3

    table_v = format_funnel_table(agg_v)
    assert "ENTONNOIR DU VIVIER C73" in table_v
    assert "rail" in table_v
    assert "road" in table_v

    detail_v = format_rejection_detail(agg_v)
    assert "rej_origin_served" in detail_v
    assert "rej_town_pop_small" in detail_v

    table_p = format_passes_table(agg_p)
    assert "TABLEAU DES PASSES DU PORTEFEUILLE C73" in table_p
    assert "44" in table_p

    print("selftest passed: C73 vivier & passes analyser verified")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="Fichiers jsonl bruts (ou stdin si vide)")
    parser.add_argument("--raw", type=Path, default=None, help="Chemin vers le fichier jsonl produit par --raw")
    parser.add_argument("--selftest", action="store_true", help="Lance la suite d'auto-tests internes")
    parser.add_argument("--detail", action="store_true", default=True, help="Affiche le détail complet des rejets")
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

    vivier_ev, passes_ev = parse_stream(lines)
    if not vivier_ev and not passes_ev:
        sys.stderr.write("Aucun événement C73 (vivier_year ou passes_year) trouvé dans l'entrée.\n")
        sys.exit(1)

    if vivier_ev:
        agg_v = aggregate_vivier(vivier_ev)
        print(format_funnel_table(agg_v))
        if args.detail:
            print(format_rejection_detail(agg_v))

    if passes_ev:
        agg_p = aggregate_passes(passes_ev)
        print(format_passes_table(agg_p))


if __name__ == "__main__":
    main()
