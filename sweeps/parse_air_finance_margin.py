#!/usr/bin/env python3
"""Analyse télémétrique des marges de financement aériennes (AIR_FINANCE).

Ce module extrait et synthétise les événements de financement aérien à partir
des journaux moteur OpenTTD (AILog / script debug) :
- AIR_FINANCE_TRY : tentatives d'élection/construction, marges, réserves, issues.
- AIR_FINANCE_FIRST_REVENUE : délai de premier revenu, trésorerie minimale vs réserve.
- AIR_FINANCE_PENDING : lignes en cours de démarrage à l'horizon d'évaluation.

Produit un rapport tabulaire sur stdout et/ou un export JSON structuré (--json PATH).
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import re
import statistics
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# Regex pour repérer les lignes contenant un jeton AIR_FINANCE
RE_TOKEN = re.compile(
    r"\b(AIR_FINANCE_(?:TRY|FIRST_REVENUE|PENDING)[A-Za-z0-9_]*)\b\s*(.*)$"
)

# Regex pour parser les paires clé=valeur (supporte valeurs simples ou entre guillemets)
RE_KV = re.compile(r'([A-Za-z0-9_]+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))')

# Regex pour supprimer les codes d'échappement ANSI
RE_ANSI = re.compile(r"\x1b\[[0-9;]*[mGKH]")


def clean_log_line(line: str) -> str:
    """Nettoie une ligne de journal brut (retire retours chariot et codes ANSI)."""
    return RE_ANSI.sub("", line).strip()


def parse_kv_payload(payload: str) -> Dict[str, str]:
    """Parse une charge utile en paires clé=valeur."""
    kv: Dict[str, str] = {}
    for match in RE_KV.finditer(payload):
        k = match.group(1)
        v = (
            match.group(2)
            if match.group(2) is not None
            else (match.group(3) if match.group(3) is not None else match.group(4))
        )
        kv[k] = v or ""
    return kv


def to_int(val: Any) -> Optional[int]:
    """Convertit en entier avec tolérance pour flottants."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None


def to_float(val: Any) -> Optional[float]:
    """Convertit en flottant."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_log_filename(filename: str | Path) -> Dict[str, Any]:
    """Extrait arm, seed et repeat depuis le nom de fichier de log."""
    path = Path(filename)
    stem = path.stem
    name = path.name

    # Pattern standard : <arm>_seed<N>_r<R> ou <arm>_seed<N> ou seed<N>_r<R>
    m = re.match(r"^(?:(?P<arm>.+?)_)?seed(?P<seed>\d+)(?:_r(?P<repeat>\d+))?.*$", stem)
    if m:
        arm = m.group("arm") or ""
        seed = int(m.group("seed"))
        repeat = int(m.group("repeat")) if m.group("repeat") is not None else 0
        return {"arm": arm, "seed": seed, "repeat": repeat, "filename": name}

    # Recherche plus large de seed\d+
    m_seed = re.search(r"seed[_-]?(\d+)", stem, re.IGNORECASE)
    if m_seed:
        seed = int(m_seed.group(1))
        prefix = stem[: m_seed.start()].rstrip("_-")
        m_r = re.search(r"_r(\d+)", stem[m_seed.end() :])
        repeat = int(m_r.group(1)) if m_r else 0
        return {"arm": prefix, "seed": seed, "repeat": repeat, "filename": name}

    return {"arm": "", "seed": 0, "repeat": 0, "filename": name}


@dataclass
class TryRecord:
    seed: int
    arm: str
    path: Optional[str]
    rank: Optional[int]
    src_town: Optional[str]
    dst_town: Optional[str]
    new_airports: Optional[int]
    margin: Optional[float]
    reserve: Optional[float]
    capital: Optional[float]
    need: Optional[float]
    cash: Optional[float]
    outcome: str
    planned: Optional[float] = None
    actual: Optional[float] = None
    reason: Optional[str] = None
    line: Optional[int] = None
    date: Optional[str] = None
    raw_kv: Dict[str, str] = field(default_factory=dict)


@dataclass
class FirstRevenueRecord:
    seed: int
    arm: str
    line: Optional[int]
    build_date: Optional[str]
    first_date: Optional[str]
    days: Optional[float]
    cash_min: Optional[float]
    reserve: Optional[float] = None
    new_airports: Optional[int] = None
    raw_kv: Dict[str, str] = field(default_factory=dict)


@dataclass
class PendingRecord:
    seed: int
    arm: str
    line: Optional[int]
    build_date: Optional[str]
    days: Optional[float]
    new_airports: Optional[int] = None
    raw_kv: Dict[str, str] = field(default_factory=dict)


@dataclass
class LogRunData:
    seed: int
    arm: str
    filename: str
    tries: List[TryRecord] = field(default_factory=list)
    first_revenues: List[FirstRevenueRecord] = field(default_factory=list)
    pendings: List[PendingRecord] = field(default_factory=list)


def parse_try_line(kv: Dict[str, str], seed: int, arm: str) -> TryRecord:
    """Construit un TryRecord à partir des paires clé=valeur d'un TRY."""
    planned = to_float(kv.get("planned"))
    actual = to_float(kv.get("actual"))
    # Normalisation des coûts de construction négatifs si applicable
    if planned is not None and planned < 0 and actual is not None and actual < 0:
        planned = abs(planned)
        actual = abs(actual)
    elif planned is not None and planned < 0:
        planned = abs(planned)

    return TryRecord(
        seed=seed,
        arm=arm,
        path=kv.get("path"),
        rank=to_int(kv.get("rank")),
        src_town=kv.get("src_town"),
        dst_town=kv.get("dst_town"),
        new_airports=to_int(kv.get("new_airports")),
        margin=to_float(kv.get("margin")),
        reserve=to_float(kv.get("reserve")),
        capital=to_float(kv.get("capital")),
        need=to_float(kv.get("need")),
        cash=to_float(kv.get("cash")),
        outcome=kv.get("outcome", "").strip().lower(),
        planned=planned,
        actual=actual,
        reason=kv.get("reason", "").strip() or None,
        line=to_int(kv.get("line")),
        date=kv.get("date", "").strip() or None,
        raw_kv=kv,
    )


