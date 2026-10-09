"""Relate rail_search blocker events to the immediately preceding early audit.

This is observational: a blocked, affordable-looking candidate is not a
counterfactual train. Missing cargo / ambiguous matches remain unmatched.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
from statistics import median

from analyse_rail_freight_dlog import decode_line
from analyse_rail_preastar import LOG_NAME


def _key(values, *, prefix=""):
    return (values.get(prefix + "src"), values.get(prefix + "dst"))


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def process_log(lines, *, file=""):
    audit = None
    current_day = None
    ranks = defaultdict(list)
    blocked = []
    built = []
    counts = Counter()
    for line_no, line in enumerate(lines, 1):
        decoded = decode_line(line)
        if decoded is None:
            continue
        year, month, day, event, data = decoded
        this_day = f"{year:04d}-{month:02d}-{day:02d}"
        if this_day != current_day:
            current_day = this_day
            audit = None
            ranks.clear()
        if event == "RAIL_AUDIT" and data.get("stage") == "early" and data.get("reason") == "search_in_progress":
            audit = {"day": this_day, "kind": data.get("kind"), "cargo": data.get("cargo"),
                     "src": data.get("src"), "dst": data.get("dst"),
                     "rank": data.get("rank"), "line_no": line_no}
        elif event == "PORTFOLIO_RANK" and data.get("mode") == "rail":
            ranks[(data.get("kind"), data.get("cargo"), *_key(data))].append({
                "log_line": line_no, "rank": data.get("rank"), "finance_capital": data.get("finance_capital"),
                "pred_profit": data.get("profit"), "rank_score": data.get("rank_score"),
                "budget_score": data.get("budget_score")})
        elif event == "RAIL_BLOCKER":
            counts["blocker_events"] += 1
            identity = (data.get("requested_kind"), data.get("requested_src"), data.get("requested_dst"))
            a = audit if audit and (audit["kind"], audit["src"], audit["dst"]) == identity and audit["line_no"] == line_no - 1 else None
            if a is None:
                counts["unmatched_early"] += 1
            elif a["cargo"] in (None, "-", ""):
                counts["unmatched_missing_cargo"] += 1
                a = None
            r = ranks.get((a["kind"], a["cargo"], a["src"], a["dst"]), []) if a else []
            if len(r) > 1:
                counts["ambiguous_same_day_rank"] += 1
            row = {"day": this_day, "year": year,
                   "kind": identity[0], "cargo": a["cargo"] if a else None,
                   "src": identity[1], "dst": identity[2],
                   "requested_rank": a["rank"] if a else None,
                   "blocker": data.get("blocker", "unknown"), "phase": data.get("phase", "unknown"),
                   "blocker_src": data.get("src"), "blocker_dst": data.get("dst"),
                   "blocker_age_days": data.get("age_days"), "blocker_spent_iters": data.get("spent"),
                   "blocker_budget_iters": data.get("budget"),
                   "same_od_as_primary_search": data.get("blocker") == "primary" and
                       _key(data) == (identity[1], identity[2]),
                   "score_at_block": data.get("fund_score"),
                   "profit_predicted_at_block": data.get("pred_profit"),
                   "budget_capital_at_block": data.get("budget_capital"),
                   "destination_at_block": data.get("destination"),
                   "score_at_same_day": r[0] if len(r) == 1 else None,
                   "score_match_status": "unique" if len(r) == 1 else ("ambiguous" if len(r) > 1 else "absent"),
                   "source_line": line_no, "early_audit_line": a["line_no"] if a else None,
                   "link_status": "adjacent_exact_kind_src_dst" if a else "unmatched"}
            blocked.append(row)
            audit = None
        elif event == "RAIL_BUILD":
            built.append({"day": this_day, "cargo": data.get("cargo"), "src": data.get("src"),
                          "dst": data.get("dst"), "line": data.get("line"), "source_line": line_no})
    first_by_key = {}
    for event in blocked:
        if event["link_status"] == "unmatched":
            continue
        key = (event["kind"], event["cargo"], event["src"], event["dst"])
        first_by_key.setdefault(key, event)
    for (kind, cargo, src, dst), row in first_by_key.items():
        successes = [x for x in built if (x["cargo"], x["src"], x["dst"]) == (cargo, src, dst)
                     and x["day"] >= row["day"]]
        row["later_build_candidate"] = successes[0] if len(successes) == 1 else None
        row["later_build_status"] = "one_possible_pair_match" if len(successes) == 1 else (
            "ambiguous_multiple" if len(successes) > 1 else "none_rail_build_tag_observed")
    by_year = defaultdict(Counter)
    unique_by_year = defaultdict(lambda: defaultdict(set))
    for ev in blocked:
        y = str(ev["year"])
        by_year[y]["blocker_visits"] += 1
        by_year[y]["by_blocker/" + ev["blocker"]] += 1
        if ev["same_od_as_primary_search"]:
            by_year[y]["self_pair_revisits"] += 1
        else:
            by_year[y]["other_pair_or_upgrade_visits"] += 1
        if ev["cargo"] and ev["kind"]:
            group = ev["kind"] + "/" + ev["cargo"]
            unique_by_year[y][group].add((ev["src"], ev["dst"]))
            by_year[y]["matched_visits"] += 1
            if ev["score_match_status"] == "unique":
                by_year[y]["rank_score_same_day_observed"] += 1
            if ev["score_at_block"] is not None and ev["profit_predicted_at_block"] is not None:
                by_year[y]["score_and_profit_at_block_observed"] += 1
                destination = ev["destination_at_block"] or "unknown"
                by_year[y]["blocked_destination/" + destination] += 1
    for y, kinds in unique_by_year.items():
        by_year[y]["distinct_kind_cargo_od"] = sum(len(v) for v in kinds.values())
    return {"file": file, "coverage": dict(counts),
            "annual": {k: dict(v) for k, v in sorted(by_year.items())},
            "first_blocked_per_kind_cargo_od": [dict(v) for v in first_by_key.values()],
            "blocked_visits": blocked,
            "build_events": built}


COMPACT_COLUMNS = ("arm", "seed", "repeat", "year", "kind", "cargo", "destination",
                   "blocker", "visits", "distinct_od", "same_od_visits", "score_covered",
                   "fund_score_median", "pred_profit_median_gbp_year",
                   "budget_capital_median_gbp")


def compact_rows(report):
    """Observed blocked visits, separating identical OD revisits and distinct pairs."""
    for run in report["runs"]:
        groups = defaultdict(list)
        for row in run["blocked_visits"]:
            if row["link_status"] != "adjacent_exact_kind_src_dst":
                continue
            group = (row["year"], row["kind"], row["cargo"], row["destination_at_block"] or "unknown",
                     row["blocker"])
            groups[group].append(row)
        for (year, kind, cargo, destination, blocker), events in sorted(groups.items()):
            scores = [n for x in events if (n := _float(x["score_at_block"])) is not None and n >= 0]
            profits = [n for x in events if (n := _float(x["profit_predicted_at_block"])) is not None and n >= 0]
            capitals = [n for x in events if (n := _float(x["budget_capital_at_block"])) is not None and n >= 0]
            distinct = {(x["src"], x["dst"]) for x in events if not x["same_od_as_primary_search"]}
            yield {"arm": run["arm"], "seed": run["seed"], "repeat": run["repeat"],
                   "year": year, "kind": kind, "cargo": cargo, "destination": destination,
                   "blocker": blocker, "visits": len(events), "distinct_od": len(distinct),
                   "same_od_visits": sum(x["same_od_as_primary_search"] for x in events),
                   "score_covered": len(scores), "fund_score_median": median(scores) if scores else None,
                   "pred_profit_median_gbp_year": median(profits) if profits else None,
                   "budget_capital_median_gbp": median(capitals) if capitals else None}


def analyse(path):
    files = [path] if path.is_file() else sorted(path.glob("*.log"))
    if not files:
        raise FileNotFoundError(path)
    runs = []
    for file in files:
        match = LOG_NAME.fullmatch(file.name)
        if match is None:
            raise ValueError("unrecognized log filename: " + file.name)
        with file.open(encoding="utf-8", errors="replace") as f:
            run = process_log(f, file=str(file))
        run.update({"seed": int(match["seed"]), "repeat": int(match["repeat"]), "arm": match["arm"]})
        runs.append(run)
    totals = defaultdict(Counter)
    for run in runs:
        for year, counters in run["annual"].items():
            totals[year].update(counters)
    return {"scope": "blocked scheduler visits, not proven profitable projects",
            "matching": "early audit must be adjacent in same log, same day, kind/src/dst",
            "ranked": "fund_score/pred_profit/budget_capital from blocked project if logged; no live cash oracle; fallback unique same-day PORTFOLIO_RANK",
            "annual_total": {year: dict(row) for year, row in sorted(totals.items())},
            "runs": runs}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("engine_dir", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--summary-csv", type=Path)
    args = ap.parse_args(argv)
    report = analyse(args.engine_dir)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    if args.summary_csv:
        with args.summary_csv.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=COMPACT_COLUMNS)
            writer.writeheader()
            writer.writerows(compact_rows(report))


if __name__ == "__main__":
    main()
