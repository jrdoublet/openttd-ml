"""Passive rail freight/passenger inventory from a frozen line-telemetry report.

Read-only post-processing of an existing benchmark JSON, with no NoAI changes.
CargoIDs 0 (PASS) and 2 (MAIL) are for the standard temperate game used by
the frozen shared-map harness; non-PASS/MAIL cargo is reported as freight.
Mixed trains/lines are kept separate, never assigned to a freight total.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path


def rail_line_classification(line, passenger="0", mail="2"):
    caps = line.get("capacity_by_cargo") or {}
    cargo = {str(k) for k, value in caps.items() if isinstance(value, (int, float)) and value > 0}
    if not cargo:
        return "unknown"
    if cargo == {passenger}:
        return "passenger"
    if cargo == {mail}:
        return "mail"
    if passenger not in cargo and mail not in cargo:
        return "freight"
    return "mixed"


def analyse(report, policy="reference", passenger="0", mail="2"):
    snapshots = ((report.get("line_telemetry") or {}).get("snapshots") or [])
    latest = {}
    for snap in snapshots:
        date = str(snap.get("date") or "")
        if snap.get("duel_policy_id") != policy or len(date) < 7 or date[5:7] != "12":
            continue
        if snap.get("arm") not in ("OpexAI", "AAAHogEx"):
            continue
        key = (int(date[:4]), int(snap["seed"]), snap["arm"])
        if key not in latest or date > str(latest[key].get("date") or ""):
            latest[key] = snap

    by_year = defaultdict(list)
    for (year, seed, arm), snap in sorted(latest.items()):
        classes = ("passenger", "mail", "freight", "mixed", "unknown")
        vehicles = {key: 0 for key in classes}
        lines = {key: 0 for key in classes}
        profits = {key: 0.0 for key in classes}
        for line in snap.get("lines") or []:
            if line.get("mode") != "rail":
                continue
            kind = rail_line_classification(line, passenger=passenger, mail=mail)
            vehicles[kind] += int(line.get("vehicles") or 0)
            lines[kind] += 1
            profits[kind] += float(line.get("profit_this_year_gbp") or 0)
        unresolved = snap.get("unresolved_vehicles") or []
        by_year[(year, arm)].append({
            "year": year,
            "arm": arm,
            "seed": seed,
            "date": snap.get("date"),
            "telemetry_ok": snap.get("ok") is True,
            "rail_vehicles": vehicles,
            "rail_lines": lines,
            "rail_profit_ytd_gbp": profits,
            "unresolved_rail_vehicles": sum(item.get("mode") in ("rail", None) for item in unresolved),
        })

    annual = []
    for (year, arm), rows in sorted(by_year.items()):
        n = len(rows)
        classes = ("passenger", "mail", "freight", "mixed", "unknown")
        annual.append({
            "year": year,
            "arm": arm,
            "samples": n,
            "seeds": sorted(row["seed"] for row in rows),
            "complete_snapshots": sum(row["telemetry_ok"] for row in rows),
            "unresolved_rail_vehicles": sum(row["unresolved_rail_vehicles"] for row in rows),
            "mean_trains": {k: round(sum(row["rail_vehicles"][k] for row in rows) / n, 3) for k in classes},
            "mean_lines": {k: round(sum(row["rail_lines"][k] for row in rows) / n, 3) for k in classes},
            "mean_profit_ytd_gbp": {k: round(sum(row["rail_profit_ytd_gbp"][k] for row in rows) / n, 1) for k in classes},
        })
    return {
        "source_campaign": report.get("campaign_id"),
        "policy": policy,
        "line_telemetry_scope": (report.get("line_telemetry") or {}).get("scope"),
        "definition": "Freight: strictly non-PASS (0) and non-MAIL (2) capacity; mixed counted separately",
        "profit_note": "Vehicle profit_this_year in December snapshots (year-to-date; not closed full-year corporate profit)",
        "annual": annual,
        "per_seed": [row for rows in by_year.values() for row in rows],
    }


def check_against_jsonl(result, jsonl_path):
    """Cross-check grouped trains against the qualified physical VEHS count."""
    observed = {}
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            date = str(row.get("date") or "")
            run = row.get("run") or []
            if (row.get("duel_policy_id") != result["policy"]
                    or len(date) < 7 or date[5:7] != "12"
                    or not run or run[0] not in ("OpexAI", "AAAHogEx")):
                continue
            physical = row.get("primary_vehicles_by_mode") or {}
            if row.get("vehs_chunk_valid") is True and physical.get("rail") is not None:
                key = (int(date[:4]), int(run[1]), run[0])
                if key not in observed or date > observed[key][0]:
                    observed[key] = (date, int(physical["rail"]))
    mismatches = []
    for row in result["per_seed"]:
        key = (row["year"], row["seed"], row["arm"])
        actual = observed.get(key)
        if actual is None:
            mismatches.append({"key": key, "reason": "missing_raw_snapshot"})
        elif sum(row["rail_vehicles"].values()) != actual[1]:
            mismatches.append({"key": key, "reason": "train_count_diff",
                               "raw": actual[1], "grouped": sum(row["rail_vehicles"].values())})
    for row in result["annual"]:
        numbers = [observed[(row["year"], seed, row["arm"])][1] for seed in row["seeds"]
                   if (row["year"], seed, row["arm"]) in observed]
        mean = sum(numbers) / len(numbers) if numbers else None
        line_count = sum(row["mean_trains"].values())
        row["raw_rail_check"] = {
            "samples": len(numbers),
            "mean_physical_trains": round(mean, 3) if mean is not None else None,
            "line_minus_physical": round(line_count - mean, 3) if mean is not None else None,
        }
    result["physical_count_validation"] = {
        "per_seed_snapshots": len(result["per_seed"]),
        "mismatches": mismatches,
        "all_equal": not mismatches,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--policy", default="reference")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--crosscheck-jsonl", type=Path,
                        help="Existing raw company snapshots for independent rail totals")
    args = parser.parse_args()
    with args.report.open(encoding="utf-8") as f:
        result = analyse(json.load(f), policy=args.policy)
    if args.crosscheck_jsonl:
        check_against_jsonl(result, args.crosscheck_jsonl)
    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