def parse_first_revenue_line(
    kv: Dict[str, str], seed: int, arm: str
) -> FirstRevenueRecord:
    """Construit un FirstRevenueRecord à partir des paires clé=valeur."""
    return FirstRevenueRecord(
        seed=seed,
        arm=arm,
        line=to_int(kv.get("line")),
        build_date=kv.get("build_date", "").strip() or None,
        first_date=kv.get("first_date", "").strip() or None,
        days=to_float(kv.get("days")),
        cash_min=to_float(kv.get("cash_min")),
        reserve=to_float(kv.get("reserve")),
        new_airports=to_int(kv.get("new_airports")),
        raw_kv=kv,
    )


def parse_pending_line(kv: Dict[str, str], seed: int, arm: str) -> PendingRecord:
    """Construit un PendingRecord à partir des paires clé=valeur."""
    return PendingRecord(
        seed=seed,
        arm=arm,
        line=to_int(kv.get("line")),
        build_date=kv.get("build_date", "").strip() or None,
        days=to_float(kv.get("days")),
        new_airports=to_int(kv.get("new_airports")),
        raw_kv=kv,
    )


def link_records_in_run(run: LogRunData) -> None:
    """Joint les lignes built avec FIRST_REVENUE et PENDING pour compléter reserve et new_airports."""
    built_map: Dict[int, TryRecord] = {}
    for t in run.tries:
        if t.outcome == "built" and t.line is not None:
            built_map[t.line] = t

    for fr in run.first_revenues:
        if fr.line is not None and fr.line in built_map:
            built = built_map[fr.line]
            if fr.reserve is None:
                fr.reserve = built.reserve
            if fr.new_airports is None:
                fr.new_airports = built.new_airports

    for p in run.pendings:
        if p.line is not None and p.line in built_map:
            built = built_map[p.line]
            if p.new_airports is None:
                p.new_airports = built.new_airports


def parse_log_stream(
    lines: Iterable[str], seed: int = 0, arm: str = "", filename: str = "stream"
) -> LogRunData:
    """Parse un flux de lignes de journal pour une partie donnée."""
    run = LogRunData(seed=seed, arm=arm, filename=filename)

    for raw_line in lines:
        line = clean_log_line(raw_line)
        if not line:
            continue
        m = RE_TOKEN.search(line)
        if not m:
            continue

        token = m.group(1)
        payload = m.group(2)
        kv = parse_kv_payload(payload)

        if token.startswith("AIR_FINANCE_TRY"):
            run.tries.append(parse_try_line(kv, seed=seed, arm=arm))
        elif token.startswith("AIR_FINANCE_FIRST_REVENUE"):
            run.first_revenues.append(
                parse_first_revenue_line(kv, seed=seed, arm=arm)
            )
        elif token.startswith("AIR_FINANCE_PENDING"):
            run.pendings.append(parse_pending_line(kv, seed=seed, arm=arm))

    link_records_in_run(run)
    return run


def parse_log_file(file_path: Path) -> LogRunData:
    """Lit et parse un fichier de journal .log."""
    meta = parse_log_filename(file_path)
    with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
        return parse_log_stream(
            fh, seed=meta["seed"], arm=meta["arm"], filename=meta["filename"]
        )


# ==============================================================================
# Fonctions statistiques
# ==============================================================================


def calc_percentile(values: Sequence[float], p: float) -> Optional[float]:
    """Calcule le centile p (entre 0.0 et 1.0) par interpolation linéaire."""
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    if n == 1:
        return float(s[0])
    idx = (n - 1) * p
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return float(s[lo])
    weight = idx - lo
    return float(s[lo] * (1.0 - weight) + s[hi] * weight)


def calc_median(values: Sequence[float]) -> Optional[float]:
    """Médiane avec tolérance liste vide."""
    if not values:
        return None
    return float(statistics.median(values))


def calc_p90(values: Sequence[float]) -> Optional[float]:
    """90e centile."""
    return calc_percentile(values, 0.90)


def calc_mean(values: Sequence[float]) -> Optional[float]:
    """Moyenne avec tolérance liste vide."""
    if not values:
        return None
    return float(statistics.mean(values))


