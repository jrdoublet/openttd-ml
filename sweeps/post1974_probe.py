"""Read diagnostic OPEX logs without conflating repeated passes with unique OD.

No experiment is launched by this script.  This is descriptive and does NOT
establish the physical viability of rejected projects.  The ``C63`` annual
ledger flushes the *previous* year; missing years stay missing, not zero.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

try:
    from sweeps.diag_c63_c58 import parse_c63_invest, C63_RE
except ImportError:
    from diag_c63_c58 import parse_c63_invest, C63_RE

LOG_RE = re.compile(r"OPEX\s+(\d{4})-(\d{1,2})-(\d{1,2})\s+([A-Z0-9_]+)\s*(.*)$")
KINDS = {"RAIL_ATTEMPT", "RAIL_BUILD", "PROJECT_CHOSEN", "PROJECT_DISCARD", "AIR_BUILD", "FLEET_PROJECT", "AIR_FLEET", "V284", "ESTIM_SPEND", "ESTIM_PASS", "ESTIM_DECISION", "ESTIM_OUTCOME", "C78_SLOT", "V233L_REJECT"}


def fields_of(payload: str) -> dict[str, str]:
    fields = {}
    for item in payload.split():
        if "=" in item:
            k, v = item.split("=", 1)
            fields[k] = v
    return fields


def int_or_none(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def od_key(row, *, ordered=True):
    """Physical origin/destination tiles, not the identity of a project.

    Freight direction is meaningful: GOOD A->B and GOOD B->A must not collapse.
    The undirected view remains an explicit conservative lower bound.
    """
    src, dst = row.get("src"), row.get("dst")
    if src is None or dst is None:
        return None
    pair = (str(src), str(dst))
    if not ordered:
        pair = tuple(sorted(pair))
    return pair


def cross_year_rail_witnesses(records):
    """Join selected RAIL ODs to eventual physical builds; no counterfactual."""
    selected = defaultdict(list)
    attempted = defaultdict(list)
    constructed = defaultdict(list)
    for year, rows in sorted(records.items()):
        for row in rows:
            pair = od_key(row)
            if pair is None:
                continue
            if row["event_kind"] == "PROJECT_CHOSEN" and row.get("mode") == "rail":
                selected[pair].append({
                    "date": row["date"], "kind": row.get("kind"), "cargo": row.get("cargo"),
                    "profit": int_or_none(row.get("profit")),
                    "cost_quote": int_or_none(row.get("cost")),
                })
            elif row["event_kind"] == "RAIL_ATTEMPT":
                attempted[pair].append({
                    "date": row["date"], "kind": row.get("kind"),
                    "ok": row.get("ok") == "1", "reason": row.get("reason"),
                    "actual_paid": int_or_none(row.get("actual")),
                    "profit_at_attempt": int_or_none(row.get("pred_profit")),
                })
            elif row["event_kind"] == "RAIL_BUILD":
                constructed[pair].append({
                    "date": row["date"], "line": int_or_none(row.get("line")),
                    "actual_logged_cost": int_or_none(row.get("cost")),
                })
    witnesses = []
    for pair in sorted(set(selected) | set(attempted) | set(constructed)):
        choices = selected.get(pair, [])
        attempts = attempted.get(pair, [])
        builds = constructed.get(pair, [])
        witnessed = bool(builds) or any(a["ok"] for a in attempts)
        witnesses.append({
            "src": pair[0], "dst": pair[1], "choices": choices,
            "attempts": attempts, "builds": builds,
            "physically_built": witnessed,
            "positive_selected_profit": any((c["profit"] or 0) > 0 for c in choices),
            "actual_success_paid": sum(
                a["actual_paid"] for a in attempts
                if a["ok"] and a["actual_paid"] is not None and a["actual_paid"] >= 0
            ),
            "classification": (
                "build_confirmed" if witnessed else
                "attempt_failed_no_build_proof" if attempts else
                "selected_no_completed_attempt"
            ),
        })
    return witnesses


def cross_year_air_witnesses(records):
    """AIR construction is observable; BUILD cost is model, not paid cash."""
    selected = defaultdict(list)
    built = defaultdict(list)
    for year, rows in sorted(records.items()):
        for row in rows:
            pair = od_key(row)
            if pair is None:
                continue
            if row["event_kind"] == "PROJECT_CHOSEN" and row.get("mode") == "air":
                selected[pair].append({
                    "date": row["date"], "profit": int_or_none(row.get("profit")),
                    "cost_quote": int_or_none(row.get("cost")),
                })
            if row["event_kind"] == "AIR_BUILD":
                built[pair].append({
                    "date": row["date"], "line": row.get("line"),
                    "model_cost": int_or_none(row.get("cost")),
                })
    return [{
        "src": pair[0], "dst": pair[1],
        "choices": selected.get(pair, []), "built": built.get(pair, []),
        "physically_built": bool(built.get(pair)),
    } for pair in sorted(set(selected) | set(built))]


def parse_log(path: Path, *, first=1974, last=1979):
    records = defaultdict(list)
    c63_records = []
    script_errors = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line_no, raw in enumerate(fh, 1):
            if re.search(r"(squirrel.*error|ai script.*crash|script error)", raw, re.IGNORECASE):
                script_errors.append(line_no)
            match = LOG_RE.search(raw)
            if not match:
                continue
            year = int(match.group(1))
            kind = match.group(4)
            if kind == "C63_INVEST":
                if C63_RE.search(raw):
                    c63_records.append(raw.strip())
                continue
            if first <= year <= last and kind in KINDS:
                records[year].append({"line": line_no, "date": f"{year}-{int(match.group(2)):02}-{int(match.group(3)):02}", "event_kind": kind, **fields_of(match.group(5))})
    c63 = parse_c63_invest("\n".join(c63_records))
    annual = {}
    for year in range(first, last + 1):
        rows = records[year]
        counts = Counter(r["event_kind"] for r in rows)
        rail = [r for r in rows if r["event_kind"] == "RAIL_ATTEMPT"]
        rail_built = [r for r in rows if r["event_kind"] == "RAIL_BUILD"]
        chosen = [r for r in rows if r["event_kind"] == "PROJECT_CHOSEN"]
        air_built = [r for r in rows if r["event_kind"] == "AIR_BUILD"]
        discard = [r for r in rows if r["event_kind"] == "PROJECT_DISCARD"]
        # RAIL_ATTEMPT lacks cargo; (src,dst,kind) is a lower bound on
        # distinct OD/cargo projects. Directed and undirected are separate.
        rail_od = sorted({(*od_key(r), r.get("kind", "?"))
                          for r in rail if od_key(r) is not None})
        rail_undirected = sorted({(*od_key(r, ordered=False), r.get("kind", "?"))
                                  for r in rail if od_key(r) is not None})
        air_od = sorted({od_key(r) for r in air_built if od_key(r) is not None})
        chosen_od = {(
            r.get("mode", "?"), *od_key(r), r.get("kind", "?"), r.get("cargo", "?"),
        ) for r in chosen if od_key(r) is not None}
        discarded_od_reasons = {(
            r.get("mode", "?"), *od_key(r), r.get("reason", "?"),
        ) for r in discard if od_key(r) is not None}
        by_mode = Counter(r.get("mode", "unknown") for r in chosen)
        paid_rail = [int_or_none(r.get("actual")) for r in rail if r.get("ok") == "1"]
        paid_rail = [x for x in paid_rail if x is not None and x >= 0]
        c63_year = c63.get(year)
        slot = [r for r in rows if r["event_kind"] == "C78_SLOT"]
        pass_rows = [r for r in slot if r.get("phase") == "projects_pass"]
        long_reject = [r for r in rows if r["event_kind"] == "V233L_REJECT"]
        mature = {}
        if c63_year is not None:
            for mode in ("rail", "air", "fleet"):
                lines = [line for line in c63_year["lines"] if line["mode"] == mode and line["age"] >= 2]
                mature[mode] = {
                    "n": len(lines),
                    "pred_p": sum(line["pred_p"] for line in lines),
                    "real_p": sum(line["real_p"] for line in lines),
                    "losing_n": sum(line["real_p"] < 0 for line in lines),
                }
        annual[str(year)] = {
            "event_counts": dict(counts),
            "rail_attempt_events": len(rail),
            "rail_build_events": len(rail_built),
            "rail_min_distinct_od_kind": len(rail_od),
            "rail_undirected_min_distinct_od_kind": len(rail_undirected),
            "rail_reason_counts": dict(Counter(r.get("reason", "unlogged") for r in rail)),
            "rail_kind_counts": dict(Counter(r.get("kind", "unlogged") for r in rail)),
            "rail_success_actual_paid_observed": sum(paid_rail),
            "rail_success_paid_observed_n": len(paid_rail),
            "air_build_events": len(air_built),
            "air_min_distinct_od": len(air_od),
            "chosen_events_by_mode": dict(by_mode),
            "chosen_unique_od_mode_kind_cargo": len(chosen_od),
            "discarded_unique_od_mode_kind_reason": len(discarded_od_reasons),
            "chosen_offers": [{
                "date": r["date"], "mode": r.get("mode"), "kind": r.get("kind"),
                "cargo": r.get("cargo"), "src": r.get("src"), "dst": r.get("dst"),
                "profit": int_or_none(r.get("profit")),
                "cost_quote": int_or_none(r.get("cost")),
            } for r in chosen],
            "rail_attempt_details": [{
                "date": r["date"], "kind": r.get("kind"), "src": r.get("src"),
                "dst": r.get("dst"), "reason": r.get("reason"),
                "ok": r.get("ok") == "1",
                "pred_profit": int_or_none(r.get("pred_profit")),
                "quote": int_or_none(r.get("quote")),
                "actual": int_or_none(r.get("actual")),
                "iterations": int_or_none(r.get("iters")),
                "opcodes": int_or_none(r.get("ops")),
            } for r in rail],
            "discard_events_by_mode_reason": dict(Counter(r.get("mode", "unknown") + ":" + r.get("reason", "unlogged") for r in discard)),
            "v284_events_by_action": dict(Counter(r.get("action", "unknown") for r in rows if r["event_kind"] == "V284")),
            "fleet_events_by_action": dict(Counter(r["event_kind"] + ":" + r.get("action", "unknown") for r in rows if r["event_kind"] in {"FLEET_PROJECT", "AIR_FLEET"})),
            "c78_limited_trace": {
                "first": min((r["date"] for r in slot), default=None),
                "last": max((r["date"] for r in slot), default=None),
                "projects_pass_events": len(pass_rows),
                "passes_no_air_candidates": sum(r.get("air_candidates") == "0" for r in pass_rows),
                "passes_with_air_candidates": sum(int_or_none(r.get("air_candidates")) not in (None, 0) for r in pass_rows),
                "pass_stop_reasons": dict(Counter(r.get("reason", "?") for r in slot if r.get("phase") == "pass_stop")),
                "cash_available_min": min((a for r in pass_rows if (a := int_or_none(r.get("available"))) is not None), default=None),
                "cash_available_max": max((a for r in pass_rows if (a := int_or_none(r.get("available"))) is not None), default=None),
            },
            "v233l_reject_event_reasons": dict(Counter(r.get("reason", "?") for r in long_reject)),
            "v233l_reject_distinct_od": len({od_key(r) for r in long_reject if od_key(r) is not None}),
            "c63_available": c63_year is not None,
            "c63_spend_by_mode": c63_year["spend"] if c63_year is not None else None,
            "c63_opportunities": c63_year["opp"] if c63_year is not None else None,
            "c63_absent_subcauses": c63_year["absent_causes"] if c63_year is not None else None,
            "c63_mature_lines_by_mode": mature if c63_year is not None else None,
            "c63_empty_probe_causes": dict(Counter(p["cause"] for p in c63_year["empty_probes"])) if c63_year is not None else None,
            "c63_lines": c63_year["lines"] if c63_year is not None else None,
        }
    return {
        "log_path": str(path), "years": annual,
        "rail_crossyear_witnesses": cross_year_rail_witnesses(records),
        "air_crossyear_witnesses": cross_year_air_witnesses(records),
        "script_error_line_numbers": script_errors,
        "limitations": [
            "Single instrumented seed, not representative nor a controlled economic duel",
            "Not all rejected projects log their OD; RAIL_ATTEMPT lacks cargo; OD-kind is a lower bound",
            "C63 invalid is residual, not proof of unbuildable site",
            "ESTIM decision trace limited in code to 1973-1975",
            "Missing C63 flush at end of 1979 is censored, not zero spend/opportunities",
            "No rejected project is certified physically buildable from this log alone",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    data = parse_log(args.log)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for y, row in data["years"].items():
        print(y, "rail", row["rail_attempt_events"], "rail OD-kind>=", row["rail_min_distinct_od_kind"], "AIR builds", row["air_build_events"], "C63", row["c63_available"])


if __name__ == "__main__":
    main()
