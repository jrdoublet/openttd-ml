#!/usr/bin/env python3
"""Audit des journaux RLW-04; aucune inference de rentabilite ou de constructibilite.

Usage :
  uvx --from 'pytest==8.4.2' python sweeps/analyze_rlw04.py results/<campaign> --format markdown
  python sweeps/analyze_rlw04.py results/<campaign> --expect-off --format json
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re


ROW = re.compile(r"\bOPEX (\d{4}-\d{1,2}-\d{1,2}) (RLW04_ENUM|RLW04_UNIT)\s+(.*)$")
KV = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)=([^\s]+)")
SUM_FIELDS = ("slices", "scanned", "visited", "band224_288", "outside201_223",
              "overrun", "calls", "low_reserve", "multislice", "extra_slices",
              "total_refresh_ops", "total_full_ops", "total_work_ops",
              "total_tail_ops", "total_enum_log_ops", "total_unit_log_ops",
              "priority_steps", "fair_steps", "index_steps", "indexed", "scan_steps",
              "sources_advanced", "cell_skips", "geo_skips", "index_ops", "scan_ops")
PEAK_FIELDS = ("stock_pax", "stock_freight", "max_ops", "max_work_ops",
               "max_tail_ops", "init_ops", "max_log_ops", "max_full_ops",
               "max_enum_log_ops", "max_refresh_ops")


def parse_line(line: str):
    match = ROW.search(line.strip())
    if not match:
        return None
    fields = dict(KV.findall(match.group(3)))
    fields["_date"] = match.group(1)
    return match.group(2), fields


def read_log(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parsed = parse_line(line)
            if parsed:
                yield parsed


def log_paths(inputs):
    paths = set()
    for raw in inputs:
        path = Path(raw)
        if path.is_file():
            paths.add(path)
        elif path.is_dir():
            paths.update(p for p in path.rglob("*")
                         if p.is_file() and (p.name.endswith(".log") or p.name.endswith(".log.gz")))
        else:
            raise FileNotFoundError(path)
    return sorted(paths)


def numeric(fields, key):
    value = fields.get(key)
    return int(value) if value is not None and value.lstrip("-").isdigit() else None


def final_snapshots(phases):
    """Cumulative counters reset only after stale_restart. Count each epoch once.

    Slice/refresh logs are checkpoints; a later stale_restart/done supersedes them.
    Keep the last slice only for an epoch not yet closed when the game ends.
    """
    snapshots = []
    pending = None
    for event in phases:
        pending = event
        if event.get("phase") in ("stale_restart", "done"):
            snapshots.append(event)
            pending = None
    if pending is not None:
        snapshots.append(pending)
    return snapshots


def progress_regressions(phases):
    """Count decreases of cumulative counters *within* an enumeration epoch.

    A true stale_restart closes the previous epoch; a catalog refresh must not
    reset source progress. Missing numeric counters cannot prove regression.
    """
    previous = None
    regressions = 0
    for event in phases:
        if previous is not None:
            decreasing = any(numeric(event, key) is not None and numeric(previous, key) is not None
                             and numeric(event, key) < numeric(previous, key)
                             for key in ("slices", "scanned", "band224_288", "outside201_223",
                                         "overrun", "refreshes"))
            pending_grew = (numeric(event, "pending") is not None
                            and numeric(previous, "pending") is not None
                            and numeric(event, "pending") > numeric(previous, "pending"))
            if decreasing or pending_grew:
                regressions += 1
        previous = None if event.get("phase") in ("stale_restart", "done") else event
    return regressions


def summarize(paths):
    results = []
    for path in paths:
        phases = []
        units = []
        for name, fields in read_log(path):
            if name == "RLW04_ENUM":
                phases.append(fields)
            else:
                units.append(fields)
        checkpoints = final_snapshots(phases)
        fields = {}
        cursor_samples = {}
        unit_progress_regressions = 0
        for entry in phases:
            if entry.get("phase") == "stale_restart":
                cursor_samples = {}
                continue
            unit_index = numeric(entry, "unit_index")
            if unit_index is None:
                continue
            sample = {
                "unit_index": unit_index, "family": entry.get("unit_family"),
                "cargo": entry.get("unit_cargo"),
                "source": numeric(entry, "unit_source"),
                "sources": numeric(entry, "unit_sources"),
                "visited": numeric(entry, "unit_visited"),
                "done": numeric(entry, "unit_done"),
                "date": entry.get("_date"),
            }
            previous = cursor_samples.get(unit_index)
            if previous is not None and any(sample[name] is not None and previous[name] is not None
                                            and sample[name] < previous[name]
                                            for name in ("source", "visited", "done")):
                unit_progress_regressions += 1
            cursor_samples[unit_index] = sample
        fields["unit_progress_regressions"] = unit_progress_regressions
        for key in SUM_FIELDS:
            values = [numeric(p, key) for p in checkpoints]
            fields[key] = sum(values) if values and all(v is not None for v in values) else None
        for key in PEAK_FIELDS:
            values = [numeric(p, key) for p in phases]
            known = [v for v in values if v is not None]
            fields[key] = max(known) if known else None
        fields["budget"] = numeric(phases[-1], "budget") if phases else None
        fields["pending"] = numeric(phases[-1], "pending") if phases else None
        fields["units"] = numeric(phases[-1], "units") if phases else None
        if phases:
            # RLW04 n'entre en jeu qu'apres les deux premieres annees.
            # La couverture en mois est une borne calendaire du premier
            # millesime trace, pas une mesure du nombre d'appels eligibles.
            year, month, _ = map(int, phases[-1]["_date"].split("-"))
            first_year = int(phases[0]["_date"].split("-")[0])
            months = (year - first_year) * 12 + month
            fields["months_since_first_year"] = months
            fields["slices_per_month"] = (round(fields["slices"] / months, 2)
                                             if fields["slices"] is not None else None)
        else:
            fields["months_since_first_year"] = None
            fields["slices_per_month"] = None
        fields["scanned_per_slice"] = (round(fields["scanned"] / fields["slices"], 2)
                                      if fields["scanned"] is not None and fields["slices"] else None)
        full = fields["total_full_ops"]
        fields["log_share_pct"] = (round(100 * (fields["total_enum_log_ops"] + fields["total_unit_log_ops"]) / full, 2)
                                   if full and fields["total_enum_log_ops"] is not None
                                   and fields["total_unit_log_ops"] is not None else None)
        fields["work_share_pct"] = (round(100 * fields["total_work_ops"] / full, 2)
                                    if full and fields["total_work_ops"] is not None else None)
        fields["cursor_samples"] = [cursor_samples[i] for i in sorted(cursor_samples)]
        refresh_counts = [numeric(p, "refreshes") for p in checkpoints]
        # New RLW-04 logs use a per-state cumulative refreshes field. Older or
        # synthetic logs can instead have an explicit refresh phase.
        if refresh_counts and all(count is not None for count in refresh_counts):
            refreshes = sum(refresh_counts)
        elif any(count is not None for count in refresh_counts):
            refreshes = None  # Mixed schemas cannot give an exact total.
        else:
            refreshes = sum(p.get("phase", "").startswith("refresh") for p in phases)
        completed = any(p.get("phase") == "done" for p in phases)
        budget_observed_ok = None
        measured_peak = fields["max_full_ops"] if fields["max_full_ops"] is not None else fields["max_ops"]
        if fields["budget"] is not None and measured_peak is not None and fields["overrun"] is not None:
            budget_observed_ok = measured_peak <= fields["budget"] and fields["overrun"] == 0
        results.append({"file": str(path), "has_shadow": bool(phases or units),
                        "complete": completed, "slices_logged": len(phases),
                        "epochs": len(checkpoints),
                        "stale_restarts": sum(p.get("phase") == "stale_restart" for p in phases),
                        "refreshes": refreshes,
                        "progress_regressions": progress_regressions(phases),
                        "slice_budget_observed_ok": budget_observed_ok,
                        "units_logged": len(units), "per_cargo": units,
                        **fields})
    return {"files": results, "logs": len(results),
            "with_shadow": sum(r["has_shadow"] for r in results),
            "complete": sum(r["complete"] for r in results),
            "limitations": [
                "Grille spatiale : seuls les puits 224..288 passes par le filtre Manhattan sont evalues; 201..223 reste a zero par construction dans cette version.",
                "Le stock contient des paires echantillonnees, pas des candidats evalues par OpexMakeCandidate.",
                "Les compteurs cumulatifs sont sommes par cycle entre stale_restart; les pics sont les maxima journalises.",
                "refreshes cumule les compteurs de cycle si disponibles; un refresh n'est pas une remise a zero; progress_regressions detecte les reculs visibles.",
                "Un cycle inacheve sans checkpoint final reste partiellement mesure; max_ops exclut les frais de log.",
                "max_full_ops (si disponible) inclut les logs pendant une tranche; init et refresh ont leurs compteurs propres.",
                "slices_per_month est une moyenne depuis janvier du premier millesime trace, sans connaitre le nombre d'appels eligibles.",
                "slice_budget_observed_ok porte sur les tranches journalisees; un schema ancien sans max_full_ops ne certifie pas les logs.",
                "Aucun evenement RLW04 n'etablit la constructibilite, l'eviction AIR ou un gain economique.",
                "DECISION_LOG et RLW03_SHADOW peuvent perturber la trajectoire: hors portes economiques.",
            ]}


def markdown(report):
    lines = ["# RLW-04 — audit d'enumeration (shadow)", "",
             f"Journaux: {report['logs']} ; traces shadow: {report['with_shadow']} ; passes closes: {report['complete']}", "",
             "| Fichier | Traces | Complet | Relances | Refresh | Reculs | Tranches | Sources/cargos clos | Paires testees | 224..288 | 201..223 (hors bande) | Pic ops | Depassements | Budget observe |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in report["files"]:
        label = Path(row["file"]).name
        val = lambda key: "?" if row[key] is None else str(row[key])
        budget_ok = "?" if row["slice_budget_observed_ok"] is None else ("oui" if row["slice_budget_observed_ok"] else "non")
        lines.append(f"| {label} | {int(row['has_shadow'])} | {int(row['complete'])} | {row['stale_restarts']} | {val('refreshes')} | {row['progress_regressions']} | {val('slices')} | {row['units_logged']} | "
                     f"{val('scanned')} | {val('band224_288')} | {val('outside201_223')} | "
                     f"{val('max_ops')} | {val('overrun')} | {budget_ok} |")
    lines.extend(["", "| Fichier | Mois observes (depuis janvier) | Tranches/mois | Paires/tranche | Appels | Refus reserve | Tranches bonus | Pic complet | Init | Pic refresh | Pic log ENUM |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"])
    for row in report["files"]:
        val = lambda key: "?" if row[key] is None else str(row[key])
        lines.append(f"| {Path(row['file']).name} | {val('months_since_first_year')} | {val('slices_per_month')} | {val('scanned_per_slice')} | {val('calls')} | {val('low_reserve')} | {val('extra_slices')} | {val('max_full_ops')} | {val('init_ops')} | {val('max_refresh_ops')} | {val('max_enum_log_ops')} |")
    lines.extend(["", "| Fichier | Travail / budget utilise (%) | Logs / budget utilise (%) | Travail total | Tranches total | Init | Refresh total | Logs total | Curseurs source/cargo observes | Reculs individuels |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"])
    for row in report["files"]:
        val = lambda key: "?" if row[key] is None else str(row[key])
        logs = (row["total_enum_log_ops"] + row["total_unit_log_ops"]
                if row["total_enum_log_ops"] is not None and row["total_unit_log_ops"] is not None else None)
        lines.append(f"| {Path(row['file']).name} | {val('work_share_pct')} | {val('log_share_pct')} | {val('total_work_ops')} | {val('total_full_ops')} | {val('init_ops')} | {val('total_refresh_ops')} | {logs if logs is not None else '?'} | {len(row['cursor_samples'])} | {row['unit_progress_regressions']} |")
    lines.extend(["", "| Fichier | Etapes index | Puits indexes | Etapes parcours | Sources closes | Cellules vides | Elagages geometrie | Ops index | Ops parcours |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|"])
    for row in report["files"]:
        val = lambda key: "?" if row.get(key) is None else str(row[key])
        lines.append(f"| {Path(row['file']).name} | {val('index_steps')} | {val('indexed')} | {val('scan_steps')} | {val('sources_advanced')} | {val('cell_skips')} | {val('geo_skips')} | {val('index_ops')} | {val('scan_ops')} |")
    lines.extend(["", *[f"- {limitation}" for limitation in report["limitations"]]])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Fichiers .log/.log.gz ou dossiers")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--expect-off", action="store_true", help="Erreur si trace RLW-04 presente")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args(argv)
    result = summarize(log_paths(args.paths))
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.format == "json" else markdown(result))
    if args.expect_off and result["with_shadow"]:
        return 2
    if args.require_complete and result["complete"] != result["logs"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
