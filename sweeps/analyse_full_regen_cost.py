#!/usr/bin/env python3
"""analyse_full_regen_cost.py

Analyseur de journaux moteur OpenTTD (-d script=4) pour quantifier le coût en opcodes
des reconstructions complètes de catalogue et portefeuille d'OpexAI.

Format de ligne ciblé émis par ai/OpexAI/task_report.nut:1480 via ai/OpexAI/probes.nut:2415 :
    dbg: [script] [OpexAI] [C76] C76_REGEN phase=regen kind=full reason=<reason> ops=<ops> days=<days> [modes=<modes>] y=<year>

Ce script fonctionne avec la bibliothèque standard Python 3 uniquement.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Format réel (ai/OpexAI/task_report.nut:1450 puis OpexC76Log, probes.nut:2412) :
#   ... OPEX <Y>-<M>-<D> C76_REGEN phase=regen kind=<kind> reason=<reason> year=<year>
#       days=<days> days_since_prev=<n> ops=<ops> towns_n=... (champs clé=valeur)
# L'ordre des champs n'est pas garanti stable : on lit les paires clé=valeur.
# Capture all KV fields regardless of their order; parse_log_line checks phase.
RE_C76_REGEN = re.compile(r"\bC76_REGEN\s+(.*)$")
RE_FIELD = re.compile(r"(\w+)=(\S*)")
RE_GAME_NAME = re.compile(r"(?P<arm>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log")


def parse_log_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse une ligne C76_REGEN phase=regen ; None pour toute autre ligne."""
    m = RE_C76_REGEN.search(line.rstrip())
    if not m:
        return None
    fields = dict(RE_FIELD.findall(m.group(1)))
    if fields.get("phase") != "regen":
        return None
    try:
        ops = int(fields["ops"])
        if ops < 0:
            return None  # invalid measurement, never a negative opcode saving
        return {
            "kind": fields["kind"],
            "reason": fields.get("reason", "unknown"),
            "ops": ops,
            "days": int(fields.get("days", 0)),
            "modes": fields.get("modes"),
            "year": int(fields["year"]),
        }
    except (KeyError, ValueError):
        return None


def parse_log_files(paths: List[Path], kind_filter: Optional[str] = "full") -> List[Dict[str, Any]]:
    """Lit une liste de fichiers de logs et extrait les événements de régénération."""
    events: List[Dict[str, Any]] = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            opener = gzip.open if path.suffix == ".gz" else open
            with opener(path, "rt", encoding="utf-8", errors="replace") as f:
                for line_no, line in enumerate(f, start=1):
                    rec = parse_log_line(line)
                    if rec is not None:
                        if kind_filter is None or rec["kind"] == kind_filter:
                            rec["source_file"] = str(path)
                            rec["line_no"] = line_no
                            events.append(rec)
        except OSError as e:
            sys.stderr.write(f"Avertissement : impossible de lire {path}: {e}\n")
    return events


