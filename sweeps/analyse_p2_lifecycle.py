#!/usr/bin/env python3
"""Analyseur P2 : cycle de vie du portefeuille post-build sous probe_scheduler=1.

Lit les enregistrements `P2_BUILD` et `P2_RESOLVE` émis par OpexAI.
Établit :
1. L'état du portefeuille avant et après chaque construction.
2. Les causes de vide du portefeuille (`emptyCause`).
3. Le délai de retour à un vivier non vide (jours, ticks).
4. Les facteurs déclencheurs du retour à non-vide (`ret_reason`).
5. Recoupements stricts des totaux (assertions mathématiques).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

P2_BUILD_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) P2_BUILD\s+(.*)$", re.M)
P2_RESOLVE_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) P2_RESOLVE\s+(.*)$", re.M)
FIELD_RE = re.compile(r"(\w+)=(\S+)")

EMPTY_CAUSE_DESCRIPTIONS = {
    "none": "Portefeuille non vidé (funded > 0 après la mise à jour incrémentale)",
    "all_unaffordable": "Candidats présents dans le vivier, mais tous plus chers que le capital restant",
    "cache_exhausted": "Vivier incrémental scanné mais aucun candidat retenu valide",
    "abandon_filtered": "Tous les candidats filtrés par la liste d'abandons",
    "stage_empty": "Étape de génération vide (staged bootstrap sans candidats du mode)",
    "empty_pool": "Vivier initialement vide (aucun candidat disponible)",
    "selection_empty": "Candidats abordables présents mais sélection optimale vide",
    "unknown": "Cause non qualifiée",
}

RETURN_REASON_DESCRIPTIONS = {
    "immediate": "Immédiat : le portefeuille n'était pas devenu vide (funded > 0)",
    "month": "Nouveau mois : rafraîchissement mensuel du catalogue",
    "capital": "Augmentation de capital : seuil de réveil atteint (>2x ou +50k£)",
    "invalidation": "Invalidation événementielle : changement d'état ou subvention expirée",
    "layers": "Changement de couche C76 (ex: nouvelles lignes, villes)",
    "periodic": "Filet périodique C76 annuel de sûreté",
    "air_fleet": "Injection flotte : opportunités aériennes ajoutées au vivier",
    "targeted_air": "Génération ciblée (veille de slots C83)",
    "catalog_other": "Autre déclencheur de rafraîchissement du catalogue",
    "other": "Autre tâche ordonnanceur",
    "sim_end": "Fin de simulation avant retour à non-vide",
}


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_fields(rest: str) -> dict[str, str]:
    return {key: value for key, value in FIELD_RE.findall(rest or "")}


def parse_p2_output(output: str, seed: int | None = None) -> list[dict]:
    """Parse les lignes P2_BUILD et P2_RESOLVE et assemble les cycles complets."""
    builds: dict[int, dict] = {}
    build_order: list[int] = []

    for year, month, day, rest in P2_BUILD_RE.findall(output or ""):
        fields = parse_fields(rest)
        b_id = _to_int(fields.get("id"), -1)
        if b_id < 0:
            continue
        date_str = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        rec = {
            "id": b_id,
            "seed": seed,
            "build_date": date_str,
            "build_year": int(year),
            "build_month": int(month),
            "build_day": int(day),
            "mode": fields.get("mode", "unknown"),
            "n_built": _to_int(fields.get("n_built"), 1),
            "cap_before": _to_int(fields.get("cap_before")),
            "cap_after": _to_int(fields.get("cap_after")),
            "cg_before": _to_int(fields.get("cg_before")),
            "cg_after": _to_int(fields.get("cg_after")),
            "scanned": _to_int(fields.get("scanned")),
            "retained": _to_int(fields.get("retained")),
            "abandon": _to_int(fields.get("abandon")),
            "alts": _to_int(fields.get("alts")),
            "funded": _to_int(fields.get("funded")),
            "cause": fields.get("cause", "unknown"),
            "next_k": _to_int(fields.get("next_k")),
            # Valeurs par défaut avant résolution :
            "resolved": False,
            "days_until_nonempty": -1,
            "ticks_until_nonempty": -1,
            "ret_reason": "sim_end",
            "ret_task": "sim_end",
            "ret_date": None,
            "ret_funded": 0,
            "ret_cause": None,
        }
        builds[b_id] = rec
        build_order.append(b_id)

    for year, month, day, rest in P2_RESOLVE_RE.findall(output or ""):
        fields = parse_fields(rest)
        b_id = _to_int(fields.get("id"), -1)
        if b_id in builds:
            rec = builds[b_id]
            rec["resolved"] = True
            rec["days_until_nonempty"] = _to_int(fields.get("days"), 0)
            rec["ticks_until_nonempty"] = _to_int(fields.get("ticks"), 0)
            rec["ret_reason"] = fields.get("ret_reason", "other")
            rec["ret_task"] = fields.get("ret_task", "other")
            rec["ret_date"] = fields.get("ret_date", f"{int(year):04d}-{int(month):02d}-{int(day):02d}")
            rec["ret_funded"] = _to_int(fields.get("funded"), 0)
            rec["ret_cause"] = fields.get("cause", "none")

    events = [builds[b_id] for b_id in build_order]
    return events


def verify_p2_invariants(events: list[dict]) -> None:
    """Vérifie strictement la cohérence mathématique et les invariants de P2."""
    if not events:
        return

    n_total = len(events)
    by_mode = Counter(e["mode"] for e in events)
    by_cause = Counter(e["cause"] for e in events)
    by_reason = Counter(e["ret_reason"] for e in events)

    # Invariant 1 : recoupement exact des totaux
    sum_mode = sum(by_mode.values())
    sum_cause = sum(by_cause.values())
    sum_reason = sum(by_reason.values())

    assert sum_mode == n_total, f"Recoupement mode divergent: {sum_mode} != {n_total}"
    assert sum_cause == n_total, f"Recoupement emptyCause divergent: {sum_cause} != {n_total}"
    assert sum_reason == n_total, f"Recoupement ret_reason divergent: {sum_reason} != {n_total}"

    # Invariant 2 : relations cause / retour
    for e in events:
        b_id = e["id"]
        cause = e["cause"]
        funded = e["funded"]
        days = e["days_until_nonempty"]
        reason = e["ret_reason"]

        if cause == "none":
            assert funded > 0, f"Build {b_id}: cause=none mais funded={funded}"
            assert days == 0, f"Build {b_id}: cause=none mais days={days}"
            assert reason == "immediate", f"Build {b_id}: cause=none mais reason={reason}"
        else:
            assert funded == 0, f"Build {b_id}: cause={cause} mais funded={funded} > 0"
            if reason != "sim_end":
                assert days >= 0, f"Build {b_id}: résolu mais days={days} < 0"


def _dist_stats(vals: list[int | float]) -> dict:
    if not vals:
        return {"n": 0, "moy": 0.0, "med": 0.0, "min": 0, "p90": 0.0, "max": 0}
    vals_sorted = sorted(vals)
    n = len(vals)
    p90_idx = int(math.ceil(0.90 * n)) - 1
    p90_val = vals_sorted[max(0, min(n - 1, p90_idx))]
    return {
        "n": n,
        "moy": round(statistics.mean(vals), 2),
        "med": round(statistics.median(vals), 2),
        "min": vals_sorted[0],
        "p90": p90_val,
        "max": vals_sorted[-1],
    }


def compute_perturbation_table(series: list[dict], baseline_series: list[dict]) -> list[dict]:
    by_seed_base = {r.get("seed"): r for r in baseline_series}
    table = []
    for var in series:
        s = var.get("seed")
        if s not in by_seed_base:
            continue
        base = by_seed_base[s]
        b_val = base.get("company_value") or 0
        v_val = var.get("company_value") or 0
        b_prof = base.get("profit_year") or 0
        v_prof = var.get("profit_year") or 0
        b_veh = base.get("n_vehicles") or 0
        v_veh = var.get("n_vehicles") or 0
        b_st = base.get("n_stations") or 0
        v_st = var.get("n_stations") or 0

        val_pct = ((v_val - b_val) / b_val * 100) if b_val > 0 else 0.0
        prof_pct = ((v_prof - b_prof) / b_prof * 100) if b_prof > 0 else 0.0

        table.append({
            "seed": s,
            "base_val": b_val,
            "var_val": v_val,
            "val_delta": v_val - b_val,
            "val_pct": val_pct,
            "base_prof": b_prof,
            "var_prof": v_prof,
            "prof_delta": v_prof - b_prof,
            "prof_pct": prof_pct,
            "base_veh": b_veh,
            "var_veh": v_veh,
            "veh_delta": v_veh - b_veh,
            "base_st": b_st,
            "var_st": v_st,
            "st_delta": v_st - b_st,
        })
    return table


def summarize_p2_events(
    events: list[dict],
    min_year: int = 1970,
    max_year: int = 1972,
    seed_series: list[dict] | None = None,
    baseline_series: list[dict] | None = None,
) -> dict:
    """Produit les agrégations statistiques et recoupements sur les années complètes."""
    verify_p2_invariants(events)

    filtered = [e for e in events if min_year <= e["build_year"] <= max_year]
    verify_p2_invariants(filtered)

    n_total = len(filtered)
    by_mode = Counter(e["mode"] for e in filtered)
    by_cause = Counter(e["cause"] for e in filtered)
    by_reason = Counter(e["ret_reason"] for e in filtered)

    # Répartition par graine
    by_seed: dict[int, list[dict]] = defaultdict(list)
    for e in filtered:
        by_seed[e.get("seed", 0)].append(e)

    # Cross-tab cause x reason
    cross_cause_reason: dict[str, Counter] = defaultdict(Counter)
    for e in filtered:
        cross_cause_reason[e["cause"]][e["ret_reason"]] += 1

    # Cross-tab mode x cause
    cross_mode_cause: dict[str, Counter] = defaultdict(Counter)
    for e in filtered:
        cross_mode_cause[e["mode"]][e["cause"]] += 1

    # Distributions des délais pour les portefeuilles qui sont devenus vides (cause != "none")
    emptied_events = [e for e in filtered if e["cause"] != "none" and e["resolved"]]
    days_emptied = [e["days_until_nonempty"] for e in emptied_events]
    ticks_emptied = [e["ticks_until_nonempty"] for e in emptied_events]

    days_stats = _dist_stats(days_emptied)
    ticks_stats = _dist_stats(ticks_emptied)

    # Distribution du capital requis pour le prochain projet vs capital restant
    next_k_vals = [e["next_k"] for e in emptied_events if e["next_k"] > 0]
    cap_after_vals = [e["cap_after"] for e in emptied_events]
    deficit_vals = [e["next_k"] - e["cap_after"] for e in emptied_events if e["next_k"] > 0]

    perturbation = None
    if seed_series and baseline_series:
        perturbation = compute_perturbation_table(seed_series, baseline_series)

    return {
        "n_total": n_total,
        "min_year": min_year,
        "max_year": max_year,
        "by_mode": dict(by_mode.most_common()),
        "by_cause": dict(by_cause.most_common()),
        "by_reason": dict(by_reason.most_common()),
        "cross_cause_reason": {k: dict(v) for k, v in cross_cause_reason.items()},
        "cross_mode_cause": {k: dict(v) for k, v in cross_mode_cause.items()},
        "days_stats": days_stats,
        "ticks_stats": ticks_stats,
        "next_k_stats": _dist_stats(next_k_vals),
        "cap_after_stats": _dist_stats(cap_after_vals),
        "deficit_stats": _dist_stats(deficit_vals),
        "by_seed_counts": {s: len(evs) for s, evs in sorted(by_seed.items())},
        "emptied_count": len(emptied_events),
        "immediate_count": sum(1 for e in filtered if e["cause"] == "none"),
        "perturbation": perturbation,
        "events": filtered,
    }


def format_p2_report(summary: dict) -> str:
    """Génère le compte-rendu textuel / markdown du diagnostic P2."""
    n = summary["n_total"]
    y_min = summary["min_year"]
    y_max = summary["max_year"]

    lines = [
        f"# Diagnostic P2 — Cycle de vie du portefeuille post-build ({y_min}–{y_max})",
        "",
        f"**Constructions totales observées : {n}** (sur {len(summary['by_seed_counts'])} graines).",
        f"- Portefeuilles restés immédiatement non vides (`cause=none`, funded > 0) : **{summary['immediate_count']}** ({summary['immediate_count'] / n * 100:.1f} %)" if n > 0 else "",
        f"- Portefeuilles vidés par la construction (`cause != none`, funded = 0) : **{summary['emptied_count']}** ({summary['emptied_count'] / n * 100:.1f} %)" if n > 0 else "",
        "",
        "## 1. Répartition des causes de vide (`emptyCause`)",
        "| Cause (`emptyCause`) | Événements | Part | Description |",
        "|---|---:|---:|---|",
    ]

    for cause, cnt in summary["by_cause"].items():
        pct = (cnt / n * 100) if n > 0 else 0.0
        desc = EMPTY_CAUSE_DESCRIPTIONS.get(cause, "Autre")
        lines.append(f"| `{cause}` | {cnt} | {pct:.1f} % | {desc} |")

    lines.extend([
        "",
        "## 2. Répartition des facteurs de retour à non-vide (`ret_reason`)",
        "| Déclencheur (`ret_reason`) | Événements | Part | Description |",
        "|---|---:|---:|---|",
    ])

    for reason, cnt in summary["by_reason"].items():
        pct = (cnt / n * 100) if n > 0 else 0.0
        desc = RETURN_REASON_DESCRIPTIONS.get(reason, "Autre")
        lines.append(f"| `{reason}` | {cnt} | {pct:.1f} % | {desc} |")

    lines.extend([
        "",
        "## 3. Répartition des modes construits",
        "| Mode | Constructions | Part |",
        "|---|---:|---:|",
    ])

    for mode, cnt in summary["by_mode"].items():
        pct = (cnt / n * 100) if n > 0 else 0.0
        lines.append(f"| `{mode}` | {cnt} | {pct:.1f} % |")

    ds = summary["days_stats"]
    ts = summary["ticks_stats"]
    lines.extend([
        "",
        "## 4. Latence de réapparition d'un portefeuille non vide",
        f"*(Mesurée sur les {summary['emptied_count']} constructions ayant vidé le vivier)*",
        "",
        "| Métrique | n | Min | Médiane | Moyenne | p90 | Max |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Jours calendaires | {ds['n']} | {ds['min']} | **{ds['med']} j** | {ds['moy']} j | {ds['p90']} j | {ds['max']} j |",
        f"| Ticks moteur | {ts['n']} | {ts['min']} | **{ts['med']} tk** | {ts['moy']} tk | {ts['p90']} tk | {ts['max']} tk |",
    ])

    def_s = summary["deficit_stats"]
    if def_s["n"] > 0:
        lines.extend([
            "",
            "## 5. Analyse financière post-build (cas `all_unaffordable`)",
            "| Grandeur | n | Min (£) | Médiane (£) | Moyenne (£) | p90 (£) | Max (£) |",
            "|---|---:|---:|---:|---:|---:|---:|",
            f"| Capital restant post-build | {summary['cap_after_stats']['n']} | {summary['cap_after_stats']['min']:,} | {summary['cap_after_stats']['med']:,} | {summary['cap_after_stats']['moy']:,} | {summary['cap_after_stats']['p90']:,} | {summary['cap_after_stats']['max']:,} |",
            f"| Capital du prochain projet (`next_k`) | {summary['next_k_stats']['n']} | {summary['next_k_stats']['min']:,} | {summary['next_k_stats']['med']:,} | {summary['next_k_stats']['moy']:,} | {summary['next_k_stats']['p90']:,} | {summary['next_k_stats']['max']:,} |",
            f"| Déficit de financement (`next_k - cap_after`) | {def_s['n']} | {def_s['min']:,} | **{def_s['med']:,} £** | {def_s['moy']:,} £ | {def_s['p90']:,} £ | {def_s['max']:,} £ |",
        ])

    lines.extend([
        "",
        "## 6. Matrice croisée `emptyCause` × `ret_reason`",
        "| Cause \\ Déclencheur | " + " | ".join(f"`{r}`" for r in summary["by_reason"].keys()) + " | **Total** |",
        "|---|" + "|".join("---:" for _ in summary["by_reason"].keys()) + "|---:|",
    ])

    for cause in summary["by_cause"].keys():
        row_counts = [summary["cross_cause_reason"].get(cause, {}).get(r, 0) for r in summary["by_reason"].keys()]
        tot_cause = sum(row_counts)
        cells = " | ".join(str(c) if c > 0 else "—" for c in row_counts)
        lines.append(f"| `{cause}` | {cells} | **{tot_cause}** |")

    lines.extend([
        "",
        "## 7. Vérification des recoupements et intégrité",
        f"- Somme par mode : {sum(summary['by_mode'].values())} == Total : {n} ✓",
        f"- Somme par cause : {sum(summary['by_cause'].values())} == Total : {n} ✓",
        f"- Somme par raison : {sum(summary['by_reason'].values())} == Total : {n} ✓",
        f"- Répartition par graine : " + ", ".join(f"graine {s} : {c}" for s, c in summary["by_seed_counts"].items()),
    ])

    if summary.get("perturbation"):
        lines.extend([
            "",
            "## 8. Perturbation sous sonde (probe_scheduler=1 vs référence probe_scheduler=0)",
            "| Graine | Valeur ref | Valeur sonde | Delta val (%) | Profit ref | Profit sonde | Delta prof (%) | Véh ref | Véh sonde (delta) | Gares ref | Gares sonde (delta) |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for p in summary["perturbation"]:
            lines.append(
                f"| {p['seed']} | {p['base_val']:,} | {p['var_val']:,} | {p['val_delta']:+,} ({p['val_pct']:+.1f}%) | "
                f"{p['base_prof']:,} | {p['var_prof']:,} | {p['prof_delta']:+,} ({p['prof_pct']:+.1f}%) | "
                f"{p['base_veh']} | {p['var_veh']} ({p['veh_delta']:+d}) | "
                f"{p['base_st']} | {p['var_st']} ({p['st_delta']:+d}) |"
            )

    lines.append("")
    return "\n".join(lines)
