#!/usr/bin/env python3
"""Analyse stricte des journaux P4_FLIP : couverture, C77, OD et tentatives.

Usage: python -X utf8 sweeps/analyse_scores_p4_flip_logs_20261013.py
       --engine-dir results/<campaign>_engine --out results/<campaign>_flip_analysis.json
Ce script ne transforme pas un changement de tete en construction prouvee.
"""

import argparse
import collections
import json
import re
from pathlib import Path

MARKER = re.compile(r"\bP4_FLIP_(FACTOR|SUMMARY|HEAD|ATTEMPT|CONTRACT)\s+")
FIELD = re.compile(r"([A-Za-z][A-Za-z_0-9]*)=([^\s]+)")
NAME = re.compile(r"^(?P<policy>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log$")


def fields(line):
    match = MARKER.search(line)
    if not match:
        return None
    return match.group(1), dict(FIELD.findall(line[match.end():]))


def identity(key):
    """Projet OD/cargo/kind sans confondre moteur/plan ou transport."""
    parts = key.split("/")
    return tuple(parts[:5]) if len(parts) >= 5 else None


def analyze_file(path):
    data = {"summaries": [], "factors": [], "heads": [], "attempts": [],
            "contracts": [], "errors": []}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parsed = fields(line)
        if not parsed:
            continue
        kind, row = parsed
        data[{"FACTOR": "factors", "SUMMARY": "summaries", "HEAD": "heads",
              "ATTEMPT": "attempts", "CONTRACT": "contracts"}[kind]].append(row)
    years = set()
    for row in data["summaries"]:
        year = int(row["report_year"])
        if year in years:
            data["errors"].append(f"duplicate report year {year}")
        years.add(year)
        selects = int(row["selects"])
        coverage = sum(int(row[field]) for field in ("verified", "skipped", "mismatch"))
        if coverage != selects:
            data["errors"].append(f"coverage year {year} {coverage}!={selects}")
        if int(row["mismatch"]) > 0:
            data["errors"].append(f"mismatch year {year}: {row['mismatch']}")
    head_ids = set()
    for row in data["heads"]:
        key = row.get("id")
        if key in head_ids:
            data["errors"].append(f"duplicate head id {key}")
        head_ids.add(key)
        if row.get("tier") is None:
            data["errors"].append(f"missing C77 for {key}")
        try:
            budget = float(row["budget"])
            lf, sf = float(row["legacy_finance"]), float(row["stable_finance"])
            if lf > budget or sf > budget:
                data["errors"].append(f"unaffordable flip id {key}: {lf}, {sf}, {budget}")
        except (KeyError, ValueError):
            data["errors"].append(f"invalid finance fields for {key}")
        row["legacy_od"] = identity(row.get("legacy", ""))
        row["stable_od"] = identity(row.get("stable", ""))
        row["distinct_service"] = row["legacy_od"] != row["stable_od"]
        row["cross_mode"] = ((row["legacy_od"] or ("",))[0]
                             != (row["stable_od"] or ("",))[0])
    for row in data["attempts"]:
        if row.get("id") not in head_ids:
            data["errors"].append(f"unmatched attempt id {row.get('id')}")
    # Les jeux s'arretent en decembre 1974, mais le dernier rapport C70 est
    # en janvier 1974 : les evenements du reste de 1974 ne peuvent figurer
    # dans un P4_FLIP_SUMMARY, meme si leurs HEAD/ATTEMPT existent dans le log.
    last_report = max(years) if years else -1
    tail_heads = sum(int(x.get("year", "-1")) >= last_report for x in data["heads"])
    tail_attempts = sum(int(x.get("year", "-1")) >= last_report for x in data["attempts"])
    annual_heads = sum(int(x["head_changes"]) for x in data["summaries"])
    annual_attempts = sum(int(x["attempts"]) for x in data["summaries"])
    if len(data["heads"]) != annual_heads + tail_heads:
        data["errors"].append("heads missing from annual summaries outside expected final-year tail")
    if len(data["attempts"]) != annual_attempts + tail_attempts:
        data["errors"].append("attempts missing from annual summaries outside expected final-year tail")
    data["totals"] = {f: sum(int(x[f]) for x in data["summaries"])
                      for f in ("selects", "verified", "skipped", "mismatch",
                                "head_changes", "attempts")}
    data["totals"]["cross_mode_flips"] = sum(bool(x["cross_mode"]) for x in data["heads"])
    data["totals"]["distinct_service_flips"] = sum(bool(x["distinct_service"]) for x in data["heads"])
    data["totals"]["head_events_in_log"] = len(data["heads"])
    data["totals"]["attempt_events_in_log"] = len(data["attempts"])
    data["totals"]["tail_head_events_unreported"] = tail_heads
    data["totals"]["tail_attempt_events_unreported"] = tail_attempts
    data["head_years"] = dict(sorted(collections.Counter(
        str(x.get("year")) for x in data["heads"]).items()))
    data["factor_exposure"] = dict(sorted(collections.Counter(
        str(x.get("mode")) for x in data["factors"]
        if abs(float(x.get("legacy_k", "1")) - float(x.get("stable_k", "1"))) > 1e-9
    ).items()))
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    records = {}
    for path in sorted(args.engine_dir.glob("*.log")):
        match = NAME.match(path.name)
        if not match:
            continue
        key = f"{match.group('policy')}:s{match.group('seed')}:r{match.group('repeat')}"
        records[key] = analyze_file(path)
    if not records:
        raise SystemExit(f"no supported logs under {args.engine_dir}")
    totals = {field: sum(r["totals"][field] for r in records.values())
              for field in next(iter(records.values()))["totals"]}
    summary = {
        "engine_dir": str(args.engine_dir), "files": len(records),
        "totals": totals,
        "errors": {k: r["errors"] for k, r in records.items() if r["errors"]},
        "per_game": records,
        "interpretation": "C77 same-tier, same-budget replay only. ATTEMPT != BUILD; probe overhead perturbs VM.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print("log_files", summary["files"], "totals", json.dumps(totals))
    for key, record in records.items():
        print(key, "totals", record["totals"], "years", record["head_years"],
              "errors", record["errors"])
    print("analysis", args.out)
    if summary["errors"]:
        raise SystemExit("ERROR: diagnostic contract violated or missing annual reports")


if __name__ == "__main__":
    main()