def summarize_distribution(values: Sequence[float]) -> Dict[str, Any]:
    """Résumé complet d'une distribution de valeurs réelles."""
    if not values:
        return {
            "count": 0,
            "min": None,
            "p10": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p90": None,
            "max": None,
            "mean": None,
            "sum": 0.0,
        }
    return {
        "count": len(values),
        "min": float(min(values)),
        "p10": calc_percentile(values, 0.10),
        "p25": calc_percentile(values, 0.25),
        "median": calc_median(values),
        "p75": calc_percentile(values, 0.75),
        "p90": calc_p90(values),
        "max": float(max(values)),
        "mean": calc_mean(values),
        "sum": float(sum(values)),
    }


# ==============================================================================
# Agrégation des métriques de groupe (par new_airports ou overall)
# ==============================================================================


def compute_group_metrics(
    try_records: Sequence[TryRecord],
    first_rev_records: Sequence[FirstRevenueRecord],
    pending_records: Sequence[PendingRecord],
) -> Dict[str, Any]:
    """Calcule l'ensemble des métriques requises pour un sous-groupe ou le total."""
    attempts = len(try_records)
    outcomes = Counter(r.outcome for r in try_records if r.outcome)

    refused_margin_count = outcomes.get("refused_margin", 0)
    refused_capital_count = outcomes.get("refused_capital", 0)
    built_count = outcomes.get("built", 0)
    failed_count = outcomes.get("failed", 0)
    total_refused = refused_margin_count + refused_capital_count

    by_outcome: Dict[str, Dict[str, Any]] = {
        "built": {
            "count": built_count,
            "share": built_count / attempts if attempts else 0.0,
        },
        "failed": {
            "count": failed_count,
            "share": failed_count / attempts if attempts else 0.0,
        },
        "refused_margin": {
            "count": refused_margin_count,
            "share": refused_margin_count / attempts if attempts else 0.0,
        },
        "refused_capital": {
            "count": refused_capital_count,
            "share": refused_capital_count / attempts if attempts else 0.0,
        },
    }
    for k, cnt in outcomes.items():
        if k not in by_outcome:
            by_outcome[k] = {
                "count": cnt,
                "share": cnt / attempts if attempts else 0.0,
            }

    # 1. Refused Margin
    shortfalls = [
        (r.need - r.cash)
        for r in try_records
        if r.outcome == "refused_margin"
        and r.need is not None
        and r.cash is not None
    ]
    # Vérification que la marge était la contrainte liante : cash >= capital+reserve et cash < need
    binding_verified = [
        r
        for r in try_records
        if r.outcome == "refused_margin"
        and r.cash is not None
        and r.capital is not None
        and r.reserve is not None
        and r.need is not None
        and r.cash >= (r.capital + r.reserve)
        and r.cash < r.need
    ]

    refused_margin_stats = {
        "count": refused_margin_count,
        "share_of_attempts": (
            refused_margin_count / attempts if attempts else 0.0
        ),
        "share_of_refused": (
            refused_margin_count / total_refused if total_refused else 0.0
        ),
        "binding_verified_count": len(binding_verified),
        "shortfall_median": calc_median(shortfalls),
        "shortfall_p90": calc_p90(shortfalls),
        "shortfall_mean": calc_mean(shortfalls),
        "shortfall_min": min(shortfalls) if shortfalls else None,
        "shortfall_max": max(shortfalls) if shortfalls else None,
    }

    # 2. Built + Failed : ratio actual/planned et dépassement (overrun) vs marge
    built_failed = [r for r in try_records if r.outcome in ("built", "failed")]
    ratios = [
        r.actual / r.planned
        for r in built_failed
        if r.planned is not None and r.planned > 0 and r.actual is not None
    ]
    with_both_planned_actual = [
        r
        for r in built_failed
        if r.planned is not None and r.actual is not None
    ]
    actual_gt_planned = [
        r for r in with_both_planned_actual if r.actual > r.planned
    ]
    share_actual_gt_planned = (
        len(actual_gt_planned) / len(with_both_planned_actual)
        if with_both_planned_actual
        else 0.0
    )

    overruns_gbp = [
        (r.actual - r.planned) for r in with_both_planned_actual
    ]
    with_margin = [
        r
        for r in with_both_planned_actual
        if r.margin is not None
    ]
    overrun_gt_margin = [
        r
        for r in with_margin
        if (r.actual - r.planned) > r.margin
    ]
    overrun_gt_margin_share = (
        len(overrun_gt_margin) / len(with_margin) if with_margin else 0.0
    )

    built_failed_stats = {
        "count": len(built_failed),
        "with_planned_actual_count": len(with_both_planned_actual),
        "ratio_median": calc_median(ratios),
        "ratio_p90": calc_p90(ratios),
        "ratio_max": max(ratios) if ratios else None,
        "share_actual_gt_planned": share_actual_gt_planned,
        "count_actual_gt_planned": len(actual_gt_planned),
        "overrun_gt_margin_count": len(overrun_gt_margin),
        "overrun_gt_margin_share": overrun_gt_margin_share,
        "overrun_gbp_median": calc_median(overruns_gbp),
        "overrun_gbp_p90": calc_p90(overruns_gbp),
        "overrun_gbp_max": max(overruns_gbp) if overruns_gbp else None,
        "overrun_gbp_sum": sum(overruns_gbp) if overruns_gbp else 0.0,
    }

    # 3. Failed : coût échoué (sunk cost) par raison
    failed_records = [r for r in try_records if r.outcome == "failed"]
    reasons_map: Dict[str, List[float]] = defaultdict(list)
    for r in failed_records:
        reason = r.reason or "unspecified"
        cost = r.actual if r.actual is not None else 0.0
        reasons_map[reason].append(cost)

    failed_by_reason: Dict[str, Dict[str, Any]] = {}
    for reason, costs in sorted(reasons_map.items()):
        failed_by_reason[reason] = {
            "count": len(costs),
            "sunk_cost_sum": sum(costs),
            "sunk_cost_median": calc_median(costs),
            "sunk_cost_max": max(costs) if costs else None,
        }

    all_failed_costs = [
        (r.actual if r.actual is not None else 0.0) for r in failed_records
    ]
    failed_stats = {
        "count": len(failed_records),
        "sunk_cost_sum": sum(all_failed_costs) if all_failed_costs else 0.0,
        "sunk_cost_median": calc_median(all_failed_costs),
        "by_reason": failed_by_reason,
    }

    # 4. First Revenue : jours et trésorerie minimale - réserve
    days_list = [r.days for r in first_rev_records if r.days is not None]
    diffs: List[float] = []
    breached: List[float] = []
    for r in first_rev_records:
        if r.cash_min is not None and r.reserve is not None:
            diff = r.cash_min - r.reserve
            diffs.append(diff)
            if diff < 0:
                breached.append(diff)

    diff_summary = summarize_distribution(diffs)
    diff_summary["breached_count"] = len(breached)
    diff_summary["breached_share"] = (
        len(breached) / len(diffs) if diffs else 0.0
    )

    first_revenue_stats = {
        "count": len(first_rev_records),
        "days_median": calc_median(days_list),
        "days_p90": calc_p90(days_list),
        "days_min": min(days_list) if days_list else None,
        "days_max": max(days_list) if days_list else None,
        "cash_min_minus_reserve": diff_summary,
    }

    # 5. Pending count
    pending_stats = {
        "count": len(pending_records),
        "unique_lines": len(
            set(r.line for r in pending_records if r.line is not None)
        ),
        "days_median": calc_median(
            [r.days for r in pending_records if r.days is not None]
        ),
    }

    return {
        "attempts": attempts,
        "outcomes": by_outcome,
        "refused_margin": refused_margin_stats,
        "built_failed": built_failed_stats,
        "failed": failed_stats,
        "first_revenue": first_revenue_stats,
        "pending": pending_stats,
    }


