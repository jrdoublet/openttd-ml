#!/usr/bin/env python3
"""Funnel rail observationnel : projets OD, passages et recherches RID séparés.

Les comptes par étape ne sont PAS un funnel causal de projets reliés : le seul
appariement strict disponible dans les logs PREASTAR est START/END/BUILD par RID.
Tout passage d'une autre étape vers un RID reste explicitement unmatched.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date
import json
from pathlib import Path

from analyse_rail_preastar import LOG_NAME, analyse as analyse_preastar
from analyse_rail_freight_dlog import decode_line


def _number(value, default=None):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _identity(kind, cargo, src, dst):
    if not kind or not cargo or not src or not dst:
        return None
    if src == "-1" or dst == "-1":
        return None
    if kind == "pax" and int(src) > int(dst):
        src, dst = dst, src
    return kind, cargo, src, dst


def parse_diagnostic_log(lines):
    """Une partie : conservez événements et OD distincts sans simuler d'appariement."""
    counts = defaultdict(Counter)
    pairs = defaultdict(lambda: defaultdict(set))
    events = []
    coverage = Counter()
    invalid = Counter()
    for lineno, line in enumerate(lines, 1):
        decoded = decode_line(line)
        if decoded is None:
            continue
        year, month, day, tag, fields = decoded
        if year < 1970 or year > 2100:
            invalid["year_outside_range"] += 1
            continue
        if tag not in ("RAIL_AUDIT", "RAIL_ATTEMPT", "PROJECT_CHOSEN",
                       "PORTFOLIO_RANK", "RAIL_PREPAIR", "VIVIER_GEN",
                       "RAIL_FREIGHT_SELECT_SHADOW", "RAIL_POOL_AUDIT",
                       "RAIL_BUILD", "PROJECT_DISCARD", "RAIL_BLOCKER"):
            continue
        coverage[tag] += 1
        counts[year]["events/" + tag] += 1
        kind = fields.get("kind")
        cargo = fields.get("cargo")
        src, dst = fields.get("src"), fields.get("dst")
        identity = _identity(kind, cargo, src, dst)
        if tag in ("PROJECT_CHOSEN", "PORTFOLIO_RANK") and fields.get("mode") != "rail":
            continue
        if tag == "PROJECT_CHOSEN":
            if kind not in ("pax", "freight"):
                invalid["chosen_kind"] += 1
                continue
            phase = "chosen"
        elif tag == "PORTFOLIO_RANK":
            if kind not in ("pax", "freight"):
                continue
            phase = "ranked_top5"
        elif tag == "RAIL_ATTEMPT":
            # Historical event lacks cargo: never silently join it to CHOSEN.
            if kind not in ("pax", "freight"):
                invalid["attempt_kind"] += 1
                continue
            cargo = "unknown"
            identity = _identity(kind, cargo, src, dst)
            phase = "attempt_no_cargo"
        elif tag == "RAIL_AUDIT":
            if fields.get("stage") not in ("attempt", "precheck", "dispatch", "early"):
                invalid["audit_stage"] += 1
                continue
            phase = "audit_" + fields["stage"]
        elif tag == "RAIL_BUILD":
            # Le log ne contient pas kind ; freight plausible si non PASS/MAIL,
            # mais aucun type n'est inventé sans information supplémentaire.
            kind = "unknown"
            identity = None
            phase = "rail_build"
        else:
            phase = tag.lower()
        if kind in ("pax", "freight"):
            grouping = (year, kind, cargo or "unknown", "destination_unknown")
            counts[grouping][phase + "/visits"] += 1
            if identity:
                pairs[grouping][phase].add(identity)
            elif phase in ("chosen", "ranked_top5", "attempt_no_cargo", "audit_attempt", "rail_build"):
                counts[grouping][phase + "/unidentified"] += 1
        if tag in ("RAIL_AUDIT", "RAIL_ATTEMPT"):
            reason = fields.get("reason", "unknown")
            counts[year][phase + "/" + reason] += 1
            if tag == "RAIL_AUDIT" and fields.get("stage") == "attempt":
                counts[year]["audit_attempt_actual_gbp"] += _number(fields.get("actual"), 0)
                counts[year]["audit_attempt_opcodes"] += _number(fields.get("ops"), 0)
        if tag == "RAIL_BUILD":
            counts[year]["rail_build/events_kind_unknown"] += 1
            counts[year]["rail_build/actual_gbp"] += _number(fields.get("cost"), 0)
            counts[year]["rail_build/cargo_" + (cargo or "unknown")] += 1
        if tag == "RAIL_PREPAIR":
            # Paire examinée / rejetée dans une génération, sans identité OD.
            cargo_ref = fields.get("freight_cargo", "unknown")
            for key in ("freight_ind_pairs", "freight_town_pairs", "freight_town_zero_monthly",
                        "freight_target_skip", "freight_abandon_skip", "freight_sources"):
                value = _number(fields.get(key))
                if value is not None:
                    counts[year]["prepair/" + key] += value
            for suffix, destination in (("freight_ind_pairs", "industry"),
                                         ("freight_town_pairs", "town")):
                value = _number(fields.get(suffix))
                if value is not None:
                    # -1 signifie plusieurs cargos à la même génération.
                    cg = f"cargo_id_{cargo_ref}" if cargo_ref != "-1" else "cargo_mix_unresolved"
                    counts[(year, "freight", cg, destination)]["pairs_examined_visits"] += value
                    counts[(year, "freight", cg, destination)]["generation_calls"] += 1
        if tag == "RAIL_FREIGHT_SELECT_SHADOW":
            # Passages de re-classement ; le cargo n'est pas exposé.
            for key in ("total_f", "cash_f", "floor_f", "eligible_f", "selected_f",
                        "town_f", "eligible_town_f", "selected_town_f"):
                value = _number(fields.get(key))
                if value is not None:
                    counts[year]["select/" + key] += value
            if _number(fields.get("eligible_f"), 0) > 0:
                counts[year]["select/calls_with_eligible_freight"] += 1
                if _number(fields.get("selected_f"), 0) == 0:
                    counts[year]["select/calls_eligible_but_not_selected"] += 1
                counts[year]["select/head_" + fields.get("head_mode", "unknown")] += 1
        if tag == "PROJECT_CHOSEN" and identity:
            events.append({"date": f"{year:04d}-{month:02d}-{day:02d}", "phase": "chosen",
                           "kind": kind, "cargo": cargo, "src": src, "dst": dst,
                           "profit_predicted_gbp_year": _number(fields.get("profit")),
                           "capital_predicted_gbp": _number(fields.get("cost")),
                           "rank": _number(fields.get("rank")), "log_line": lineno})
        if tag == "RAIL_AUDIT" and fields.get("stage") == "attempt" and identity:
            events.append({"date": f"{year:04d}-{month:02d}-{day:02d}", "phase": "attempt",
                           "kind": kind, "cargo": cargo, "src": src, "dst": dst,
                           "reason": fields.get("reason"),
                           "actual_gbp": _number(fields.get("actual")),
                           "opcodes": _number(fields.get("ops")), "log_line": lineno})
    by_group = {}
    for group, values in counts.items():
        if not isinstance(group, tuple):
            continue
        year, kind, cargo, destination = group
        key = f"{year}/{kind}/{cargo}/{destination}"
        by_group[key] = {**dict(values), **{
            f"{phase}/distinct_od": len(identities)
            for phase, identities in pairs[group].items()}}
    return {"annual": {str(y): dict(c) for y, c in counts.items() if isinstance(y, int)},
            "by_year_kind_cargo_destination": by_group,
            "events": events, "coverage": dict(coverage), "invalid": dict(invalid)}


