#!/usr/bin/env python3
"""AIR BFAIL : pression de financement suivant la conservation de A.

Diagnostic observationnel. Le budget de sélection est une variable du
portefeuille, pas un solde de caisse. Ajouter le coût historique de A à ce
budget est uniquement un test de sensibilité statique, jamais une simulation
de destruction, d'évitement du chantier ou de profit contrefactuel.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path, PureWindowsPath
import re

from analyse_air_orphan_profit import iso
from parse_air_finance_margin import clean_log_line, parse_kv_payload, parse_log_filename


TOKENS = re.compile(r"\b(AIR_ORPHAN_RETAIN|AIR_FINANCE_TRY|AIR_FINANCE_SELECT)\b\s*(.*)$")
NUMERIC = ("budget", "air", "blocked_margin", "blocked_capital", "blk_finance")


def log_events(lines):
    out = []
    warnings = []
    for line_no, raw in enumerate(lines, 1):
        match = TOKENS.search(clean_log_line(raw))
        if not match:
            continue
        kind = match.group(1)
        kv = parse_kv_payload(match.group(2))
        if len(re.findall(r"\b[A-Za-z0-9_]+\s*=", match.group(2))) != len(kv):
            warnings.append({"code": "duplicate_field", "line": line_no})
            continue
        out.append({"kind": kind, "kv": kv, "line": line_no})
    return out, warnings


def integer(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def find_failure(events, orphan):
    """Verify retained A with the actual failed build from the same log."""
    at = orphan["log_line"]
    origins = [e for e in events if e["line"] == at and e["kind"] == "AIR_ORPHAN_RETAIN"]
    if len(origins) != 1:
        return None, "missing_origin_log_line"
    origin = origins[0]
    kv = origin["kv"]
    if (integer(kv.get("anchor")) != orphan["anchor"]
            or integer(kv.get("station")) != orphan["station"]
            or integer(kv.get("date")) != orphan["date"]
            or integer(kv.get("cost_a")) != orphan["cost_a_gbp"]):
        return None, "origin_mismatch"
    # Probe AIR_ORPHAN_RETAIN is emitted inside the builder immediately
    # before its caller emits AIR_FINANCE_TRY; other logs may interleave.
    following = [e for e in events if e["kind"] == "AIR_FINANCE_TRY"
                 and at < e["line"] <= at + 12]
    matching = [e for e in following if e["kv"].get("reason") == "BFAIL"
                and e["kv"].get("outcome") == "failed"
                and e["kv"].get("orphan_kept") == "1"
                and e["kv"].get("date") == iso(orphan["date"])
                and integer(e["kv"].get("actual")) == orphan["total_build_cost_gbp"]]
    if len(matching) != 1:
        return None, "failed_try_missing_or_ambiguous"
    match = matching[0]
    if integer(match["kv"].get("cash")) is None:
        return None, "cash_missing"
    return match, None


def next_selection(events, failure, orphan):
    next_builds = [e for e in events if e["kind"] == "AIR_FINANCE_TRY"
                   and e["line"] > failure["line"]
                   and e["kv"].get("outcome") == "built"]
    first_build_line = min((e["line"] for e in next_builds), default=None)
    for e in events:
        if e["kind"] != "AIR_FINANCE_SELECT" or e["line"] <= failure["line"]:
            continue
        if first_build_line is not None and e["line"] >= first_build_line:
            return None, "other_build_before_selection"
        kv = e["kv"]
        try:
            day = date.fromisoformat(kv.get("date", ""))
        except ValueError:
            return None, "invalid_selection_date"
        lag = (day - date.fromisoformat(iso(orphan["date"]))).days
        if lag < 0:
            return None, "regressive_selection_date"
        if lag > 7:
            return None, "no_selection_within_seven_days"
        if any(integer(kv.get(k)) is None for k in NUMERIC[:4]):
            return None, "missing_selection_fields"
        if integer(kv.get("blocked_margin")) > 0 and integer(kv.get("blk_finance")) is None:
            return None, "missing_blocked_finance"
        return {"lag_days": lag, "line": e["line"], **kv}, None
    return None, "no_subsequent_selection"


def analyze_run(log_path, run):
    meta = parse_log_filename(log_path.name)
    if (meta["seed"], meta["arm"], meta["repeat"]) != (run["seed"], run["arm"], run["repeat"]):
        raise ValueError(f"log identity mismatch: {log_path}")
    with log_path.open(encoding="utf-8", errors="replace") as stream:
        events, warnings = log_events(stream)
    records = []
    for orphan in run["orphans"]:
        fail, fail_err = find_failure(events, orphan)
        select, select_err = next_selection(events, fail, orphan) if fail else (None, None)
        rec = {"seed": run["seed"], "arm": run["arm"], "repeat": run["repeat"],
               "date": iso(orphan["date"]), "anchor": orphan["anchor"],
               "station": orphan["station"], "status": orphan["status"],
               "first_reuse_line": orphan["first_reuse_line"],
               "cost_a_historical_gbp": orphan["cost_a_gbp"],
               "failed_build_total_gbp": orphan["total_build_cost_gbp"],
               "failure_match_status": fail_err or "matched",
               "selection_match_status": select_err if fail else "failure_unmatched"}
        if fail:
            cash = integer(fail["kv"]["cash"])
            rec["cash_before_failure_gbp"] = cash
            rec["cash_after_failed_build_proxy_gbp"] = cash - orphan["total_build_cost_gbp"]
            rec["failure_log_line"] = fail["line"]
        if select:
            budget = integer(select["budget"])
            blocked = integer(select["blocked_margin"])
            finance = integer(select.get("blk_finance"))
            deficit = finance - budget if blocked and finance is not None else None
            crossing = (deficit <= orphan["cost_a_gbp"]
                        if deficit is not None and deficit > 0 else None)
            rec.update(selection_match_status="matched", selection_lag_days=select["lag_days"],
                       selection_budget_gbp=budget,
                       selected_top_mode=select.get("top_mode"),
                       selection_air_candidates=integer(select["air"]),
                       margin_blocked_count=blocked,
                       capital_blocked_count=integer(select["blocked_capital"]),
                       best_margin_blocked_finance_gbp=finance if blocked else None,
                       best_margin_blocked_deficit_gbp=deficit,
                       static_avoided_a_cost_covers_deficit=crossing,
                       static_same_day_margin_crossing=(crossing if select["lag_days"] == 0 else None))
        records.append(rec)
    return records, warnings


def analyze(orphans_file, logs_dir):
    data = json.loads(Path(orphans_file).read_text(encoding="utf-8"))
    records, warnings = [], []
    observed = set()
    for run in data["runs"]:
        if not run["orphans"]:
            continue
        filename = PureWindowsPath(run["file"]).name
        path = Path(logs_dir) / filename
        if not path.is_file() or filename in observed:
            raise ValueError(f"missing or duplicated log: {filename}")
        observed.add(filename)
        rs, ws = analyze_run(path, run)
        records.extend(rs)
        warnings.extend({"file": filename, **w} for w in ws)
    status = Counter(r["selection_match_status"] for r in records)
    return {"source_orphans": str(orphans_file), "source_logs": str(logs_dir),
            "interpretation": "static financing sensitivity only; no counterfactual outcome",
            "records": sorted(records, key=lambda r: (r["seed"], r["date"], r["station"])),
            "summary": {"orphans": len(records), "historical_cost_a_gbp": sum(
                r["cost_a_historical_gbp"] for r in records),
                "selection_status_counts": dict(status),
                "matched_margin_blocked": sum(r.get("margin_blocked_count", 0) > 0 for r in records),
                "same_day_selection_count": sum(r.get("selection_lag_days") == 0 for r in records),
                "same_day_margin_crossings": sum(r.get("static_same_day_margin_crossing") is True for r in records),
                "delayed_static_margin_crossings": sum(r.get("selection_lag_days", 0) > 0
                    and r.get("static_avoided_a_cost_covers_deficit") is True for r in records)},
            "warnings": warnings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orphans", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args(argv)
    result = analyze(args.orphans, args.logs)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