def aggregate_runs(runs: List[LogRunData]) -> Dict[str, Any]:
    """Agrège l'ensemble des parties par new_airports, au global et par graine."""
    all_tries: List[TryRecord] = []
    all_first_rev: List[FirstRevenueRecord] = []
    all_pending: List[PendingRecord] = []

    tries_by_airport: Dict[int, List[TryRecord]] = defaultdict(list)
    first_rev_by_airport: Dict[int, List[FirstRevenueRecord]] = defaultdict(list)
    pending_by_airport: Dict[int, List[PendingRecord]] = defaultdict(list)

    runs_by_seed: Dict[int, List[LogRunData]] = defaultdict(list)

    for run in runs:
        runs_by_seed[run.seed].append(run)
        for t in run.tries:
            all_tries.append(t)
            if t.new_airports is not None:
                tries_by_airport[t.new_airports].append(t)

        for fr in run.first_revenues:
            all_first_rev.append(fr)
            if fr.new_airports is not None:
                first_rev_by_airport[fr.new_airports].append(fr)

        for p in run.pendings:
            all_pending.append(p)
            if p.new_airports is not None:
                pending_by_airport[p.new_airports].append(p)

    # 1. Global (overall)
    overall_metrics = compute_group_metrics(
        all_tries, all_first_rev, all_pending
    )

    # 2. Par new_airports (0, 1, 2)
    by_new_airports: Dict[str, Dict[str, Any]] = {}
    for n in (0, 1, 2):
        by_new_airports[str(n)] = compute_group_metrics(
            tries_by_airport[n],
            first_rev_by_airport[n],
            pending_by_airport[n],
        )

    # 3. Ventilation par graine
    by_seed: Dict[str, Dict[str, Any]] = {}
    for seed, seed_runs in sorted(runs_by_seed.items()):
        seed_tries: List[TryRecord] = []
        seed_first_rev: List[FirstRevenueRecord] = []
        seed_pending: List[PendingRecord] = []
        arms = {r.arm for r in seed_runs if r.arm}
        arm_str = ",".join(sorted(arms)) if arms else ""

        for r in seed_runs:
            seed_tries.extend(r.tries)
            seed_first_rev.extend(r.first_revenues)
            seed_pending.extend(r.pendings)

        metrics = compute_group_metrics(
            seed_tries, seed_first_rev, seed_pending
        )
        metrics["seed"] = seed
        metrics["arm"] = arm_str
        metrics["runs_count"] = len(seed_runs)
        by_seed[str(seed)] = metrics

    return {
        "metadata": {
            "files_count": len(runs),
            "seeds_count": len(runs_by_seed),
        },
        "overall": overall_metrics,
        "by_new_airports": by_new_airports,
        "by_seed": by_seed,
    }


# ==============================================================================
# Formatage et rendu du rapport tabulaire
# ==============================================================================