def _days(first, last):
    try:
        return (date.fromisoformat(last) - date.fromisoformat(first)).days
    except (ValueError, TypeError):
        return None


def build_report(directory: Path):
    logs = sorted(directory.glob("*.log")) if directory.is_dir() else [directory]
    if not logs or not all(path.is_file() for path in logs):
        raise FileNotFoundError(directory)
    preastar = analyse_preastar(directory)
    pre_by_run = defaultdict(list)
    for row in preastar["attempts"]:
        pre_by_run[(row["arm"], row["seed"], row["repeat"])].append(row)
    runs = []
    rid_detail = []
    for path in logs:
        m = LOG_NAME.fullmatch(path.name)
        if not m:
            raise ValueError(f"unrecognized log filename: {path}")
        arm, seed, repeat = m["arm"], int(m["seed"]), int(m["repeat"])
        with path.open(encoding="utf-8", errors="replace") as handle:
            parsed = parse_diagnostic_log(handle)
        run = {"file": str(path), "arm": arm, "seed": seed, "repeat": repeat,
               **parsed, "preastar": {}}
        annual = defaultdict(Counter)
        for search in pre_by_run[(arm, seed, repeat)]:
            mode, kind, cargo = search["mode"], search["kind"], search["cargo"]
            year = search["start_date"][:4] if search["start_date"] else "unknown"
            bucket = annual[year]
            bucket[mode + "/start"] += 1
            bucket[mode + "/" + search["search_class"]] += 1
            terminal = [e for e in search["build_history"] if e["status"] in ("built", "failed", "expired", "dropped")]
            if terminal:
                bucket[mode + "/build_" + terminal[-1]["status"]] += 1
            elif search["build_history"]:
                bucket[mode + "/last_" + search["build_history"][-1]["status"]] += 1
            else:
                bucket[mode + "/no_build_record"] += 1
            if search["iters"] is not None:
                bucket[mode + "/iters_completed"] += search["iters"]
            if mode == "primary" and kind in ("freight", "pax") and year.isdecimal():
                name = f"{year}/{kind}/{cargo}/destination_unknown"
                by_group = run["by_year_kind_cargo_destination"].setdefault(name, {})
                by_group["primary_rid/start"] = by_group.get("primary_rid/start", 0) + 1
                by_group["primary_rid/" + search["search_class"]] = by_group.get("primary_rid/" + search["search_class"], 0) + 1
                if terminal:
                    name2 = "primary_rid/build_" + terminal[-1]["status"]
                    by_group[name2] = by_group.get(name2, 0) + 1
            rid_detail.append({"arm": arm, "seed": seed, "repeat": repeat, "rid": search["rid"],
                               "mode": mode, "kind": kind, "cargo": cargo, "src": search["src"],
                               "dst": search["dst"], "start": search["start_date"], "end": search["end_date"],
                               "age_days": _days(search["start_date"], search["end_date"]),
                               "outcome": search["search_class"], "iters": search["iters"],
                               "budget": search["budget"], "status": search["status"],
                               "build_events": search["build_history"],
                               "upstream_link_status": "unmatched_no_shared_project_id"})
        run["preastar"] = {key: dict(value) for key, value in sorted(annual.items())}
        runs.append(run)
    return {"scope": "observational_only", "identity_rule": "run+RID for A*; kind+cargo+src+dst only a pair key",
            "unmatched_between_chosen_attempt_search": True,
            "destination_kind_coverage": "unknown_per_project; PREPAIR aggregates only",
            "profit_observed_coverage": "not in engine event logs; use same-run line telemetry separately",
            "preastar_summary": preastar["summary"], "preastar_warnings": preastar["warnings"],
            "runs": runs, "rid_detail": rid_detail}


