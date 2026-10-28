#!/usr/bin/env python3
"""Offline EB-2 analysis of already decoded C66 results; no games or metric re-decoding.

Usage: python3 sweeps/diag_eb2_maturation.py CAMPAIGN.json --out ANALYSIS.json
Retained signs are counted once at the terminal snapshot, never across months.
No individual line profit or causal fallback attribution is inferred from signs.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from statistics import mean


def fallback_builds(path, seeds, policy):
    """Join DECISION_LOG markers by OD within each game; include failed attempts."""
    records = []
    for seed in seeds:
        log = path.parent / (path.stem + "_engine") / f"{policy}_seed{seed}_r0.log"
        if not log.exists() or not log.stat().st_size:
            continue
        pending, successful = {}, {}
        for line in log.read_text(encoding="utf-8").splitlines():
            match = re.search(r"OPEX (\d+)-(\d+)-(\d+) (EB2_FALLBACK|RAIL_ATTEMPT|RAIL_BUILD|PROJECT_DISCARD) (.*)", line)
            if not match:
                continue
            date = "-".join(f"{int(match[i]):02}" for i in (1, 2, 3))
            fields = dict(re.findall(r"(\w+)=([^ ]+)", match[5]))
            od = fields.get("src"), fields.get("dst")
            if match[4] == "EB2_FALLBACK":
                record = {"seed": seed, "src": int(od[0]), "dst": int(od[1]),
                          "fallback_date": date, "attempt": None, "build": None, "discard": None}
                records.append(record)
                pending[od] = record
            elif match[4] == "RAIL_ATTEMPT" and od in pending:
                record = pending.pop(od)
                record["attempt"] = {"date": date, **fields}
                if fields.get("ok") == "1":
                    successful[od] = record
            elif match[4] == "RAIL_BUILD" and od in successful:
                successful.pop(od)["build"] = {"date": date, **fields}
            elif (match[4] == "PROJECT_DISCARD" and od in pending
                  and fields.get("reason") == "cash_at_build"):
                # search_in_progress is an intermediate suspension, not an outcome.
                pending.pop(od)["discard"] = {"date": date, **fields}
    return records


def link_fallback_lines(data, attempts, policy):
    """Geometric correspondence, not an exact NoAI line identity.

    Require one and only one rail group with both endpoints within 16 tiles
    of the logged OD at the first matching monthly snapshot. Then follow its
    local station key; never silently substitute a different group later.
    """
    width = 2 ** data["map_size"]
    def distance(a, b):
        return abs(a % width - b % width) + abs(a // width - b // width)
    snapshots = (data.get("line_telemetry") or {}).get("snapshots", [])
    links = []
    for record in attempts:
        if not record["build"]:
            continue
        selected = sorted((s for s in snapshots if s["arm"] == "OpexAI"
                           and s["seed"] == record["seed"] and s["duel_policy_id"] == policy
                           and s["date"] >= record["build"]["date"]), key=lambda s: s["date"])
        result = {"seed": record["seed"], "src": record["src"], "dst": record["dst"],
                  "build": record["build"], "match": None, "annual_lines": {}}
        for snapshot in selected:
            candidates = []
            for line in snapshot["lines"]:
                tiles = line["ordered_station_tiles"]
                if line["mode"] != "rail" or len(tiles) != 2 or None in tiles:
                    continue
                orientations = [(distance(record["src"], tiles[i]),
                                 distance(record["dst"], tiles[1-i])) for i in (0, 1)]
                feasible = [g for g in orientations if max(g) <= 16]
                if feasible:
                    candidates.append((line, min(feasible, key=sum)))
            if candidates:
                result["match"] = {"date": snapshot["date"], "candidates": len(candidates)}
                if len(candidates) == 1:
                    line, gaps = candidates[0]
                    result["match"].update(line_key=line["line_key_local"], endpoint_gaps=gaps)
                break
        match = result["match"]
        if match and match["candidates"] == 1:
            for snapshot in selected:
                if snapshot["date"].endswith("-12-01"):
                    result["annual_lines"][snapshot["date"]] = [line for line in snapshot["lines"]
                        if line["line_key_local"] == match["line_key"]]
        links.append(result)
    return links


def analyse(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    comparison = data["policy_comparison"]
    ref, var = (comparison[k] for k in ("reference_policy_id", "variant_policy_id"))
    seeds = data["seeds"]
    rows = {}
    jsonl = path.with_suffix(".jsonl")
    with jsonl.open(encoding="utf-8") as stream:
        for row in map(json.loads, stream):
            if row["run"][0] != "OpexAI":
                continue
            key = row["run"][1], row["date"], row["duel_policy_id"]
            if key in rows:
                raise ValueError(f"Duplicate company snapshot: {key}")
            rows[key] = row
    dates = sorted({key[1] for key in rows})
    metrics = ("profit_year", "profit", "money", "current_loan",
               "primary_vehicles", "n_stations")
    monthly = []
    for date in dates:
        record = {"date": date, "metrics": {}}
        for metric in metrics:
            pairs = [(rows[s, date, ref][metric], rows[s, date, var][metric])
                     for s in seeds]
            valid = [(a, b) for a, b in pairs if a is not None and b is not None]
            record["metrics"][metric] = {
                "n": len(valid),
                "reference": mean(a for a, b in valid) if valid else None,
                "variant": mean(b for a, b in valid) if valid else None,
                "delta": mean(b-a for a, b in valid) if valid else None,
            }
        monthly.append(record)
    terminal = dates[-1]
    signs = {}
    for policy in (ref, var):
        counts, opcodes = defaultdict(Counter), defaultdict(Counter)
        unknown = Counter()
        coverage = Counter()
        for seed in seeds:
            row = rows[seed, terminal, policy]
            coverage[row["rail_attempt_sign_coverage"]] += 1
            left, right = defaultdict(list), defaultdict(list)
            for event in row.get("rail_attempt_sign_or") or []:
                counts[event["year"]][event["reason"]] += 1
                left[tuple(event[k] for k in ("year", "line_id", "position"))].append(event)
            for event in row.get("rail_attempt_sign_ob") or []:
                right[tuple(event[k] for k in ("year", "line_id", "position"))].append(event)
            for key, events in left.items():
                if len(events) == 1 and len(right[key]) == 1:
                    opcodes[key[0]][events[0]["reason"]] += right[key][0]["opcodes"]
                else:
                    unknown[key[0]] += len(events)
        signs[policy] = {"terminal_retained_counts_by_year": dict(counts),
                         "one_to_one_sign_opcode_sums_by_year": dict(opcodes),
                         "unpaired_or_ambiguous_or_by_year": dict(unknown),
                         "snapshot_coverage": dict(coverage)}
    per_seed = []
    for seed in seeds:
        first = None
        for date in dates:
            a, b = rows[seed, date, ref], rows[seed, date, var]
            if any(a[k] != b[k] for k in metrics):
                first = date
                break
        annual = {}
        for date in dates:
            if date.endswith("-12-01"):
                a, b = rows[seed, date, ref], rows[seed, date, var]
                annual[date[:4]] = {k: b[k]-a[k] if a[k] is not None and b[k] is not None
                                   else None for k in metrics}
        per_seed.append({"seed": seed, "first_observed_metric_divergence": first,
                         "annual_deltas": annual})
    terminal_deltas = [rows[s, terminal, var]["profit_year"]-
                       rows[s, terminal, ref]["profit_year"] for s in seeds]
    expected = comparison["aggregates"]["profit_year"]["policy_delta"]["mean"]
    if abs(mean(terminal_deltas)-expected) > 1e-5:
        raise ValueError("Monthly terminal mean disagrees with C66 comparison")
    attempts = fallback_builds(path, seeds, var)
    return {
        "source": str(path), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "jsonl_sha256": hashlib.sha256(jsonl.read_bytes()).hexdigest(),
        "campaign": data["campaign_id"], "source_bundle_sha256": data["source_bundle_sha256"],
        "policies": data["policies"], "aaahogex_settings": data["aaahogex_settings"],
        "failed_runs": data["failed_runs"], "health_statuses": dict(Counter(
            game["game_status"] for game in data["games"])),
        "verdict": comparison["verdict"],
        "complete_pairs": comparison["complete_pairs"],
        "comparison_complete": comparison["comparison_complete"],
        "metric_coverage_complete": comparison["metric_coverage_complete"],
        "profit_year_statistics": comparison["aggregates"]["profit_year"]["policy_delta"],
        "value_guard_pass": comparison["value_guard_pass"],
        "monthly": monthly, "per_seed": per_seed, "signs": signs,
        "fallback_attempts_from_decision_logs": attempts,
        "fallback_line_geometric_links": link_fallback_lines(data, attempts, var),
        "limits": ["Metric divergence is not the date of a fallback or construction.",
                   "Signs have no cargo, OD, unique attempt identity or individual line profit.",
                   "One-to-one OR/OB keys are a coverage proxy, not proof of event identity.",
                   "Missing values are not imputed; yearly snapshots overlap rolling quarters.",
                   "Results use existing harness metrics; no causal capital ledger is inferred."],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = analyse(args.campaign)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("campaign", "verdict", "profit_year_statistics")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