def _fmt_gbp(val: Optional[float | int]) -> str:
    if val is None:
        return "-"
    sign = "-" if val < 0 else ""
    return f"{sign}£{abs(val):,.0f}"


def _fmt_pct(val: Optional[float]) -> str:
    if val is None:
        return "-"
    return f"{val * 100:.1f}%"


def _fmt_ratio(val: Optional[float]) -> str:
    if val is None:
        return "-"
    return f"{val:.3f}"


def _fmt_num(val: Optional[float | int], dec: int = 1) -> str:
    if val is None:
        return "-"
    if isinstance(val, int) or val == int(val):
        return str(int(val))
    return f"{val:.{dec}f}"


def render_report_table(report: Dict[str, Any]) -> str:
    """Génère un tableau texte complet pour affichage sur stdout."""
    lines: List[str] = []
    meta = report.get("metadata", {})
    overall = report.get("overall", {})
    by_airports = report.get("by_new_airports", {})
    by_seed = report.get("by_seed", {})

    lines.append("=" * 95)
    lines.append("AIR FINANCE MARGIN & EXECUTION REPORT")
    lines.append(
        f"Fichiers analysés : {meta.get('files_count', 0)} | "
        f"Graines uniques : {meta.get('seeds_count', 0)}"
    )
    lines.append("=" * 95)
    lines.append("")

    # --- TABLEAU COMPARATIF : OVERALL vs NEW_AIRPORTS (0, 1, 2) ---
    col_w = [34, 14, 14, 14, 14]
    header = (
        f"{'Métrique':<{col_w[0]}} "
        f"{'Overall':>{col_w[1]}} "
        f"{'0 aéroports':>{col_w[2]}} "
        f"{'1 aéroport':>{col_w[3]}} "
        f"{'2 aéroports':>{col_w[4]}}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    def get_group(col_idx: int) -> Dict[str, Any]:
        if col_idx == 1:
            return overall
        return by_airports.get(str(col_idx - 2), {})

    def row(label: str, fn) -> str:
        vals = [label]
        for col_idx in range(1, 5):
            g = get_group(col_idx)
            vals.append(fn(g))
        return (
            f"{vals[0]:<{col_w[0]}} "
            f"{vals[1]:>{col_w[1]}} "
            f"{vals[2]:>{col_w[2]}} "
            f"{vals[3]:>{col_w[3]}} "
            f"{vals[4]:>{col_w[4]}}"
        )

    # Attempts & Outcomes
    lines.append(row("Tentatives (attempts)", lambda g: str(g.get("attempts", 0))))
    lines.append(
        row(
            "  - built",
            lambda g: f"{g.get('outcomes', {}).get('built', {}).get('count', 0)} ({_fmt_pct(g.get('outcomes', {}).get('built', {}).get('share'))})",
        )
    )
    lines.append(
        row(
            "  - failed",
            lambda g: f"{g.get('outcomes', {}).get('failed', {}).get('count', 0)} ({_fmt_pct(g.get('outcomes', {}).get('failed', {}).get('share'))})",
        )
    )
    lines.append(
        row(
            "  - refused_margin",
            lambda g: f"{g.get('outcomes', {}).get('refused_margin', {}).get('count', 0)} ({_fmt_pct(g.get('outcomes', {}).get('refused_margin', {}).get('share'))})",
        )
    )
    lines.append(
        row(
            "  - refused_capital",
            lambda g: f"{g.get('outcomes', {}).get('refused_capital', {}).get('count', 0)} ({_fmt_pct(g.get('outcomes', {}).get('refused_capital', {}).get('share'))})",
        )
    )

    # Refused Margin
    lines.append(
        row(
            "Part refused_margin (/attempts)",
            lambda g: _fmt_pct(g.get("refused_margin", {}).get("share_of_attempts")),
        )
    )
    lines.append(
        row(
            "Part refused_margin (/refusés)",
            lambda g: _fmt_pct(g.get("refused_margin", {}).get("share_of_refused")),
        )
    )
    lines.append(
        row(
            "Déficit médian (need - cash)",
            lambda g: _fmt_gbp(g.get("refused_margin", {}).get("shortfall_median")),
        )
    )
    lines.append(
        row(
            "Déficit p90 (need - cash)",
            lambda g: _fmt_gbp(g.get("refused_margin", {}).get("shortfall_p90")),
        )
    )

    # Built + Failed
    lines.append(
        row(
            "Ratio réel/prévu (médiane)",
            lambda g: _fmt_ratio(g.get("built_failed", {}).get("ratio_median")),
        )
    )
    lines.append(
        row(
            "Ratio réel/prévu (p90)",
            lambda g: _fmt_ratio(g.get("built_failed", {}).get("ratio_p90")),
        )
    )
    lines.append(
        row(
            "Ratio réel/prévu (max)",
            lambda g: _fmt_ratio(g.get("built_failed", {}).get("ratio_max")),
        )
    )
    lines.append(
        row(
            "Part réel > prévu",
            lambda g: _fmt_pct(
                g.get("built_failed", {}).get("share_actual_gt_planned")
            ),
        )
    )
    lines.append(
        row(
            "Part dépassement > marge",
            lambda g: f"{g.get('built_failed', {}).get('overrun_gt_margin_count', 0)} ({_fmt_pct(g.get('built_failed', {}).get('overrun_gt_margin_share'))})",
        )
    )
    lines.append(
        row(
            "Dépassement GBP (médiane)",
            lambda g: _fmt_gbp(g.get("built_failed", {}).get("overrun_gbp_median")),
        )
    )

    # Failed
    lines.append(
        row(
            "Coût échoué total (sunk sum)",
            lambda g: _fmt_gbp(g.get("failed", {}).get("sunk_cost_sum")),
        )
    )
    lines.append(
        row(
            "Coût échoué médian (sunk med)",
            lambda g: _fmt_gbp(g.get("failed", {}).get("sunk_cost_median")),
        )
    )

    # First Revenue
    lines.append(
        row(
            "1er revenu : jours (médiane)",
            lambda g: _fmt_num(g.get("first_revenue", {}).get("days_median")),
        )
    )
    lines.append(
        row(
            "1er revenu : jours (p90)",
            lambda g: _fmt_num(g.get("first_revenue", {}).get("days_p90")),
        )
    )
    lines.append(
        row(
            "Trésorerie < réserve (brèche)",
            lambda g: f"{g.get('first_revenue', {}).get('cash_min_minus_reserve', {}).get('breached_count', 0)} ({_fmt_pct(g.get('first_revenue', {}).get('cash_min_minus_reserve', {}).get('breached_share'))})",
        )
    )
    lines.append(
        row(
            "Diff trésorerie - réserve (méd)",
            lambda g: _fmt_gbp(
                g.get("first_revenue", {})
                .get("cash_min_minus_reserve", {})
                .get("median")
            ),
        )
    )

    # Pending
    lines.append(
        row(
            "Lignes en attente (pending)",
            lambda g: str(g.get("pending", {}).get("count", 0)),
        )
    )
    lines.append("-" * len(header))
    lines.append("")

    # --- DÉTAIL DES ÉCHECS PAR RAISON ---
    failed_overall = overall.get("failed", {})
    by_reason = failed_overall.get("by_reason", {})
    if by_reason:
        lines.append("DÉTAIL DES ÉCHECS PAR RAISON (Global) :")
        lines.append(
            f"  {'Raison':<30} {'Nb':>5} {'Coût Total':>14} {'Coût Médian':>14} {'Coût Max':>14}"
        )
        lines.append(f"  {'-'*30} {'-'*5} {'-'*14} {'-'*14} {'-'*14}")
        for reason, rdata in sorted(
            by_reason.items(),
            key=lambda x: x[1].get("sunk_cost_sum", 0),
            reverse=True,
        ):
            lines.append(
                f"  {reason:<30} {rdata.get('count', 0):>5} "
                f"{_fmt_gbp(rdata.get('sunk_cost_sum')):>14} "
                f"{_fmt_gbp(rdata.get('sunk_cost_median')):>14} "
                f"{_fmt_gbp(rdata.get('sunk_cost_max')):>14}"
            )
        lines.append("")

    # --- VENTILATION PAR GRAINE (PER-SEED BREAKDOWN) ---
    if by_seed:
        lines.append("VENTILATION PAR GRAINE (PER-SEED BREAKDOWN) :")
        s_hdr = (
            f"  {'Graine':>6} {'Bras':<12} {'Att':>4} {'Blt':>4} {'Fail':>4} "
            f"{'RefM':>5} {'RefC':>5} {'Ovr>M':>6} {'SunkSum':>11} "
            f"{'1stRev':>6} {'JoursMed':>8} {'Brèche':>7} {'Pend':>5}"
        )
        lines.append(s_hdr)
        lines.append(f"  {'-'*len(s_hdr.strip())}")

        for seed_str, sdata in by_seed.items():
            seed_val = sdata.get("seed", seed_str)
            arm_val = sdata.get("arm", "")[:12]
            att = sdata.get("attempts", 0)
            blt = sdata.get("outcomes", {}).get("built", {}).get("count", 0)
            fail = sdata.get("outcomes", {}).get("failed", {}).get("count", 0)
            ref_m = (
                sdata.get("outcomes", {})
                .get("refused_margin", {})
                .get("count", 0)
            )
            ref_c = (
                sdata.get("outcomes", {})
                .get("refused_capital", {})
                .get("count", 0)
            )
            ovr_m = (
                sdata.get("built_failed", {}).get("overrun_gt_margin_count", 0)
            )
            sunk = sdata.get("failed", {}).get("sunk_cost_sum", 0)
            frev = sdata.get("first_revenue", {}).get("count", 0)
            days = sdata.get("first_revenue", {}).get("days_median")
            brch = (
                sdata.get("first_revenue", {})
                .get("cash_min_minus_reserve", {})
                .get("breached_count", 0)
            )
            pend = sdata.get("pending", {}).get("count", 0)

            lines.append(
                f"  {seed_val:>6} {arm_val:<12} {att:>4} {blt:>4} {fail:>4} "
                f"{ref_m:>5} {ref_c:>5} {ovr_m:>6} {_fmt_gbp(sunk):>11} "
                f"{frev:>6} {_fmt_num(days, 0):>8} {brch:>7} {pend:>5}"
            )
        lines.append("")

    return "\n".join(lines)


# ==============================================================================
# Fixtures internes et Selftest
# ==============================================================================

FIXTURE_SEED42 = """
[2026-10-06 00:01:00] dbg: [script:4] [0] [I] AIR_FINANCE_TRY date=1971-03-01 path=0 rank=0 src_town=1 dst_town=2 new_airports=0 margin=10000 reserve=15000 capital=25000 need=50000 cash=55000 outcome=built planned=25000 actual=26000 reason=ok line=1
[2026-10-06 00:02:00] dbg: [script:4] [0] [I] AIR_FINANCE_TRY date=1971-06-01 path=1 rank=0 src_town=3 dst_town=4 new_airports=1 margin=12000 reserve=15000 capital=35000 need=62000 cash=58000 outcome=refused_margin
[2026-10-06 00:03:00] dbg: [script:4] [0] [I] AIR_FINANCE_TRY date=1971-09-01 path=2 rank=0 src_town=5 dst_town=6 new_airports=2 margin=15000 reserve=15000 capital=45000 need=75000 cash=40000 outcome=refused_capital
[2026-10-06 00:04:00] dbg: [script:4] [0] [I] AIR_FINANCE_TRY date=1972-01-15 path=3 rank=1 src_town=7 dst_town=8 new_airports=2 margin=15000 reserve=15000 capital=50000 need=80000 cash=85000 outcome=failed planned=50000 actual=10000 reason=ERR_FLAT_LAND line=2
[2026-10-06 00:05:00] dbg: [script:4] [0] [I] AIR_FINANCE_TRY date=1972-04-10 path=4 rank=0 src_town=9 dst_town=10 new_airports=2 margin=15000 reserve=15000 capital=40000 need=70000 cash=75000 outcome=built planned=40000 actual=60000 reason=ok line=3 unknown_tag=xyz
[2026-10-06 00:06:00] dbg: [script:4] [0] [I] AIR_FINANCE_FIRST_REVENUE line=1 build_date=1971-03-01 first_date=1971-06-20 days=111 cash_min=18000
[2026-10-06 00:07:00] dbg: [script:4] [0] [I] AIR_FINANCE_FIRST_REVENUE line=3 build_date=1972-04-10 first_date=1972-09-15 days=158 cash_min=12000
[2026-10-06 00:08:00] dbg: [script:4] [0] [I] AIR_FINANCE_PENDING line=4 build_date=1972-11-01 days=60
"""

FIXTURE_SEED100 = """
AILog: AIR_FINANCE_TRY date=1971-02-15 path=0 rank=0 src_town=11 dst_town=12 new_airports=1 margin=10000 reserve=12000 capital=30000 need=52000 cash=48000 outcome=refused_margin
AIR_FINANCE_TRY date=1971-05-10 path=1 rank=0 src_town=13 dst_town=14 new_airports=1 margin=10000 reserve=12000 capital=28000 need=50000 cash=55000 outcome=built planned=28000 actual=28000 reason=ok line=10
AIR_FINANCE_TRY date=1971-08-01 path=2 rank=1 src_town=15 dst_town=16 new_airports=1 margin=10000 reserve=12000 capital=32000 need=54000 cash=60000 outcome=failed planned=32000 actual=5000 reason=ERR_LOCAL_AUTHORITY line=11
AIR_FINANCE_FIRST_REVENUE line=10 build_date=1971-05-10 first_date=1971-08-18 days=100 cash_min=14000
"""


def run_selftest() -> bool:
    """Exécute les assertions d'auto-test sur les fixtures intégrées."""
    run42 = parse_log_stream(
        FIXTURE_SEED42.strip().splitlines(),
        seed=42,
        arm="p6_shadow",
        filename="p6_shadow_seed42_r0.log",
    )
    run100 = parse_log_stream(
        FIXTURE_SEED100.strip().splitlines(),
        seed=100,
        arm="p6_shadow",
        filename="p6_shadow_seed100_r0.log",
    )

    report = aggregate_runs([run42, run100])
    overall = report["overall"]

    # Invariants globaux
    assert overall["attempts"] == 8, f"Expected 8 attempts, got {overall['attempts']}"
    assert overall["outcomes"]["built"]["count"] == 3
    assert overall["outcomes"]["failed"]["count"] == 2
    assert overall["outcomes"]["refused_margin"]["count"] == 2
    assert overall["outcomes"]["refused_capital"]["count"] == 1

    # Refused margin
    ref_m = overall["refused_margin"]
    assert ref_m["count"] == 2
    assert abs(ref_m["share_of_attempts"] - (2 / 8)) < 1e-6
    assert abs(ref_m["share_of_refused"] - (2 / 3)) < 1e-6
    # Shortfall: 62000 - 58000 = 4000; 52000 - 48000 = 4000
    assert ref_m["shortfall_median"] == 4000.0
    assert ref_m["binding_verified_count"] == 2

    # Built + Failed
    bf = overall["built_failed"]
    assert bf["count"] == 5
    # Ratios: 26/25=1.04, 10/50=0.2, 60/40=1.5, 28/28=1.0, 5/32=0.15625
    assert abs(bf["ratio_median"] - 1.0) < 1e-6
    assert bf["ratio_max"] == 1.5
    # Actual > planned : seed42 line 1 (26k > 25k) et seed42 line 3 (60k > 40k) -> 2 / 5
    assert abs(bf["share_actual_gt_planned"] - 0.4) < 1e-6
    # Overrun > margin : seed42 line 3 : overrun=20k > margin 15k -> 1 / 5
    assert bf["overrun_gt_margin_count"] == 1
    assert abs(bf["overrun_gt_margin_share"] - 0.2) < 1e-6

    # Failed sunk costs
    failed = overall["failed"]
    assert failed["count"] == 2
    assert failed["sunk_cost_sum"] == 15000.0
    assert failed["sunk_cost_median"] == 7500.0
    assert "ERR_FLAT_LAND" in failed["by_reason"]
    assert failed["by_reason"]["ERR_FLAT_LAND"]["sunk_cost_sum"] == 10000.0
    assert "ERR_LOCAL_AUTHORITY" in failed["by_reason"]
    assert failed["by_reason"]["ERR_LOCAL_AUTHORITY"]["sunk_cost_sum"] == 5000.0

    # First Revenue
    frev = overall["first_revenue"]
    assert frev["count"] == 3
    # Days : 111, 158, 100 -> médiane 111
    assert frev["days_median"] == 111.0
    # Reserve breach :
    # line 1 : cash_min 18k, reserve 15k -> +3k
    # line 3 : cash_min 12k, reserve 15k -> -3k (brèche !)
    # line 10 : cash_min 14k, reserve 12k -> +2k
    diff_st = frev["cash_min_minus_reserve"]
    assert diff_st["breached_count"] == 1
    assert abs(diff_st["breached_share"] - (1 / 3)) < 1e-6
    assert diff_st["min"] == -3000.0

    # Pending
    assert overall["pending"]["count"] == 1

    # new_airports breakdown
    assert report["by_new_airports"]["0"]["attempts"] == 1
    assert report["by_new_airports"]["1"]["attempts"] == 4
    assert report["by_new_airports"]["2"]["attempts"] == 3

    # Per-seed breakdown
    assert "42" in report["by_seed"]
    assert "100" in report["by_seed"]
    assert report["by_seed"]["42"]["attempts"] == 5
    assert report["by_seed"]["100"]["attempts"] == 3

    # Test de rendu texte
    rendered = render_report_table(report)
    assert "AIR FINANCE MARGIN & EXECUTION REPORT" in rendered
    assert "ERR_FLAT_LAND" in rendered
    assert "p6_shadow" in rendered

    # Test serialization JSON
    dumped = json.dumps(report)
    assert len(dumped) > 100

    print("SELFTEST OK: all assertions passed on inline fixtures.")
    return True


# ==============================================================================
# Point d'entrée CLI
# ==============================================================================


def collect_log_files(paths: Sequence[str | Path]) -> List[Path]:
    """Résout récursivement les chemins ou dossiers passés en fichiers .log."""
    files: List[Path] = []
    for item in paths:
        p = Path(item)
        if p.is_file():
            if p.suffix.lower() == ".log" or True:  # Accepte le fichier explicite
                files.append(p)
        elif p.is_dir():
            # Cherche les fichiers .log du dossier
            found = sorted(p.glob("*.log"))
            if not found:
                found = sorted(p.rglob("*.log"))
            files.extend(found)
        else:
            # Traite comme glob
            parent = p.parent if str(p.parent) != "" else Path(".")
            pattern = p.name
            matches = sorted(parent.glob(pattern))
            for m in matches:
                if m.is_file():
                    files.append(m)
    return sorted(set(files))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Parse les journaux OpenTTD pour analyser la télémétrie AIR_FINANCE."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Dossier contenant les fichiers .log, ou fichiers de log individuels",
    )
    parser.add_argument(
        "-d",
        "--dir",
        dest="log_dir",
        default=None,
        help="Dossier de journaux moteur (ex. results/<campaign>_engine/)",
    )
    parser.add_argument(
        "--json",
        metavar="PATH",
        nargs="?",
        const="-",
        default=None,
        help="Chemin du fichier JSON de sortie (ou '-' pour écrire le JSON sur stdout)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Exécute les auto-tests internes avec les fixtures intégrées",
    )
    args = parser.parse_args(argv)

    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    input_targets: List[str | Path] = []
    if args.log_dir:
        input_targets.append(args.log_dir)
    if args.inputs:
        input_targets.extend(args.inputs)

    runs: List[LogRunData] = []

    if input_targets:
        log_files = collect_log_files(input_targets)
        if not log_files:
            print(
                f"Erreur : aucun fichier .log trouvé dans : {input_targets}",
                file=sys.stderr,
            )
            return 1
        for f in log_files:
            runs.append(parse_log_file(f))
    else:
        # Lecture depuis stdin si canal ouvert
        if not sys.stdin.isatty():
            runs.append(parse_log_stream(sys.stdin, seed=0, filename="stdin"))
        else:
            parser.print_help(sys.stderr)
            return 1

    report = aggregate_runs(runs)

    if args.json:
        json_text = json.dumps(report, ensure_ascii=False, indent=2)
        if args.json == "-":
            print(json_text)
        else:
            out_path = Path(args.json)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json_text + "\n", encoding="utf-8")
            # Affiche aussi le tableau récapitulatif sur stdout
            print(render_report_table(report))
    else:
        print(render_report_table(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