def aggregate_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Agrège les événements par motif et par année."""
    total_ops_all = sum(ev["ops"] for ev in events)
    total_count_all = len(events)

    # Agrégation globale par motif
    by_reason_raw: Dict[str, List[int]] = {}
    by_year_raw: Dict[int, Dict[str, List[int]]] = {}

    for ev in events:
        r = ev["reason"]
        y = ev["year"]
        ops = ev["ops"]

        by_reason_raw.setdefault(r, []).append(ops)
        by_year_raw.setdefault(y, {}).setdefault(r, []).append(ops)

    def stats_for_ops(ops_list: List[int], grand_total_ops: int) -> Dict[str, Any]:
        count = len(ops_list)
        total = sum(ops_list)
        med = float(statistics.median(ops_list)) if ops_list else 0.0
        max_v = max(ops_list) if ops_list else 0
        min_v = min(ops_list) if ops_list else 0
        share = (total / grand_total_ops * 100.0) if grand_total_ops > 0 else 0.0
        return {
            "count": count,
            "total_ops": total,
            "median_ops": med,
            "max_ops": max_v,
            "min_ops": min_v,
            "share_pct": round(share, 2),
        }

    by_reason: Dict[str, Any] = {}
    for r, ops_list in sorted(by_reason_raw.items(), key=lambda kv: sum(kv[1]), reverse=True):
        by_reason[r] = stats_for_ops(ops_list, total_ops_all)

    by_year: Dict[str, Any] = {}
    for y in sorted(by_year_raw.keys()):
        year_total_ops = sum(sum(lst) for lst in by_year_raw[y].values())
        by_year[str(y)] = {
            "total_ops": year_total_ops,
            "reasons": {
                r: stats_for_ops(ops_list, year_total_ops)
                for r, ops_list in sorted(by_year_raw[y].items(), key=lambda kv: sum(kv[1]), reverse=True)
            },
        }

    return {
        "total_events": total_count_all,
        "total_ops": total_ops_all,
        "by_reason": by_reason,
        "by_year": by_year,
    }


def format_text_summary(summary: Dict[str, Any], kind_filter: Optional[str] = "full") -> str:
    """Produit un rapport texte formaté pour la console."""
    lines: List[str] = []
    lines.append("=" * 78)
    lines.append(f"BILAN DES RECONSTRUCTIONS OPEXAI (kind={kind_filter or 'tous'})")
    lines.append("=" * 78)
    lines.append(f"Événements totaux : {summary['total_events']}")
    lines.append(f"Opcodes totaux   : {summary['total_ops']:,}")
    lines.append("")

    lines.append("1. VENTILATION PAR MOTIF (REASON)")
    lines.append("-" * 78)
    header = f"{'Motif':<16} | {'Nombre':>8} | {'Total Opcodes':>15} | {'Médiane':>12} | {'Max':>12} | {'Part %':>8}"
    lines.append(header)
    lines.append("-" * 78)
    for reason, data in summary.get("by_reason", {}).items():
        line = (
            f"{reason:<16} | "
            f"{data['count']:>8} | "
            f"{data['total_ops']:>15,} | "
            f"{int(data['median_ops']):>12,} | "
            f"{data['max_ops']:>12,} | "
            f"{data['share_pct']:>7.2f}%"
        )
        lines.append(line)
    lines.append("-" * 78)
    lines.append("")

    lines.append("2. VENTILATION CHRONOLOGIQUE PAR ANNÉE")
    lines.append("-" * 78)
    for year, ydata in summary.get("by_year", {}).items():
        lines.append(f"Année {year} (Total: {ydata['total_ops']:,} ops) :")
        for reason, rdata in ydata.get("reasons", {}).items():
            lines.append(
                f"  - {reason:<14} : {rdata['count']:>3} fois, "
                f"{rdata['total_ops']:>12,} ops ({rdata['share_pct']:>5.1f}% de l'année), "
                f"méd={int(rdata['median_ops']):,} max={rdata['max_ops']:,}"
            )
    lines.append("=" * 78)
    return "\n".join(lines)


def collect_log_paths(inputs: List[str]) -> List[Path]:
    """Collecte les journaux et réconcilie les copies .log/.log.gz exactes."""
    collected: List[Path] = []
    for inp in inputs:
        p = Path(inp)
        if p.is_file():
            collected.append(p)
        elif p.is_dir():
            for root, _, files in os.walk(p):
                for f in files:
                    if f.endswith((".log", ".log.gz")) or "engine" in f:
                        collected.append(Path(root) / f)
        else:
            sys.stderr.write(f"Avertissement : chemin introuvable : {inp}\n")
    def decompressed_digest(path: Path) -> str:
        digest = hashlib.sha256()
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    by_logical_file: Dict[Path, Path] = {}
    numeric_game_names: Dict[tuple, str] = {}
    for path in sorted({p.resolve() for p in collected}):
        base_name = path.name[:-3] if path.suffix == ".gz" else path.name
        match = RE_GAME_NAME.fullmatch(base_name)
        if match is not None:
            game = (str(path.parent), match["arm"], int(match["seed"]),
                    int(match["repeat"]))
            previous_name = numeric_game_names.setdefault(game, base_name)
            if previous_name != base_name:
                raise ValueError(
                    f"identite de partie ambigue : {previous_name} / {base_name}"
                )
        key = path.with_name(base_name)
        previous = by_logical_file.get(key)
        if previous is None:
            by_logical_file[key] = path
        else:
            if decompressed_digest(previous) != decompressed_digest(path):
                raise ValueError(f"copies de journal contradictoires : {previous} / {path}")
            if previous.suffix == ".gz" and path.suffix != ".gz":
                by_logical_file[key] = path
    return sorted(by_logical_file.values())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyse du coût en opcodes des reconstructions complètes OpexAI (-d script=4)."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Chemins vers les fichiers .log ou dossiers contenant les logs (*_engine).",
    )
    parser.add_argument(
        "--kind",
        default="full",
        help="Filtre sur le champ kind (défaut: 'full', passer 'all' pour tous les kinds).",
    )
    parser.add_argument(
        "--out",
        help="Chemin du fichier JSON de sortie.",
    )
    args = parser.parse_args()

    paths = collect_log_paths(args.inputs)
    if not paths:
        sys.stderr.write("Erreur : aucun fichier de journal trouvé.\n")
        return 1

    kind_filter = None if args.kind == "all" else args.kind
    events = parse_log_files(paths, kind_filter=kind_filter)
    summary = aggregate_events(events)

    text_report = format_text_summary(summary, kind_filter=kind_filter)
    print(text_report)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\nRésultats structurés enregistrés dans {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
