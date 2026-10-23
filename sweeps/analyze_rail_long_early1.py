#!/usr/bin/env python3
"""Passive RAIL-LONG-EARLY-1 funnel from OpexAI ``decision_log`` files.

Usage:
    python sweeps/analyze_rail_long_early1.py results/campaign_engine --format markdown
    python sweeps/analyze_rail_long_early1.py results/campaign_engine --format json --out report.json

Accepts one or more ``.log`` / ``.log.gz`` files or directories. Policies are
separated by the ``<policy>_seed<N>_r<K>.log`` filename convention. All numbers
are *event occurrences*, never independent opportunities or paired causal
effects. A RAIL_ATTEMPT lacks cargo and a RAIL_BUILD lacks kind in the current
schema: do not fabricate either by joining unrelated log lines.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import gzip
import json
from pathlib import Path
import re
import statistics


EVENTS = frozenset({
    "RAIL_LONG_SCREEN", "RAIL_LONG_CANDIDATE", "PROJECT_CHOSEN", "RAIL_ATTEMPT",
    "RAIL_BUILD", "AIR_BUILD", "PORTFOLIO_RANK", "V217_RAIL_REFILL",
})
DISTANCE_BINS = ("<=200", "201-250", "251-350", "351-400", ">400", "unknown")
OPEX_LINE = re.compile(r"\bOPEX (\d{4})-(\d{1,2})-(\d{1,2}) ([A-Z0-9_]+)(?: (.*))?$")
FIELD = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)")
POLICY_FILE = re.compile(r"(?P<policy>.+)_seed\d+_r\d+\.log(?:\.gz)?$", re.I)
LIMITATIONS = (
    "Les nombres sont des occurrences de journal, pas des OD/projets uniques ; "
    "les régénérations et classements successifs peuvent répéter une paire.",
    "RAIL_LONG_SCREEN rapporte des passages par filtre (distance_long, economics, "
    "profit, ratio, accepted), distincts des candidats admis RAIL_LONG_CANDIDATE ; "
    "ses compteurs ne sont pas des projets uniques.",
    "RAIL_LONG_CANDIDATE n'est émis que pour des candidats acceptés >200 "
    "lorsque la sonde correspondante est active : zéro événement n'implique pas zéro candidat.",
    "RAIL_ATTEMPT ne porte pas de cargo et RAIL_BUILD ne porte pas de kind ; "
    "unknown signifie non observé. Aucune jointure OD implicite n'est effectuée.",
    "iters, ops et search_ops négatifs (notamment -1) sont des sentinelles "
    "indisponibles ; leurs statistiques excluent ces valeurs.",
    "AIR choisi, AIR bâti et AIR classé derrière une tête RAIL sont des observations ; "
    "elles ne prouvent ni éviction causale ni profit AIR perdu.",
    "Le diagnostic decision_log peut modifier le coût en opcodes et les trajectoires ; "
    "comparer uniquement des bras instrumentés identiquement. Pas de qualification économique ici.",
)


def decode_line(line: str):
    """Return (year, event, fields), or None for irrelevant/invalid rows."""
    match = OPEX_LINE.search(line.rstrip())
    if match is None:
        return None
    year, month, day, tag, values = match.groups()
    if tag not in EVENTS or not (1 <= int(month) <= 12 and 1 <= int(day) <= 31):
        return None
    return int(year), tag, dict(FIELD.findall(values or ""))


def number(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def distance_bin(value):
    """Manhattan distances; nonpositive and absent values stay unclassified."""
    dist = number(value)
    if dist is None or dist <= 0:
        return "unknown"
    if dist <= 200:
        return "<=200"
    if dist <= 250:
        return "201-250"
    if dist <= 350:
        return "251-350"
    if dist <= 400:
        return "351-400"
    return ">400"


def numeric_stats(values):
    if not values:
        return {"n": 0, "sum": 0, "mean": None, "median": None}
    return {
        "n": len(values), "sum": sum(values),
        "mean": round(statistics.mean(values), 2),
        "median": statistics.median(values),
    }


@dataclass
class EventBucket:
    counts: Counter = field(default_factory=Counter)
    failures: Counter = field(default_factory=Counter)
    screen_reasons: Counter = field(default_factory=Counter)
    caps: Counter = field(default_factory=Counter)
    iters: list[int] = field(default_factory=list)
    search_ops: list[int] = field(default_factory=list)
    ops: list[int] = field(default_factory=list)

    def record(self, event, fields):
        name = {
            "RAIL_LONG_SCREEN": "screened", "RAIL_LONG_CANDIDATE": "candidates",
            "PROJECT_CHOSEN": "chosen",
            "PORTFOLIO_RANK": "ranked", "RAIL_ATTEMPT": "attempts",
            "RAIL_BUILD": "built", "AIR_BUILD": "built",
        }[event]
        self.counts[name] += 1
        if event == "RAIL_LONG_SCREEN":
            self.screen_reasons[fields.get("reason") or "unknown"] += 1
        if event == "RAIL_LONG_CANDIDATE":
            cap = number(fields.get("cap"))
            if cap is not None and cap > 0:
                self.caps[str(cap)] += 1
        if event != "RAIL_ATTEMPT":
            return
        ok = fields.get("ok")
        if ok == "1":
            self.counts["attempt_ok"] += 1
        elif ok == "0":
            self.counts["attempt_failed"] += 1
            self.failures[fields.get("reason") or "unknown"] += 1
        else:
            self.counts["attempt_unknown_outcome"] += 1
        for key, target in (("iters", self.iters), ("search_ops", self.search_ops),
                            ("ops", self.ops)):
            value = number(fields.get(key))
            if value is not None and value >= 0:
                target.append(value)

    def report(self):
        return {
            **{name: self.counts[name] for name in (
                "screened", "candidates", "ranked", "chosen", "attempts", "attempt_ok",
                "attempt_failed", "attempt_unknown_outcome", "built")},
            "screen_reasons": dict(sorted(self.screen_reasons.items())),
            "failure_reasons": dict(sorted(self.failures.items())),
            "candidate_caps": dict(sorted(self.caps.items(), key=lambda item: int(item[0]))),
            "iters": numeric_stats(self.iters),
            "search_ops": numeric_stats(self.search_ops),
            "ops": numeric_stats(self.ops),
        }


@dataclass
class RefillBucket:
    calls: int = 0
    v269_active: int = 0
    freight_caps: Counter = field(default_factory=Counter)
    ops: list[int] = field(default_factory=list)
    candidates: list[int] = field(default_factory=list)
    startable: list[int] = field(default_factory=list)

    def record(self, fields):
        self.calls += 1
        if fields.get("v269") == "1":
            self.v269_active += 1
        cap = number(fields.get("freight_cap"))
        if cap is not None and cap > 0:
            self.freight_caps[str(cap)] += 1
        for key, output in (("ops", self.ops), ("candidates", self.candidates),
                            ("startable", self.startable)):
            value = number(fields.get(key))
            if value is not None and value >= 0:
                output.append(value)

    def report(self):
        return {
            "calls": self.calls, "v269_active": self.v269_active,
            "freight_caps": dict(sorted(self.freight_caps.items(), key=lambda item: int(item[0]))),
            "ops": numeric_stats(self.ops),
            "candidates": numeric_stats(self.candidates),
            "startable": numeric_stats(self.startable),
        }


class PolicyAccumulator:
    def __init__(self):
        self.files = []
        self.coverage = Counter()
        self.ignored_modes = Counter()
        self.by_year_mode = defaultdict(EventBucket)
        self.by_detail = defaultdict(EventBucket)
        self.refills = defaultdict(RefillBucket)
        self.rank_lists = defaultdict(Counter)

    def record(self, year, event, fields):
        self.coverage[event] += 1
        if event == "V217_RAIL_REFILL":
            self.refills[(year, fields.get("cargo") or "unknown")].record(fields)
            return
        mode = {"RAIL_LONG_SCREEN": "rail", "RAIL_LONG_CANDIDATE": "rail",
                "RAIL_ATTEMPT": "rail",
                "RAIL_BUILD": "rail", "AIR_BUILD": "air"}.get(event, fields.get("mode"))
        if mode not in ("rail", "air"):
            self.ignored_modes[mode or "unknown"] += 1
            return
        raw_distance = fields.get("manh") if event == "RAIL_ATTEMPT" else fields.get("dist")
        bin_name = distance_bin(raw_distance)
        kind = fields.get("kind") or "unknown"
        cargo = fields.get("cargo") or "unknown"
        self.by_year_mode[(year, mode)].record(event, fields)
        self.by_detail[(year, mode, bin_name, cargo, kind)].record(event, fields)

    def record_ranking_list(self, rows):
        """Co-ranking within a *contiguous* PORTFOLIO_RANK list only."""
        if not rows or rows[0][2].get("rank") != "0":
            return
        year, _, head = rows[0]
        mode = head.get("mode") or "unknown"
        stats = self.rank_lists[year]
        stats["lists"] += 1
        if mode == "rail":
            stats["rail_heads"] += 1
            long_head = distance_bin(head.get("dist")) in DISTANCE_BINS[1:5]
            if long_head:
                stats["long_rail_heads"] += 1
            if any(row.get("mode") == "air" for _, _, row in rows[1:]):
                stats["rail_head_with_air_ranked"] += 1
                if long_head:
                    stats["long_rail_head_with_air_ranked"] += 1
        elif mode == "air":
            stats["air_heads"] += 1

    def report(self):
        year_mode = []
        for (year, mode), bucket in sorted(self.by_year_mode.items()):
            year_mode.append({"year": year, "mode": mode, **bucket.report()})
        details = []
        for (year, mode, dist, cargo, kind), bucket in sorted(
                self.by_detail.items(), key=lambda item: (
                    item[0][0], item[0][1], DISTANCE_BINS.index(item[0][2]), item[0][3], item[0][4])):
            details.append({"year": year, "mode": mode, "distance_bin": dist,
                            "cargo": cargo, "kind": kind, **bucket.report()})
        refills = [
            {"year": year, "cargo": cargo, **bucket.report()}
            for (year, cargo), bucket in sorted(self.refills.items())
        ]
        ranking = [
            {"year": year, **{key: stats[key] for key in (
                "lists", "rail_heads", "air_heads", "long_rail_heads",
                "rail_head_with_air_ranked", "long_rail_head_with_air_ranked")}}
            for year, stats in sorted(self.rank_lists.items())
        ]
        return {
            "files": self.files,
            "event_coverage": {tag: self.coverage[tag] for tag in sorted(EVENTS)},
            "ignored_other_mode_events": dict(sorted(self.ignored_modes.items())),
            "by_year_mode": year_mode,
            "by_year_distance_cargo_kind": details,
            "refills_by_year_cargo": refills,
            "ranked_lists_by_year": ranking,
        }


def policy_from_filename(path: Path):
    match = POLICY_FILE.fullmatch(path.name)
    return match.group("policy") if match else "unknown"


def analyze_sources(sources):
    """Analyze (path, iterable of lines) sources, keeping policies disjoint."""
    collectors = {}
    for file_path, lines in sources:
        path = Path(file_path)
        policy = policy_from_filename(path)
        collector = collectors.setdefault(policy, PolicyAccumulator())
        collector.files.append(str(path))
        ranking = []
        next_rank = 0

        def flush_ranking():
            nonlocal ranking, next_rank
            collector.record_ranking_list(ranking)
            ranking = []
            next_rank = 0

        for line in lines:
            parsed = decode_line(line)
            if parsed is None:
                # A different Opex event interrupts the ranking block;
                # unrelated engine output is allowed between its rows.
                if OPEX_LINE.search(line.rstrip()):
                    flush_ranking()
                continue
            year, event, fields = parsed
            if event == "PORTFOLIO_RANK":
                rank = number(fields.get("rank"))
                if rank == 0 or rank != next_rank:
                    flush_ranking()
                if rank is not None and rank == next_rank:
                    ranking.append((year, event, fields))
                    next_rank += 1
            else:
                flush_ranking()
            collector.record(year, event, fields)
        flush_ranking()
    return {
        "scope": "passive_decision_log_event_counts",
        "distance_bins": list(DISTANCE_BINS),
        "limitations": list(LIMITATIONS),
        "policies": {key: collectors[key].report() for key in sorted(collectors)},
    }


def _open_log(path):
    if path.name.endswith(".log.gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")


def find_logs(paths, policy=None):
    """Expand explicitly supplied files/directories and avoid counting twice."""
    found = {}
    for candidate in paths:
        path = Path(candidate)
        if not path.exists():
            raise FileNotFoundError(path)
        matches = path.iterdir() if path.is_dir() else (path,)
        for item in matches:
            if not item.is_file() or not (item.name.endswith(".log") or item.name.endswith(".log.gz")):
                continue
            if policy is not None and policy_from_filename(item) != policy:
                continue
            found[str(item.resolve())] = item
    return [found[key] for key in sorted(found)]


def analyze_paths(paths, policy=None):
    log_files = find_logs(paths, policy=policy)
    if not log_files:
        raise ValueError("Aucun journal .log/.log.gz correspondant")
    # Stream one file at a time, including gzip streams.
    def inputs():
        for path in log_files:
            with _open_log(path) as handle:
                yield path, handle
    return analyze_sources(inputs())


def _summary_failures(row):
    failures = row["failure_reasons"]
    return ", ".join(f"{key}:{value}" for key, value in failures.items()) or "—"


def render_markdown(report):
    lines = ["# RAIL-LONG-EARLY-1 — diagnostic des journaux decision_log", "",
             "Observations agrégées par politique, année, distance Manhattan, cargo et type.", ""]
    for policy, data in report["policies"].items():
        lines.extend([f"## Politique `{policy}` ({len(data['files'])} journaux)", "",
                      "| Année | Mode | Filtrés | Candidats longs | Classés | Choisis | Tentatives | Échecs | Bâtis | Itérations Σ | Recherche ops Σ |",
                      "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"])
        for row in data["by_year_mode"]:
            lines.append(f"| {row['year']} | {row['mode']} | {row['screened']} | {row['candidates']} | {row['ranked']} | "
                         f"{row['chosen']} | {row['attempts']} | {row['attempt_failed']} | "
                         f"{row['built']} | {row['iters']['sum']} ({row['iters']['n']} mes.) | "
                         f"{row['search_ops']['sum']} ({row['search_ops']['n']} mes.) |")
        lines.extend(["", "### Détail par année, distance, cargo et type", "",
                      "| Année | Mode | Distance | Cargo | Type | Filtrés (motifs) | Candidats | Classés | Choisis | Tentatives (OK/KO/?) | Bâtis | Échecs par raison | Iter. Σ/n | Search ops Σ/n |",
                      "|---|---|---|---|---|---|---:|---:|---:|---|---:|---|---|---|"])
        for row in data["by_year_distance_cargo_kind"]:
            attempts = f"{row['attempts']} ({row['attempt_ok']}/{row['attempt_failed']}/{row['attempt_unknown_outcome']})"
            screens = ", ".join(f"{k}:{v}" for k, v in row["screen_reasons"].items()) or "—"
            lines.append(f"| {row['year']} | {row['mode']} | {row['distance_bin']} | "
                         f"{row['cargo']} | {row['kind']} | {row['screened']} ({screens}) | {row['candidates']} | "
                         f"{row['ranked']} | {row['chosen']} | {attempts} | {row['built']} | "
                         f"{_summary_failures(row)} | {row['iters']['sum']}/{row['iters']['n']} | "
                         f"{row['search_ops']['sum']}/{row['search_ops']['n']} |")
        lines.extend(["", "### Recharges V217", "",
                      "| Année | Cargo | Appels | V269 actif | Plafonds fret | Projets publiés Σ/n | Opcodes Σ/n |",
                      "|---|---|---:|---:|---|---|---|"])
        for row in data["refills_by_year_cargo"]:
            caps = ", ".join(f"{k}:{v}" for k, v in row["freight_caps"].items()) or "—"
            lines.append(f"| {row['year']} | {row['cargo']} | {row['calls']} | {row['v269_active']} | "
                         f"{caps} | {row['candidates']['sum']}/{row['candidates']['n']} | "
                         f"{row['ops']['sum']}/{row['ops']['n']} |")
        lines.extend(["", "### Classements : AIR derrière une tête RAIL", "",
                      "| Année | Classements | Têtes RAIL | Têtes AIR | Têtes RAIL >200 | RAIL tête + AIR classé | RAIL >200 tête + AIR classé |",
                      "|---|---:|---:|---:|---:|---:|---:|"])
        for row in data["ranked_lists_by_year"]:
            lines.append(f"| {row['year']} | {row['lists']} | {row['rail_heads']} | "
                         f"{row['air_heads']} | {row['long_rail_heads']} | "
                         f"{row['rail_head_with_air_ranked']} | {row['long_rail_head_with_air_ranked']} |")
        lines.extend(["", "Couverture des événements : " + ", ".join(
            f"`{tag}`={count}" for tag, count in data["event_coverage"].items()), ""])
    lines.extend(["## Limites d'attribution", ""])
    lines.extend(f"- {warning}" for warning in report["limitations"])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="Dossiers _engine ou fichiers .log/.log.gz")
    parser.add_argument("--policy", help="Filtrer par identifiant de politique extrait du nom de fichier")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--out", type=Path, help="Écrire le rapport (sinon stdout)")
    args = parser.parse_args(argv)
    try:
        report = analyze_paths(args.inputs, policy=args.policy)
    except (FileNotFoundError, OSError, ValueError) as exc:
        parser.error(str(exc))
    output = (json.dumps(report, ensure_ascii=False, indent=2) + "\n"
              if args.format == "json" else render_markdown(report))
    if args.out is None:
        print(output, end="")
    else:
        args.out.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