FUNNEL_COLUMNS = ("arm", "seed", "repeat", "year", "kind", "cargo", "destination_kind",
                  "chosen/visits", "chosen/distinct_od", "ranked_top5/visits",
                  "ranked_top5/distinct_od", "audit_attempt/visits",
                  "audit_attempt/distinct_od", "audit_attempt/unidentified",
                  "audit_dispatch/visits", "audit_precheck/visits", "audit_early/visits",
                  "primary_rid/start", "primary_rid/ok", "primary_rid/cap_abnd",
                  "primary_rid/nopa", "primary_rid/unknown", "primary_rid/build_built",
                  "primary_rid/build_failed", "pairs_examined_visits", "generation_calls")


def funnel_rows(report):
    for run in report["runs"]:
        for key, counters in sorted(run["by_year_kind_cargo_destination"].items()):
            year, kind, cargo, destination = key.split("/", 3)
            if int(year) < 1972 or int(year) > 1975:
                continue
            row = {"arm": run["arm"], "seed": run["seed"], "repeat": run["repeat"],
                   "year": year, "kind": kind, "cargo": cargo,
                   "destination_kind": destination}
            for column in FUNNEL_COLUMNS[7:]:
                # Missing key is unknown coverage, not zero.
                row[column] = counters.get(column)
            yield row


def save_csv(path, rows, headers):
    with Path(path).open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("engine_dir", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--funnel-csv", type=Path)
    ap.add_argument("--rid-csv", type=Path)
    args = ap.parse_args(argv)
    report = build_report(args.engine_dir)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    if args.funnel_csv:
        save_csv(args.funnel_csv, funnel_rows(report), FUNNEL_COLUMNS)
    if args.rid_csv:
        fields = ("arm", "seed", "repeat", "rid", "mode", "kind", "cargo", "src", "dst",
                  "start", "end", "age_days", "outcome", "iters", "budget", "status",
                  "upstream_link_status")
        save_csv(args.rid_csv, report["rid_detail"], fields)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
